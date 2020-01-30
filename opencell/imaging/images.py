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


class MicroManagerTIFF:

    def __init__(self, src_filepath, verbose=True):
        '''

        '''

        self.verbose = verbose
        self.src_filepath = src_filepath

        self.events = []
        self.global_metadata = {'processing_timestamp': timestamp()}

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
        self.tiff = tifffile.TiffFile(self.src_filepath)


    @staticmethod
    def _parse_mm_tag_schema_v1(mm_tag):
        '''
        Parse a MicroManagerMetadata tag in the 'old' schema
        (KC: I believe this schema corresponds to MicroManager 1.x)
        '''
        md = {
            'slice_ind': mm_tag['SliceIndex'],
            'frame_ind': mm_tag['FrameIndex'],
            'channel_ind': mm_tag['ChannelIndex'],
            'position_ind': mm_tag['PositionIndex'],
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
            'frame_ind': mm_tag['FrameIndex'],
            'channel_ind': mm_tag['ChannelIndex'],
            'position_ind': mm_tag['PositionIndex'],
            'exposure_time': mm_tag.get('Andor EMCCD-Exposure')['PropVal'],
            'laser_status_405': mm_tag.get('Andor ILE-A-Laser 405-Power Enable')['PropVal'],
            'laser_power_405': mm_tag.get('Andor ILE-A-Laser 405-Power Setpoint')['PropVal'],
            'laser_status_488': mm_tag.get('Andor ILE-A-Laser 488-Power Enable')['PropVal'],
            'laser_power_488': mm_tag.get('Andor ILE-A-Laser 488-Power Setpoint')['PropVal']
        }
        return md


    def parse_micromanager_metadata(self):
        '''
        Parse the MicroManager metadata for each page in the TIFF file
        '''

        # the IJMetadata appears only in the first page
        ij_metadata = None
        try:
            ij_metadata = self.tiff.pages[0].tags['IJMetadata'].value['Info']
        except Exception:
            self.event_logger('There was no IJMetadata tag found on the first page')

        if ij_metadata is not None:
            try:
                ij_metadata = json.loads(ij_metadata)
            except Exception:
                self.event_logger('IJMetadata could not be parsed by json.loads')

        mm_metadata_rows = []
        for ind, page in enumerate(self.tiff.pages):
            mm_metadata_row = {
                'page_ind': ind,
                'error': False
            }

            mm_tag = page.tags.get('MicroManagerMetadata')
            if not isinstance(mm_tag, tifffile.tifffile.TiffTag):
                self.event_logger('There was no MicroManagerMetadata tag found on page %s' % ind)
                mm_metadata_row['error'] = True
                mm_metadata_rows.append(mm_metadata_row)
                continue

            try:
                page_metadata_v1 = self._parse_mm_tag_schema_v1(mm_tag.value)
            except Exception:
                page_metadata_v1 = None
            try:
                page_metadata_v2 = self._parse_mm_tag_schema_v2(mm_tag.value)
            except Exception:
                page_metadata_v2 = None

            page_metadata = {}
            mm_metadata_version = None
            if page_metadata_v1 is not None:
                mm_metadata_version = 'v1'
                page_metadata = page_metadata_v1
            elif page_metadata_v2 is not None:
                mm_metadata_version = 'v2'
                page_metadata = page_metadata_v2
            else:
                mm_metadata_row['error'] = True
                self.event_logger('Unable to parse MicroManagerMetadata tag from page %s' % ind)

            mm_metadata_rows.append({**mm_metadata_row, **page_metadata})

        self.mm_metadata = pd.DataFrame(data=mm_metadata_rows)
        self.global_metadata['mm_metadata_version'] = mm_metadata_version



class RawPipelineTIFF(MicroManagerTIFF):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # the channels we expect to find in a Pipeline-like TIFF
        self.laser_405 = '405'
        self.laser_488 = '488'


    def validate_micromanager_metadata(self):
        '''
        Validate the parsed MicroManager metadata tags for a raw Pipeline-like TIFF file
        (these are TIFFs found in the 'PlateMicroscopy' directory)

        Generates validated_mm_metadata and sets various flags
        that determine whether and how to split the pages into the 405 and 488 channels

        Steps
        ------
        - drop rows with any NAs
        - check that the dropped rows had a parsing error
        - check for two channel_inds and an equal number of pages from each
        - if there are no channel_inds, check for an even number of pages
        - if there are two channel_inds, check that slice_inds
          and exposure settings are consistent within each channel

        '''

        # whether the MM metadata has two channel inds with an equal number of slices
        self.has_valid_channel_inds = False

        # whether the MM metadata for each channel has slice_inds that increment by one
        self.has_valid_slice_inds = False

        # whether it is safe to split the TIFF stack into channels by splitting the pages in half,
        # when there are not valid channel inds
        self.safe_to_split_in_half = False

        md = self.mm_metadata.copy()

        # remove the error flag column
        errors = md['error']
        md = md.drop(labels='error', axis=1)

        # drop rows with NAs in any of the columns parsed from the MicroManagerMetadata tag
        parsed_columns = set(md.columns).difference(['page_ind'])
        md = md.dropna(how='any', subset=parsed_columns, axis=0)

        # check that the dropped rows had an error
        # (note that 'error' means either there was no MM tag or it could not be parsed)
        num_error_rows = errors.sum()
        num_dropped_rows = self.mm_metadata.shape[0] - md.shape[0]
        if num_dropped_rows != num_error_rows:
            self.event_logger(
                '%s rows with NAs were dropped but %s rows had errors' %
                (num_dropped_rows, num_error_rows))

        # check that we can coerce the parsed columns as expected
        int_columns = ['slice_ind', 'channel_ind']
        for column in int_columns:
            md[column] = md[column].apply(int)

        float_columns = ['laser_power_405', 'laser_power_488', 'exposure_time']
        for column in float_columns:
            md[column] = md[column].apply(float)

        # if there are two distinct channels, we assign the first to 405 and the second to 488
        self.channel_inds = None
        unique_channel_inds = sorted(md.channel_ind.unique())
        if len(unique_channel_inds) == 2:
            self.channel_inds = {
                self.laser_405: min(unique_channel_inds),
                self.laser_488: max(unique_channel_inds),
            }

        # if there are three channel_inds, we assume the third channel is brightfield
        elif set(unique_channel_inds) == set([0, 1, 2]):
            self.event_logger('There were three channel inds')
            self.channel_inds = {
                self.laser_405: 0,
                self.laser_488: 1,
            }

        # if there's one channel index, check for an even number of pages
        elif len(unique_channel_inds) == 1:
            if np.mod(md.shape[0], 2) == 0:
                self.safe_to_split_in_half = True
            else:
                self.event_logger('There is one channel_ind and an odd number of pages')
        else:
            self.event_logger('Unexpected number of channel_inds (%s)' % unique_channel_inds)

        # if there were valid channel_inds, check for an equal number of pages from each channel
        if self.channel_inds is not None:
            num_405 = (md.channel_ind == self.channel_inds[self.laser_405]).sum()
            num_488 = (md.channel_ind == self.channel_inds[self.laser_488]).sum()
            if num_405 == num_488:
                self.has_valid_channel_inds = True
            else:
                self.event_logger(
                    'Channels have unequal number of slices: %s and %s' % (num_405, num_488))

        # in each channel, check that slice_ind increments by 1.0
        # and that exposure time and laser power are consistent
        for channel_ind in unique_channel_inds:
            md_channel = md.loc[md.channel_ind == channel_ind]
            steps = np.unique(np.diff(md_channel.slice_ind))

            # check that slice inds are contiguous
            if len(steps) == 1 and steps[0] == 1:
                self.has_valid_slice_inds = True
            elif len(steps) == 1:
                self.event_logger(
                    'Unexpected slice_ind increment %s for channel_ind %s' % (steps[0], channel_ind))
            elif len(steps) > 1:
                self.event_logger(
                    'The slice_inds are not contiguous for channel_ind %s' % channel_ind)

            for column in float_columns:
                steps = np.unique(np.diff(md_channel[column]))
                if len(steps) > 1 or steps[0] != 0:
                    self.event_logger(
                        'Inconsistent values found in column %s for channel_ind %s' %
                        (column, channel_ind))

        self.validated_mm_metadata = md


    @staticmethod
    def tag_and_coerce_metadata(row, tag):
        '''
        Transform `row` to a dict, prepend the keys with `tag`,
        and do some hackish type coercion
        '''
        d = {}
        for key, val in dict(row).items():
            key = '%s_%s' % (key, tag)
            try:
                val = float(val)
            except Exception:
                pass
            d[key] = val
        return d


    def split_channels(self):
        '''
        Split the pages of the pipeline-like TIFF into 405 and 488 channels
        to construct the z-stack for each channel and, if possible,
        extract the channel-specific MM metadata (i.e., exposure time and laser power)

        Overview
        --------
        In a perfect world, this would be easy: we would simple use the two unique channel_inds
        to split the pages by channel (and verify the page order using the slice_inds).

        Unfortunately, due to a bug, the MM metadata tag in some TIFFs is the same on every page
        (this is notably true for 'disentangled' TIFFs from Plates 16,17,18).
        In these cases, we split the tiff into channels simply by splitting the pages in half.

        Note that we use the flags set in self.validate_mm_metadata to determine
        which of these methods to use.

        Assignment of channels
        ----------------------
        When there are two valid channel_inds, the 405 laser is assigned
        to the lower channel_ind (which is either 0 or -1).
        When there are no channel_inds, the 405 laser is assigned
        to the first half of the pages.

        '''

        self.did_split_channels = True

        self.stacks = {}
        md = self.validated_mm_metadata.copy()

        if self.has_valid_channel_inds:
            for channel_name in (self.laser_405, self.laser_488):
                channel_md = md.loc[md.channel_ind == self.channel_inds[channel_name]]
                self.global_metadata.update(
                    self.tag_and_coerce_metadata(channel_md.iloc[0], tag=channel_name))
                self.stacks[channel_name] = self.concat_pages(channel_md.page_ind.values)

        elif self.safe_to_split_in_half:
            n = int(md.shape[0]/2)
            self.stacks[self.laser_405] = self.concat_pages(md.iloc[:n].page_ind.values)
            self.stacks[self.laser_488] = self.concat_pages(md.iloc[n:].page_ind.values)

        else:
            self.event_logger('Unable to safely split pages by channel')
            self.did_split_channels = False


    def concat_pages(self, page_inds):
        '''
        '''
        stack = np.array([self.tiff.pages[ind].asarray() for ind in page_inds])
        return stack


    def project_stack(self, channel_name, axis, dst_filepath=None):
        '''
        Generate x-, y-, or z-projections and log the max and min intensities
        '''

        axis_inds = {'x': 1, 'y': 2, 'z': 0}
        if axis not in axis_inds.keys():
            raise ValueError("Axis must be one of 'x', 'y', or 'z'")
        axis_ind = axis_inds[axis]

        try:
            proj = self.stacks[channel_name].max(axis=axis_ind)
            minmax = {
                'min_intensity': int(proj.min()),
                'max_intensity': int(proj.max()),
            }
            self.global_metadata.update(self.tag_and_coerce_metadata(minmax, tag=channel_name))

            if dst_filepath is not None:
                tifffile.imsave(dst_filepath, proj)

        except Exception:
            self.event_logger(
                'An error occured while %s-projecting the %s channel' % (axis, channel_name))


    def calculate_z_profiles(self, channel):
        '''
        Calculate various statistics of the intensities for each z-slice
        '''

        stack = self.stacks[channel]

        min_profile = np.array([zslice.min() for zslice in stack]).astype(int)
        max_profile = np.array([zslice.max() for zslice in stack]).astype(int)
        mean_profile = np.array([zslice.mean() for zslice in stack]).astype(int)
        p9999_profile = np.array([np.percentile(zslice, 99.99) for zslice in stack]).astype(int)

        return {
            'min': min_profile,
            'max': max_profile,
            'mean': mean_profile,
            'p9999': p9999_profile,
        }


    @staticmethod
    def find_cell_layer(stack):
        '''
        Estimate the center of the cell layer using the center of mass
        of the z-profile of the mean intensity of the Hoechst staining
        '''

        # z-profile of the mean intensity in the Hoechst channel
        raw_profile = np.array([zslice.mean() for zslice in stack]).astype(float)
        profile = raw_profile - raw_profile.mean()
        profile[profile < 0] = 0

        x = np.arange(len(profile))
        center_of_mass = (profile * x).sum()/profile.sum()
        return center_of_mass, raw_profile


    def align_cell_layer(self, rel_bottom, rel_top, step_size):
        '''
        Approximately align the 405 and 488 stacks to correct for chromatic aberration,
        and crop around the cell layer so that it is in the center of the stack

        rel_bottom, rel_top : the position of the bottom and top of the cell layer,
            relative to the center of the cell layer, in an integer number of microns
            (rel_bottom should be negative)
        '''

        result = {}

        stack_405 = self.stacks[self.laser_405].copy()
        stack_488 = self.stacks[self.laser_488].copy()

        # hard-coded chromatic aberration offset in microns
        # this is an empirically estimated median offset
        # obtained by inspecting z-stacks from nucleus-localized targets
        chromatic_aberration_offset = 1.0
        offset_ind = int(chromatic_aberration_offset / step_size)

        stack_405 = stack_405[:-offset_ind, :, :]
        stack_488 = stack_488[offset_ind:, :, :]

        # estimate the cell layer center and round it the nearest z-slice
        cell_layer_center, _ = self.find_cell_layer(stack_405)
        cell_layer_center = np.round(cell_layer_center)

        # absolute position, in number of z-slices, of the top and bottom of the cell layer
        bottom_ind = int(cell_layer_center + rel_bottom / step_size)
        top_ind = int(cell_layer_center + rel_top / step_size)

        if bottom_ind < 0:
            result['error'] = 'The cell layer center was too close to the bottom of the stack'
        elif top_ind >= stack_405.shape[0]:
            result['error'] = 'The cell layer center was too close to the top of the stack'
        else:
            stack_405 = stack_405[bottom_ind:top_ind, :, :]
            stack_488 = stack_488[bottom_ind:top_ind, :, :]

        result['offset_488_405'] = offset_ind
        result['crop_window'] = [bottom_ind, top_ind]
        result['cell_layer_center'] = cell_layer_center
        stacks = {'405': stack_405, '488': stack_488}
        return stacks, result
