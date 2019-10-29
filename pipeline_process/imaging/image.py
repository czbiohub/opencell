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


class RawPipelineImage:

    def __init__(self, src_filepath):
        '''
        Processing methods for raw pipeline-like z-stacks

        Assumptions
        -----------

        '''
        self.metadata = {}
        self.src_filepath = src_filepath


    def calc_hash(self):
        '''
        Calculate the sha1 hash from the file contents
        '''
        sha1 = hashlib.sha1()
        with open(self.src_filepath, 'rb') as file:
            sha1.update(file.read())

        hash_value = sha1.hexdigest()
        self.metadata['sha1_hash'] = hash_value
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
        self.metadata['loader'] = loader
    

    def parse_micromanager_metadata(self):
        '''
        Parse the MicroManager metadata for each page in the TIFF file
        '''

        # the MM metadata tag name *should* be consistent
        mm_tag_name = 'MicroManagerMetadata'

        if not hasattr(self, 'tiff'):
            self.open_tiff()

        rows = []
        for ind, page in enumerate(self.tiff.pages):
            row = {'ind': ind}
            mm_tag = page.tags.get(mm_tag_name)
            if not isinstance(mm_tag, tifffile.tifffile.TiffTag):
                rows.append({'ind': ind, 'error': 'Missing MicroManagerMetadata tag'})
                continue

            mm_tag = mm_tag.value
            metadata_schema = None
            page_metadata = {'error': 'Unparseable MicroManagerMetadata tag'}
            try:
                page_metadata = self._parse_mm_tag_schema_v1(mm_tag)
                metadata_schema = 'v1'
            except:
                try:
                    page_metadata = self._parse_mm_tag_schema_v2(mm_tag)
                    metadata_schema = 'v2'
                except:
                    pass
            rows.append({**row, **page_metadata})

        self.mm_metadata = pd.DataFrame(data=rows)
        self.metadata['metadata_schema'] = metadata_schema


    @staticmethod
    def _parse_mm_tag_schema_v1(mm_tag):
        '''
        Parse a MicroManagerMetadata tag in the 'old' schema
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


    def load_stack(self, channel_ind):
        '''
        Load the stack for one channel into a numpy array
        '''
        inds = np.argwhere(self.mm_metadata.channel_ind==channel_ind).flatten()
        inds.sort()

        im = np.array([self.tiff.pages[ind].asarray() for ind in inds])
        return im


    def project_stack(self, channel_name='dapi', axis_name='z', dst_filepath=None):
        '''
        Generate x-, y-, or z-projections
        '''
        
        # TODO: eliminate NaN rows in mm_metadata
        channel_inds = self.mm_metadata.channel_ind.unique()
        if channel_name == 'dapi':
            channel_ind = channel_inds.min()
        if channel_name == 'gfp':
            channel_ind = channel_inds.max()

        axes = {'x': 1, 'y': 2, 'z': 0}
        if axis_name not in axes.keys():
            raise ValueError("Axis must be one of 'x', 'y', or 'z'")
        axis_ind = axes[axis_name]

        proj = self.load_stack(channel_ind).max(axis=axis_ind)
        if dst_filepath is not None:
            imageio.imsave(dst_filepath, proj)

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
        