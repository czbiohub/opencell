import os
import re
import sys
import glob
import json
import pickle
import skimage
import hashlib
import datetime
import tifffile

import numpy as np
import pandas as pd

from opencell import constants
from opencell.imaging import micromanager


class RawZStackProcessor:

    def __init__(
        self, 
        pml_id, 
        parental_line, 
        imaging_round_id, 
        plate_id, 
        well_id, 
        site_num, 
        target_name,
        raw_filepath):
        
        self.pml_id = pml_id
        self.parental_line = parental_line
        self.imaging_round_id = imaging_round_id
        self.plate_id = plate_id
        self.well_id = well_id
        self.site_num = site_num
        self.target_name = target_name
        self.raw_filepath = raw_filepath

        # create site_id from site_num
        self.site_id = 'S%02d' % int(self.site_num)


    def src_filepath(self, src_root=None):
        '''
        Construct the absolute filepath to a TIFF stack in the 'PlateMicroscopy' directory 
        from a row of metadata (works for raw and processed TIFFs)

        Returns a path of the form (relative to src_root):
        'mNG96wp15/ML0125_20190424/mNG96wp15_sortday2/C11_4_SLC35F2.ome.tif'

        src_root is the absolute path to the 'PlateMicroscopy' directory
        (e.g., on `cap`, '/gpfsML/ML_group/PlateMicroscopy/')
        '''

        src_root = '' if src_root is None else src_root
        src_filepath = os.path.join(src_root, self.raw_filepath)
        return src_filepath

    
    def dst_plate_dir(self):
        '''
        Construct a dst plate_dir from an src plate_dir

        Destination plate directory names are of the form 'czML0383-P0001-R01'
        '''
        dst_plate_dir = f'{self.parental_line}-{self.plate_id}-{self.imaging_round_id}'
        return dst_plate_dir


    def dst_filepath(self, dst_root=None, kind=None, channel=None, axis=None, makedirs=True):
        '''
        Construct the relative directory path and filename for a 'kind' of output file

        The path is of the form {kind}/{channel}/{axis}/{dst_plate_dir}

        dst_plate_dir is of the form 'czML0383-P0001-R01'
        dst_filename is of the form '{dst_plate_dir}-ML0123-A01-S01-CLTA'

        Returns dst_dirpath and the dst_filename as a tuple
        (so that dst_dirpath can be created if it doesn't exist)

        '''

        if dst_root is None:
            dst_root = ''
        
        kinds = ['metadata', 'projections', 'raw-stacks', 'cropped-stacks', 'processed-stacks']
        if kind not in kinds:
            raise ValueError('%s is not a valid destination kind' % kind)
        subdir_names = [kind]

        # validate and create subdir names for projections directory
        # (channel and projection axis)
        if kind == 'projections':
            if channel not in ['dapi', 'gfp', 'rgb']:
                raise ValueError("'%s' is not a valid channel" % channel)
            if axis not in ['x', 'y', 'z']:
                raise ValueError("'%s' is not a valid axis" % axis)
            subdir_names.extend([channel, axis])

        # destination plate_dir name
        dst_plate_dir = self.dst_plate_dir()

        # construct the destination dirpath
        dst_dirpath = os.path.join(dst_root, *subdir_names, dst_plate_dir)
        if makedirs:
            os.makedirs(dst_dirpath, exist_ok=True)
        
        # construct the destination filename
        dst_filename = f'{dst_plate_dir}-{self.pml_id}-{self.well_id}-{self.site_id}-{self.target_name}'
        return os.path.join(dst_dirpath, dst_filename)


    @staticmethod
    def tag_filepath(filepath, tag, ext):
        '''
        Append a tag and a file extension to a filepath
        Example: 'data/MMStack-01.tif' -> 'data/MMStack-01_metadata.csv'
        '''
        # remove the existing extension (if any)
        filepath, _ = os.path.splitext(filepath)
        filepath = f'{filepath}-{tag}.{ext}'
        return filepath


    def process_raw_tiff(self, dst_root, src_root):
        '''
        Process a single raw TIFF
            1) parse the micromanager and other metadata
            2) split the tiff pages into DAPI and GFP channels
            3) generate z-projections

        src_root : the root of the 'PlateMicroscopy' directory
        dst_root : the destination 'oc-plate-microscopy' directory 
        '''

        src_filepath = self.src_filepath(src_root=src_root)

        tiff = micromanager.RawPipelineTIFF(src_filepath, verbose=False)
        tiff.parse_micromanager_metadata()
        tiff.validate_micromanager_metadata()

        # attempt to split the channels and project
        tiff.split_channels()
        if tiff.did_split_channels:
            for channel in ['dapi', 'gfp']:
                for axis in ['x', 'y', 'z']:
                    dst_filepath = self.dst_filepath(
                        dst_root=dst_root, kind='projections', channel=channel, axis=axis)

                    tag = '%s-PROJ-%s' % (channel.upper(), axis.upper())
                    dst_filepath = self.tag_filepath(dst_filepath, tag=tag, ext='tif')
                    tiff.project_stack(channel_name=channel, axis=axis, dst_filepath=dst_filepath)

        # the tiff file must be manually closed
        tiff.tiff.close()

        # save the parsing events
        dst_filepath = self.dst_filepath(dst_root, kind='metadata')
        events_path = self.tag_filepath(dst_filepath, tag='raw-tiff-processing-events', ext='csv')
        tiff.save_events(events_path)

        # append the fov_id to the tiff metadata
        tiff_metadata = tiff.global_metadata
        return tiff_metadata


    def calculate_fov_features(self, dst_root, pipeline_fov_scorer):
        '''
        scorer : an instance of PipelineFOVScorer in 'training' mode
        row : a row of self.md_raw
        dst_root : the root destination to which z-projections were saved in process_raw_tiff
        '''

        # construct the filepath to the DAPI z-projection
        filepath = self.dst_filepath(dst_root, kind='projections', channel='dapi', axis='z')
        filepath = self.tag_filepath(filepath, tag='DAPI-PROJ-Z', ext='tif')

        # calculate the features from the z-projection
        features = pipeline_fov_scorer.process_existing_fov(filepath)
        return features


    def aggregate_filepaths(self, rows, dst_root, kind='metadata', tag='metadata-parsing-events', ext='csv'):
        '''
        Aggregate filepaths for a particular kind of processed file
        by generating these filepaths (which may not exist) from the `rows` dataframe

        For now, `kind` and `tag` must match the corresponding kwargs 
        in the method that generated/will generate the processed files
        '''

        paths = []
        for ind, row in rows.iterrows():
            path = self.dst_filepath(dst_root, kind=kind)
            path = self.tag_filepath(path, tag=tag, ext=ext)
            paths.append(path)
            
        return paths

        
        

