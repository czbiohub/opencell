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
            filenames = [name for name in filenames if '.tif' in name]
            if not filenames:
                continue
            
            # only include 'mnG96wp{num}' or 'mNG96wp{num}_Thawed'
            rel_path = path.replace(self.root_dir, '')
            if not re.match('^mNG96wp[1-9]([0-9])?(_Thawed|/)', rel_path):
                continue
                
            path_dirs = rel_path.split(os.sep)
            path_info = {'level_%d' % ind: path_dir for ind, path_dir in enumerate(path_dirs)}
            if paths_only:
                rows.append(path_info)
            else:
                for filename in filenames:
                    file_info = {}
                    try:
                        file_info = self.parse_raw_filename(filename)
                    except:
                        print('Warning: unparse-able filename %s' % filename)
                    rows.append({'filename': filename, **file_info, **path_info})

        md = pd.DataFrame(data=rows)
        # d = d.replace(to_replace=np.nan, value='')

        # rename subdirectory columns
        md = md.rename(columns={'level_0': 'plate_dir', 'level_1': 'exp_dir', 'level_2': 'exp_subdir'})

        # parse plate_num from plate_dir
        md['plate_num'] = [re.findall('^mNG96wp([0-9]{1,2})', s.split(os.sep)[0])[0] for s in md.plate_dir]

        self.md = md


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


    def raw_metadata(self):
        '''
        All raw z-stacks - these are all TIFF files 
        in experiment dirs of the form '^ML[0-9]{4}_[0-9]{8}$'
        For example: 'ML0045_20181022'
        '''
        d_raw = self.md.loc[self.md.exp_dir.apply(
            lambda s: re.match('^ML[0-9]{4}_[0-9]{8}$', s) is not None)].copy()
        return d_raw


    @staticmethod
    def make_projections(row, src_root, dst_root):
        '''
        Project all of the raw z-stacks

        row : a row of raw metadata
        src_root : the root of the PlateMicroscopy directory
        dst_root : the directory in which to save projections
        '''

        def add_tag(filepath, tag):
            return filepath.replace('.tif', '_%s.tif' % tag)

        src_filepath = os.path.join(src_root, row.plate_dir, row.exp_dir)
        if not pd.isna(row.exp_subdir):
            src_filepath = os.path.join(src_filepath, row.exp_subdir)
        src_filepath = os.path.join(src_filepath, row.filename)
        
        dst_dir = os.path.join(dst_root, row.plate_dir)
        dst_filename = 'P%04d_%s_%s' % (row.plate_num, row.exp_dir, row.filename)

        os.makedirs(dst_dir, exist_ok=True)
        dst_filepath = os.path.join(dst_dir, dst_filename.replace('.ome', ''))

        # hackish way to check whether we've already processed this stack
        # (GFP_YPROJ is the last projection saved below)
        if os.path.isfile(add_tag(dst_filepath, 'GFP_YPROJ')):
            return

        # note: important to use skimage's tifffile, and not the stand-alone package,
        # to avoid errors that occur when loading some stacks with tifffile itself
        # (these errors appear to be related to invalid TIFF metadata tags)
        # (example: 'E7_9_RAB14.ome.tif' in 'mNG96wp1_Thawed')
        im = skimage.external.tifffile.imread(src_filepath) 

        # some stacks are shape (z, channel, x, y) and some are (z, x, y) 
        if len(im.shape) == 4:
            dapi_stack = im[:, 0, :, :]
            gfp_stack = im[:, 1, :, :]
        else:
            nslices = int(im.shape[0]/2)
            dapi_stack = im[:nslices, :, :]
            gfp_stack = im[nslices:, :, :]  

        tifffile.imsave(add_tag(dst_filepath, 'DAPI_ZPROJ'), dapi_stack.max(axis=0))
        tifffile.imsave(add_tag(dst_filepath, 'GFP_ZPROJ'), gfp_stack.max(axis=0))
        
        tifffile.imsave(add_tag(dst_filepath, 'DAPI_XPROJ'), dapi_stack.max(axis=1))
        tifffile.imsave(add_tag(dst_filepath, 'GFP_XPROJ'), gfp_stack.max(axis=1))
        
        tifffile.imsave(add_tag(dst_filepath, 'DAPI_YPROJ'), dapi_stack.max(axis=2))
        tifffile.imsave(add_tag(dst_filepath, 'GFP_YPROJ'), gfp_stack.max(axis=2))
        
        return im.shape


    def make_all_projections(self):
        pass


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


        
        

