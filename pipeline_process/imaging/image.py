import os
import re
import sys
import glob
import json
import pickle
import skimage
import hashlib
import imageio
import datetime
import tifffile
import numpy as np
import pandas as pd


def timestamp():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


class RawPipelineImage:

    def __init__(self, src_filepath, verbose=True):
        '''
        Processing methods for raw pipeline-like z-stacks

        Assumptions
        -----------

        '''
        self.events = []
        self.global_metadata = {'timestamp': timestamp()}
        
        self.verbose = verbose
        self.src_filepath = src_filepath
        self.open_tiff()


    def event_logger(self, message):
        '''
        '''
        if self.verbose:
            print('EVENT: %s' % message)
        self.events.append({'message': message, 'timestamp': timestamp()})


    def save_events(self, dst_filepath):
        if not self.events:
            return
        pd.DataFrame(data=self.events).to_csv(dst_filepath, index=False)


    def save_global_metadata(self, dst_filepath):
        with open(dst_filepath, 'w') as file:
            json.dump(self.global_metadata, file)


    def save_mm_metadata(self, dst_filepath):
        self.mm_metadata.to_csv(dst_filepath, index=False)


    def calc_hash(self):
        '''
        Calculate the sha1 hash from the file contents
        '''
        sha1 = hashlib.sha1()
        with open(self.src_filepath, 'rb') as file:
            sha1.update(file.read())

        hash_value = sha1.hexdigest()
        self.global_metadata['sha1_hash'] = hash_value
        return hash_value


    def open_tiff(self):
        '''
        Open the stack using tifffile.TiffFile
        '''
        loader = 'tifffile'
        try:
            self.tiff = tifffile.TiffFile(self.src_filepath)
        except:
            loader = 'skimage.external.tifffile'
            self.tiff = skimage.external.tifffile.TiffFile(self.src_filepath)        
        self.global_metadata['loader'] = loader
    

    def parse_micromanager_metadata(self):
        '''
        Parse the MicroManager metadata for each page in the TIFF file
        '''

        # the IJMetadata appears only in the first page
        ij_metadata = None
        try:
            ij_metadata = self.tiff.pages[0].tags['IJMetadata'].value['Info']
        except:
            self.event_logger('There was no IJMetadata tag found on the first page')
        
        if ij_metadata is not None:
            try:
                ij_metadata = json.loads(ij_metadata)
            except:
                self.event_logger('IJMetadata could not be parsed by json.loads')
        self.global_metadata['ij_metadata'] = ij_metadata

        rows = []
        for ind, page in enumerate(self.tiff.pages):
            row = {
                'page_ind': ind,
                'error': False
            }

            mm_tag = page.tags.get('MicroManagerMetadata')
            if not isinstance(mm_tag, tifffile.tifffile.TiffTag):
                self.event_logger('There was no MicroManagerMetadata tag found on page %s' % ind)
                row['error'] = True
                rows.append(row)
                continue

            try:
                page_metadata_v1 = self._parse_mm_tag_schema_v1(mm_tag.value)
            except:
                page_metadata_v1 = None
                try:
                    page_metadata_v2 = self._parse_mm_tag_schema_v2(mm_tag.value)
                except:
                    page_metadata_v2 = None

            page_metadata = {}
            metadata_schema = None
            if page_metadata_v1 is not None:
                metadata_schema = 'v1'
                page_metadata = page_metadata_v1
            elif page_metadata_v2 is not None:
                metadata_schema = 'v2'
                page_metadata = page_metadata_v2
            else:
                row['error'] = True
                self.event_logger('Unable to parse MicroManagerMetadata tag from page %s' % ind)

            rows.append({**row, **page_metadata})

        self.mm_metadata = pd.DataFrame(data=rows)
        self.global_metadata['metadata_schema'] = metadata_schema


    @staticmethod
    def _parse_mm_tag_schema_v1(mm_tag):
        '''
        Parse a MicroManagerMetadata tag in the 'old' schema
        (KC: I believe this schema corresponds to MicroManager 1.x)
        '''
        md = {
            'slice_ind': mm_tag['SliceIndex'],
            'channel_ind': mm_tag['ChannelIndex'],
            'exposure_time': mm_tag['AndorEMCCD-Exposure'],
            'laser_status_405': mm_tag['AndorILE-A-Laser 405-Power Enable'],
            'laser_power_405': mm_tag['AndorILE-A-Laser 405-Power Setpoint'],
            'laser_status_488': mm_tag['AndorILE-A-Laser 488-Power Enable'],
            'laser_power_488': mm_tag['AndorILE-A-Laser 488-Power Setpoint']
        }
        return md


    @staticmethod
    def _parse_mm_tag_schema_v2(mm_tag):
        '''
        Parse a MicroManagerMetadata tag in the 'new' schema
        (KC: I believe this schema corresponds to MicroManager 2.x)
        '''
        md = {
            'slice_ind': mm_tag['SliceIndex'],
            'channel_ind': mm_tag['ChannelIndex'],
            'exposure_time': mm_tag['Andor EMCCD-Exposure']['PropVal'],
            'laser_status_405': mm_tag['Andor ILE-A-Laser 405-Power Enable']['PropVal'],
            'laser_power_405': mm_tag['Andor ILE-A-Laser 405-Power Setpoint']['PropVal'],
            'laser_status_488': mm_tag['Andor ILE-A-Laser 488-Power Enable']['PropVal'],
            'laser_power_488': mm_tag['Andor ILE-A-Laser 488-Power Setpoint']['PropVal']
        }
        return md


    def validate_micromanager_metadata(self):
        '''
        '''

        md = self.mm_metadata.copy()

        # remove the error flag column
        errors = md['error']
        md = md.drop(labels='error', axis=1)

        # drop rows with NAs in any of the columns parsed from the MicroManagerMetadata tag
        parsed_columns = set(md.columns).difference(['page_ind'])
        md = md.dropna(how='any', subset=parsed_columns, axis=0)

        # check that the dropped rows had an error
        num_error_rows = errors.sum()
        num_dropped_rows = self.mm_metadata.shape[0] - md.shape[0]
        if num_dropped_rows != num_error_rows:
            self.event_logger('More rows with NAs were dropped than there were rows with errors')

        # check that we can coerce the parsed columns as expected
        int_columns = ['slice_ind', 'channel_ind']
        for column in int_columns:
            md[column] = md[column].apply(int)

        float_columns = ['laser_power_405', 'laser_power_488', 'exposure_time',]
        for column in float_columns:
            md[column] = md[column].apply(float)

        # check for two channels and an equal number of slices
        # hint: many stacks have only channel_ind
        channel_inds = md.channel_ind.unique()
        if len(channel_inds) != 2:
            self.event_logger('Unexpected number of channel_inds (%s)' % channel_inds)
        else:
            num_0 = (md.channel_ind==channel_inds[0]).sum()
            num_1 = (md.channel_ind==channel_inds[1]).sum()
            if num_0 != num_1:
                self.event_logger('Channels have unequal number of slices: %s and %s' % (num_0, num_1))

        # if there's one channel index, check for an even number of pages
        if len(channel_inds) == 1 and np.mod(md.shape[0], 2) == 1:
            self.event_logger('There is one channel_ind and an odd number of pages')

        # check that slice inds are contiguous
        # and that exposure time and laser power are consistent for each channel
        for channel_ind in channel_inds:
            md_channel = md.loc[md.channel_ind==channel_ind]
            steps = np.unique(np.diff(md_channel.slice_ind))

            if len(steps) > 1:
                self.event_logger(
                    'The slice_inds are not contiguous for channel_ind %s' % channel_ind)

            if len(steps) == 1 and steps[0] != 1:
                self.event_logger(
                    'Unexpected slice_ind increment %s for channel_ind %s' % (steps[0], channel_ind))

            for column in float_columns:
                steps = np.unique(np.diff(md_channel[column]))
                if len(steps) > 1 or steps[0] != 0:
                    self.event_logger(
                        'Inconsistent values found in column %s for channel_ind %s' % (column, channel_ind))

        self.validated_mm_metadata = md


    def load_stack(self, channel_ind):
        '''
        Load the stack for one channel into a numpy array
        '''
        inds = np.argwhere(self.validated_mm_metadata.channel_ind==channel_ind).flatten()
        inds.sort()

        im = np.array([self.tiff.pages[ind].asarray() for ind in inds])
        return im


    def project_stack(self, channel='dapi', axis='z', dst_filepath=None):
        '''
        Generate x-, y-, or z-projections
        '''
        
        channel_inds = self.validated_mm_metadata.channel_ind.unique()
        if channel == 'dapi':
            channel_ind = channel_inds.min()
        if channel == 'gfp':
            channel_ind = channel_inds.max()

        axis_inds = {'x': 1, 'y': 2, 'z': 0}
        if axis not in axis_inds.keys():
            raise ValueError("Axis must be one of 'x', 'y', or 'z'")
        axis_ind = axis_inds[axis]

        proj = self.load_stack(channel_ind).max(axis=axis_ind)
        if dst_filepath is not None:
            tifffile.imsave(dst_filepath, proj)

        return proj


    def crop_stack(self):
        '''
        Crop the stacks in z around the cell layer
        '''
        pass


    def downsample(self, scale):
        '''
        Downsample the stack
        '''
        pass


    def to_uint8(self):
        '''
        '''
        pass
        