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


# hard-coded plate directory names of the 'original' image data
PLATE_DIR_NAMES = {'P%04d' % num: 'mNG96wp%d' % num for num in range(1, 20)}

# hard-coded plate directory names for 'thawed' image data
THAWED_PLATE_DIR_NAMES = {'P%04d' % num: 'mNG96wp%d_Thawed' % num for num in range(1, 20)}


class PlateMicroscopyAPI:

    
    def __init__(self, root_dir=None, cache_dir=None, partition=None):
        '''
        '''

        self.root_dir = root_dir
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

        self.cached_os_walk_filepath = os.path.join(self.cache_dir, 'os_walk.p')
        self.cached_metadata_filepath = os.path.join(self.cache_dir, 'all-metadata.csv')

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
    
        os_walk = list(os.walk(self.root_dir))
        with open(self.cached_os_walk_filepath, 'wb') as file:
            pickle.dump(os_walk, file)


    def load_cached_metadata(self):
        self.md = pd.read_csv(self.cached_metadata_filepath)
        self.construct_raw_metadata()


    def cache_metadata(self, overwrite=False):
        if not overwrite and os.path.isfile(self.cached_metadata_filepath):
            raise ValueError('Cached metadata already exists')
        self.md.to_csv(self.cached_metadata_filepath, index=False)


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
    def parse_raw_filename(filename):
        '''
        Parse well_id, fov_num, and target name from a raw TIFF filename
        
        For almost all filenames, the format is '{well_id}_{fov_num}_{target_name}.ome.tif'
        
        The exception is 'Jin' lines, which appear in plate6 and plate7;
        here, the format is '{well_id}_{fov_num}_Jin_{well_id}_{target_name}.ome.tif'
        
        (Note that this Jin-specific format is not adhered to 
        in the 'Updated_PublicationQuality' directories)
        '''
        
        filename = filename.split('.')[0]
        well_id = filename.split('_')[0]
        fov_num = filename.split('_')[1]
        target_name = filename.split('_')[2]
        
        if target_name == 'Jin':
            pass #gene_name = filename.split('_')[4]
        
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
            # 'mnG96wp{num}' or 'mNG96wp{num}_Thawed'
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
                file_info = {}
                try:
                    file_info = self.parse_raw_filename(filename)
                except:
                    print('Warning: unparse-able filename %s' % filename)
                rows.append({'filename': filename, **file_info, **path_info})

        md = pd.DataFrame(data=rows)
        # d = d.replace(to_replace=np.nan, value='')

        # rename the subdirectory columns
        # (we know that there are always at most three of these columns)
        md = md.rename(columns={'level_0': 'plate_dir', 'level_1': 'exp_dir', 'level_2': 'exp_subdir'})

        # parse the plate_num from the plate_dir
        md['plate_num'] = [re.findall('^mNG96wp([0-9]{1,2})', s.split(os.sep)[0])[0] for s in md.plate_dir]

        # the ML experiment ID
        md['exp_id'] = [exp_dir.split('_')[0] for exp_dir in md.exp_dir]

        # flag all of the raw files
        # these are all TIFF files in experiment dirs of the form '^ML[0-9]{4}_[0-9]{8}$'
        # (for example: 'ML0045_20181022')        
        md['is_raw'] = md.exp_dir.apply(lambda s: re.match('^ML[0-9]{4}_[0-9]{8}$', s) is not None)

        self.md = md
        self.construct_raw_metadata()


    def construct_raw_metadata(self):
        '''
        Construct the raw metadata (a subset of self.md)
        '''

        # use the is_raw flag
        md_raw = self.md.loc[self.md.is_raw].copy()

        # parse the ML experiment ID from the experiment directory name
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


    @staticmethod
    def dst_filepath(row, kind=None, channel=None, axis=None):
        '''
        Construct the relative directory path and filename for a 'kind' of output file

        The path is of the form {dst_root}/{dst_plate_dir}

        dst_plate_dir is of the form 'smNG-P0001-E01-R00'
        dst_filename is of the form '{dst_plate_dir}-ML0123-A01-S01-CLTA'

        Returns dst_dirpath and the dst_filename as a tuple
        (so that dst_dirpath can be created if it doesn't exist)

        '''

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
            subdir_names.extend([channel, 'PROJ%s' % axis])

        # parental line is always the mNeonGreen 1-10 line 
        # (here abbreviated 'smNG' for 'split mNeonGreen')
        parental_line = 'mNG'

        # the plate design ID
        plate_id = 'P%04d' % row.plate_num

        # the electroporation ID 
        # (always the same, since all plates have been electroporated once)
        ep_id = 'E01'

        # hackish way to determine the imaging round ID
        # (zero for the first, post-sorting round)
        if 'Thawed2' in row.plate_dir:
            imaging_round_id = 'R02'
        elif 'Thawed' in row.plate_dir:
            imaging_round_id = 'R01'
        else:
            imaging_round_id = 'R00'

        dst_plate_dir = f'{parental_line}-{plate_id}-{ep_id}-{imaging_round_id}'

        # construct the destination dirpath
        dst_dirpath = os.path.join(*subdir_names, dst_plate_dir)

        fov_id = '%02d' % int(row.fov_num)
        dst_filename = f'{dst_plate_dir}-{row.exp_id}-{row.well_id}-{fov_id}-{row.target_name}'
        
        return dst_dirpath, dst_filename


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


    def parse_raw_tiff_metadata(self, row, src_root, dst_root):
        '''
        Parse the metadata from a raw TIFF file

        row : a row of the `self.md_raw` dataframe
        src_root : the root of the 'PlateMicroscopy' directory
        dst_root : the destination 'oc-plate-microscopy' directory 
        '''

        src_filepath = self.src_filepath(row, src_root=src_root)

        # destination dirpath and filename (without file extension)
        dst_dirpath, dst_filename = self.dst_filepath(row, kind='metadata')
        dst_dirpath = os.path.join(dst_root, dst_dirpath)
        dst_filepath = os.path.join(dst_dirpath, dst_filename)
        os.makedirs(dst_dirpath, exist_ok=True)

        tiff = image.RawPipelineImage(src_filepath, verbose=False)
        tiff.parse_micromanager_metadata()
        tiff.validate_micromanager_metadata()

        # save the parsing events and parsed metadata
        path = self.tag_filepath(dst_filepath, tag='metadata-parsing-events', ext='csv')
        tiff.save_events(path)

        path = self.tag_filepath(dst_filepath, tag='mm-metadata', ext='csv')
        tiff.save_mm_metadata(path)

        path = self.tag_filepath(dst_filepath, tag='global-metadata', ext='json')
        tiff.save_global_metadata(path)


    def aggregate_filepaths(self, dst_root, kind='metadata', tag='metadata-parsing-events', ext='csv'):
        '''
        '''

        paths = []
        for _, row in self.md_raw.iterrows():
            path = os.path.join(dst_root, *self.dst_filepath(row, kind=kind))
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


        
        

