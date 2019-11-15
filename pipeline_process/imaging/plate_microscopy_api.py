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

from . import image


class PlateMicroscopyAPI:

    
    def __init__(self, root_dir=None, cache_dir=None):
        '''
        '''

        self.root_dir = root_dir
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

        self.cached_os_walk_filepath = os.path.join(self.cache_dir, 'os_walk.p')
        self.cached_metadata_filepath = os.path.join(self.cache_dir, 'all-metadata.csv')
        self.cached_raw_metadata_filepath = os.path.join(self.cache_dir, 'raw-metadata.csv')

        if os.path.isfile(self.cached_os_walk_filepath):
            self.load_cached_os_walk()

        if os.path.isfile(self.cached_metadata_filepath):
            self.load_cached_metadata()


    def load_cached_os_walk(self):
        with open(self.cached_os_walk_filepath, 'rb') as file:
            self.os_walk = pickle.load(file)


    def cache_os_walk(self):
        if os.path.isfile(self.cached_os_walk_filepath):
            raise ValueError('Cached os_walk already exists')
    
        self.os_walk = list(os.walk(self.root_dir))
        with open(self.cached_os_walk_filepath, 'wb') as file:
            pickle.dump(self.os_walk, file)


    def load_cached_metadata(self):
        self.md = pd.read_csv(self.cached_metadata_filepath)
        if os.path.isfile(self.cached_raw_metadata_filepath):
            self.md_raw = pd.read_csv(self.cached_raw_metadata_filepath)
        else:
            self.construct_raw_metadata()


    def cache_metadata(self, overwrite=False):
        if not overwrite and os.path.isfile(self.cached_metadata_filepath):
            raise ValueError('Cached metadata already exists')
        self.md.to_csv(self.cached_metadata_filepath, index=False)
        self.md_raw.to_csv(self.cached_raw_metadata_filepath, index=False)


    def check_max_depth(self):
        '''
        check the maximum subdirectory depth (relative to the PlateMicroscopy dir)
        Depth is three for 'plate_dir/exp_dir/sortday_dir/'
        Depth is two for either 'plate_dir/exp_dir/' or 'plate_dir/PublicationQuality/'
        '''
        maxx = 0
        for row in self.os_walk:
            path, subdirs, filenames = row
            filenames = [name for name in filenames if '.tif' in name]
            if not filenames:
                continue
            maxx = max(maxx, len(path.replace(self.root_dir, '').split(os.sep)))  
        return maxx
    

    @staticmethod
    def parse_raw_tiff_filename(filename):
        '''
        Parse well_id, fov_num, and target name from a raw TIFF filename
        
        For almost all filenames, the format is '{well_id}_{fov_num}_{target_name}.ome.tif'
        
        The exception is 'Jin' lines, which appear in plate6 and plate7;
        here, the format is '{well_id}_{fov_num}_Jin_{well_id}_{target_name}.ome.tif',
        and it is the first well_id that is the 'real', pipeline-relevant, well_id
        
        Note that the target name sometimes includes the terminus that was tagged,
        in the form of a trailing '-N', '-C', '_N', '_C', '_Int', '-Int'

        Also, two target names include a trailing '-A' or '-B' 
        (these are 'HLA-A' and 'ARHGAP11A-B')
        '''
        
        well_id = '[A-H][1-9][0-2]?'
        fov_num = '[1-9][0-9]?'
        target_name = r'[a-zA-Z0-9]+'
        appendix = r'[\-|_][a-zA-Z]+'
        raw_pattern = rf'^({well_id})_({fov_num})_({target_name})({appendix})?.ome.tif$'

        # in Jin filenames, the second well_id is not relevant
        raw_jin_pattern = rf'^({well_id})_({fov_num})_Jin_(?:{well_id})_({target_name})({appendix})?.ome.tif$'
        
        filename_was_parsed = False
        for pattern in [raw_pattern, raw_jin_pattern]:
            result = re.match(pattern, filename)
            if result:
                filename_was_parsed = True
                well_id, fov_num, target_name, appendix = result.groups()
                break

        if not filename_was_parsed:
            return None

        return {
            'well_id': well_id,
            'fov_num': fov_num,
            'target_name': target_name
        }


    def construct_metadata(self, paths_only=False):
        '''
        Create metadata dataframe from the os.walk results
        '''
        rows = []
        for row in self.os_walk:
            path, subdirs, filenames = row

            # all TIFF files in the directory
            # (we assume these are TIFF stacks)
            filenames = [name for name in filenames if '.tif' in name]
            if not filenames:
                continue

            # ignore plate-level directories that are not of the form
            # 'mnG96wp{num}' or 'mNG96wp{num}_Thawed',
            # where num is an integer greater than 0
            rel_path = path.replace(self.root_dir, '')
            if not re.match('^mNG96wp[1-9]([0-9])?(_Thawed|/)', rel_path):
                continue

            # create a column for each subdirectory, starting with the plate-level directory
            path_dirs = rel_path.split(os.sep)
            path_info = {'level_%d' % ind: path_dir for ind, path_dir in enumerate(path_dirs)}

            # create a row only for the path
            if paths_only:
                rows.append(path_info)
                continue
            
            # create a row for each file
            for filename in filenames:
                # parse the well_id, site_num, and target_name from the filename
                # TODO: consider moving this to construct_raw_metadata
                file_info = self.parse_raw_tiff_filename(filename)
                if file_info is None:
                    file_info = {}
                    # only warn about unparseable filenames that appear to be raw
                    if '.ome.tif' in filename and 'MMStack' not in filename:
                        print('Warning: unparseable but seemingly raw filename %s' % filename)

                rows.append({'filename': filename, **file_info, **path_info})

        md = pd.DataFrame(data=rows)
        # d = d.replace(to_replace=np.nan, value='')

        # rename the subdirectory columns
        # (we know that there are always at most three of these columns)
        md = md.rename(columns={'level_0': 'plate_dir', 'level_1': 'exp_dir', 'level_2': 'exp_subdir'})

        # parse the plate_num from the plate_dir
        md['plate_num'] = [self.parse_src_plate_dir(plate_dir) for plate_dir in md.plate_dir]

        # flag all of the raw files
        # these are all TIFF files in experiment dirs of the form '^ML[0-9]{4}_[0-9]{8}$'
        # (for example: 'ML0045_20181022')        
        md['is_raw'] = md.exp_dir.apply(lambda s: re.match('^ML[0-9]{4}_[0-9]{8}$', s) is not None)

        self.md = md
        self.construct_raw_metadata()


    @staticmethod
    def parse_src_plate_dir(plate_dir):
        '''
        Parse the plate number from a src plate_dir
        Example: 'mNG96wp19' -> '19'
        '''
        plate_num = re.findall('^mNG96wp([0-9]{1,2})', plate_dir.split(os.sep)[0])[0]
        return plate_num


    def construct_raw_metadata(self):
        '''
        Construct the raw metadata (a subset of self.md)
        '''

        # use the is_raw flag
        md_raw = self.md.loc[self.md.is_raw].copy()

        # parse the ML experiment ID from the experiment directory name
        # (note that we already implicitly validated the form of the exp_dirs
        # in construct_metadata when we generated the is_raw flags)
        md_raw['exp_id'] = [exp_dir.split('_')[0] for exp_dir in md_raw.exp_dir]

        # make sure the plate_num is a number
        md_raw['plate_num'] = md_raw.plate_num.apply(int)

        # drop rows without a well_id
        # (these are un-renamed stacks in 'Plate5_Thawed2')
        md_raw.dropna(how='any', subset=['well_id'], axis=0, inplace=True)

        # check for valid well_ids and pad the column numbers ('A1' -> 'A01')
        dropped_inds = []
        for ind, row in md_raw.iterrows():        
            result = re.findall('([A-H])([0-9]{1,2})', row.well_id)
            if not result:        
                dropped_inds.append(ind)
                continue            
            well_row, well_col = result[0]
            md_raw.at[ind, 'well_id'] = '%s%02d' % (well_row, int(well_col))
        md_raw.drop(dropped_inds, inplace=True)

        self.md_raw = md_raw


    def append_file_info(self):
        '''
        Append the file size and creation time to the metadata
        (requires that the partition be mounted)
        '''
        if not os.path.isdir(self.root_dir):
            print('Warning: cannot determine file info unless the partition is mounted')
            return

        md = self.md.replace(to_replace=np.nan, value='')
        for ind, row in md.iterrows():
            if not np.mod(ind, 10000):
                print(ind)
            s = os.stat(os.path.join(self.root_dir, row.plate_dir, row.exp_dir, row.exp_subdir, row.filename))
            md.at[ind, 'filesize'] = s.st_size
            md.at[ind, 'ctime'] = s.st_ctime

        self.md = md


    @staticmethod
    def src_filepath(row, src_root=None):
        '''
        Construct the absolute filepath to a TIFF stack in the 'PlateMicroscopy' directory 
        from a row of metadata (works for raw and processed TIFFs)

        Returns a path of the form (relative to src_root):
        'mNG96wp15/ML0125_20190424/mNG96wp15_sortday2/C11_4_SLC35F2.ome.tif'

        src_root is the absolute path to the 'PlateMicroscopy' directory
        (e.g., on `cap`, '/gpfsML/ML_group/PlateMicroscopy/')
        '''
        if src_root is None:
            src_root = ''
        
        # exp_subdir can be missing
        exp_subdir = row.exp_subdir
        if  pd.isna(exp_subdir):
            exp_subdir = ''

        src_filepath = os.path.join(src_root, row.plate_dir, row.exp_dir, exp_subdir, row.filename)
        return src_filepath

    
    def dst_plate_dir(self, src_plate_dir):
        '''
        Construct a dst plate_dir from an src plate_dir

        Destination plate directory names are of the form 'mNG-P0001-E01-R00'
        '''
        
        # parental line is always the mNeonGreen 1-10 line 
        # (here abbreviated 'mNG' for 'split mNeonGreen')
        parental_line = 'mNG'

        # the plate design ID
        plate_num = self.parse_src_plate_dir(src_plate_dir)
        plate_id = 'P%04d' % int(plate_num)

        # the electroporation ID 
        # (always the same, since all plates have been electroporated once)
        ep_id = 'E01'

        # hackish way to determine the imaging round ID
        # (zero for the first, post-sorting round)
        if 'Thawed2' in src_plate_dir:
            imaging_round_id = 'R03'
        elif 'Thawed' in src_plate_dir:
            imaging_round_id = 'R02'
        else:
            imaging_round_id = 'R01'

        dst_plate_dir = f'{parental_line}-{plate_id}-{ep_id}-{imaging_round_id}'
        return dst_plate_dir


    def dst_filepath(self, row, dst_root=None, kind=None, channel=None, axis=None, makedirs=True):
        '''
        Construct the relative directory path and filename for a 'kind' of output file

        The path is of the form {kind}/{channel}/{axis}/{dst_plate_dir}

        dst_plate_dir is of the form 'mNG-P0001-E01-R00'
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
            axis, channel = axis.upper(), channel.upper()
            if channel not in ['DAPI', 'GFP', 'RGB']:
                raise ValueError("'%s' is not a valid channel" % channel)
            if axis not in ['X', 'Y', 'Z']:
                raise ValueError("'%s' is not a valid axis" % axis)
            subdir_names.extend([channel, 'PROJ-%s' % axis])

        # destination plate_dir name
        dst_plate_dir = self.dst_plate_dir(row.plate_dir)

        # construct the destination dirpath
        dst_dirpath = os.path.join(dst_root, *subdir_names, dst_plate_dir)
        if makedirs:
            os.makedirs(dst_dirpath, exist_ok=True)
        
        # construct the destination filename
        fov_id = '%02d' % int(row.fov_num)
        dst_filename = f'{dst_plate_dir}-{row.exp_id}-{row.well_id}-{fov_id}-{row.target_name}'
        
        return os.path.join(dst_dirpath, dst_filename)


    @staticmethod
    def tag_filepath(filepath, tag, ext):
        '''
        Append a tag and a file extension to a filepath
        Example: 'data/MMStack-01.tif' -> 'data/MMStack-01_metadata.csv'
        '''
        # remove the existing extension (if any)
        filepath, _ = os.path.splitext(filepath)
        filepath = f'{filepath}_{tag}.{ext}'
        return filepath


    def process_raw_tiff(self, row, dst_root, src_root=None):
        '''
        Process a single raw TIFF
            1) parse the micromanager and other metadata
            2) split the tiff pages into DAPI and GFP channels
            3) generate z-projections

        row : a row of the `self.md_raw` dataframe
        src_root : the root of the 'PlateMicroscopy' directory
        dst_root : the destination 'oc-plate-microscopy' directory 
        '''

        if src_root is None:
            src_root = self.root_dir
    
        src_filepath = self.src_filepath(row, src_root=src_root)

        tiff = image.RawPipelineTIFF(src_filepath, verbose=False)
        tiff.parse_micromanager_metadata()
        tiff.validate_micromanager_metadata()

        # attempt to split the channels and project
        tiff.split_channels()
        if tiff.did_split_channels:
            for channel in ['dapi', 'gfp']:
                for axis in ['x', 'y', 'z']:
                    dst_filepath = self.dst_filepath(
                        row, dst_root=dst_root, kind='projections', channel=channel, axis=axis)

                    tag = '%s-PROJ-%s' % (channel.upper(), axis.upper())
                    dst_filepath = self.tag_filepath(dst_filepath, tag=tag, ext='tif')
                    tiff.project_stack(channel_name=channel, axis=axis, dst_filepath=dst_filepath)

        # save the parsing events and parsed global metadata
        dst_filepath = self.dst_filepath(row, dst_root=dst_root, kind='metadata')
        metadata_path = self.tag_filepath(dst_filepath, tag='raw-tiff-metadata', ext='json')
        events_path = self.tag_filepath(dst_filepath, tag='raw-tiff-processing-events', ext='csv')
        
        tiff.save_global_metadata(metadata_path)
        tiff.save_events(events_path)
        tiff.tiff.close()


    def calculate_fov_features(self, row, dst_root, scorer):
        '''
        scorer : an instance of PipelineFOVScorer in 'training' mode
        row : a row of self.md_raw
        dst_root : the root destination to which z-projections were saved in process_raw_tiff
        '''

        # construct the filepath to the DAPI z-projection
        filepath = self.dst_filepath(row, dst_root, kind='projections', channel='dapi', axis='z')
        filepath = self.tag_filepath(filepath, tag='DAPI-PROJ-Z', ext='tif')

        # calculate the features from the z-projection
        features = scorer.process_existing_fov(filepath)
        return features


    def aggregate_filepaths(self, dst_root, kind='metadata', tag='metadata-parsing-events', ext='csv'):
        '''
        Aggregate filepaths for a particular kind of processed file
        by generating these filepaths (which may not exist) from the rows of self.md_raw

        For now, `kind` and `tag` must match the corresponding kwargs 
        in the method that generated/will generate the processed files
        '''

        paths = []
        for _, row in self.md_raw.iterrows():
            path = self.dst_filepath(row, dst_root=dst_root, kind=kind)
            path = self.tag_filepath(path, tag=tag, ext=ext)
            paths.append(path)
            
        return paths


    def get_experiments(self, plate_id, well_id, group='original'):
        '''
        Get all of the experiment names for a given sample
        '''
        pass


    def get_filepaths(self, plate_id, well_id, group='original'):
        '''
        Parameters
        ----------
        plate_id : either a number or an id of the form 'P0001'
        well_id : a well_id of the form 'A1' or 'A01'
        group : the group or 'round' of imaging: 'original' | 'thawed' | 'all'
        '''
        pass


        
        

