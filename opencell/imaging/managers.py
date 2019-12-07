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


class PlateMicroscopyManager:
    '''
    This class organizes the methods that determine the plate_id, well_id, etc,
    for all of the raw images found in the 'PlateMicroscopy' directory

    '''

    def __init__(self, root_dir=None, cache_dir=None):
        
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

        # the trailing slash is required to correctly remove
        # the root_dir from the raw filepaths in construct_metadata
        self.root_dir = '%s%s' % (self.os_walk[0][0], os.sep)


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
        Parse well_id, site_num, and target name from a raw TIFF filename
        
        For almost all filenames, the format is '{well_id}_{site_num}_{target_name}.ome.tif'
        
        The exception is 'Jin' lines, which appear in plate6 and plate7;
        here, the format is '{well_id}_{site_num}_Jin_{well_id}_{target_name}.ome.tif',
        and it is the first well_id that is the 'real', pipeline-relevant, well_id
        
        Note that the target name sometimes includes the terminus that was tagged,
        in the form of a trailing '-N', '-C', '_N', '_C', '_Int', '-Int'

        Also, two target names include a trailing '-A' or '-B' 
        (these are 'HLA-A' and 'ARHGAP11A-B')
        '''
        
        well_id = '[A-H][1-9][0-2]?'
        site_num = '[1-9][0-9]?'
        target_name = r'[a-zA-Z0-9]+'
        appendix = r'[\-|_][a-zA-Z]+'
        raw_pattern = rf'^({well_id})_({site_num})_({target_name})({appendix})?.ome.tif$'

        # in Jin filenames, the second well_id is not relevant
        raw_jin_pattern = rf'^({well_id})_({site_num})_Jin_(?:{well_id})_({target_name})({appendix})?.ome.tif$'
        
        filename_was_parsed = False
        for pattern in [raw_pattern, raw_jin_pattern]:
            result = re.match(pattern, filename)
            if result:
                filename_was_parsed = True
                well_id, site_num, target_name, appendix = result.groups()
                break

        if not filename_was_parsed:
            return None

        site_num = int(site_num)
        return well_id, site_num, target_name


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

            # parse the plate_num and imaging round from the plate_dir
            plate_num, imaging_round_num = self.parse_src_plate_dir(path_dirs[0])
            plate_info = {
                'plate_num': plate_num,
                'imaging_round_num': imaging_round_num,
            }

            # create a row only for the path
            if paths_only:
                rows.append({**path_info, **plate_info})
                continue
            
            # create a row for each file
            for filename in filenames:
                rows.append({'filename': filename, **path_info, **plate_info})

        md = pd.DataFrame(data=rows)
        # d = d.replace(to_replace=np.nan, value='')

        # rename the subdirectory columns
        # (we know that there are always at most three of these columns)
        md = md.rename(columns={'level_0': 'plate_dir', 'level_1': 'exp_dir', 'level_2': 'exp_subdir'})

        # flag all of the raw files
        # these are all TIFF files in experiment dirs of the form '^ML[0-9]{4}_[0-9]{8}$'
        # (for example: 'ML0045_20181022')        
        md['is_raw'] = md.exp_dir.apply(lambda s: re.match('^ML[0-9]{4}_[0-9]{8}$', s) is not None)

        self.md = md


    @staticmethod
    def parse_src_plate_dir(src_plate_dir):
        '''
        Parse the plate number from a src plate_dir
        Example: 'mNG96wp19' -> '19'
        '''
        plate_num = int(re.findall('^mNG96wp([0-9]{1,2})', src_plate_dir.split(os.sep)[0])[0])

        # hackish way to determine the imaging round number from the plate_dir
        if 'Thawed2' in src_plate_dir:
            imaging_round_num = 3
        elif 'Thawed' in src_plate_dir:
            imaging_round_num = 2
        else:
            imaging_round_num = 1

        return plate_num, imaging_round_num


    def construct_raw_metadata(self):
        '''
        Construct the raw metadata (a subset of self.md)
        '''

        # use the is_raw flag
        md_raw = self.md.loc[self.md.is_raw].copy()

        for column in ['well_id', 'site_num', 'target_name', 'fov_id']:
            md_raw[column] = None
        
        dropped_inds = []
        # parse the well_id, site_num, and target_name from the filename,
        # and drop rows with unparseable filenames
        for ind, row in md_raw.iterrows():        
            result = self.parse_raw_tiff_filename(row.filename)
            if not result:
                if 'MMStack' not in row.filename:
                    print('Warning: unparseable raw filename %s' % row.filename)
                dropped_inds.append(ind)
                continue

            well_id, site_num, target_name = result
            md_raw.at[ind, 'site_num'] = site_num
            md_raw.at[ind, 'target_name'] = target_name
        
            # pad the well_id ('A1' -> 'A01')
            well_row, well_col = re.match('([A-H])([0-9]{1,2})', well_id).groups()
            md_raw.at[ind, 'well_id'] = '%s%02d' % (well_row, int(well_col))
    
        print('Warning: dropping %s rows of unparseable raw metadata' % len(dropped_inds))
        md_raw.drop(dropped_inds, inplace=True)

        #the parental_line is the same for all plates in PlateMicroscopy
        md_raw['parental_line'] = constants.PARENTAL_LINE_NAME

        # the electroporation ID is always the same
        # (since all plates have been electroporated once)
        md_raw['ep_id'] = 'EP01'

        # the ML experiment ID from the experiment directory name
        # (note that we already implicitly validated the form of the exp_dirs
        # in construct_metadata when we generated the is_raw column)
        md_raw['exp_id'] = [exp_dir.split('_')[0] for exp_dir in md_raw.exp_dir]

        # the PML ID, which denotes pipeline-ML microsopy acquisitions,
        # and which is what acqusitions are keyed on in the database
        md_raw['pml_id'] = [f'P{ml_id}' for ml_id in md_raw.exp_id]

        # plate_id, round_id, site_id
        md_raw['site_id'] = ['S%02d' % int(num) for num in md_raw.site_num]
        md_raw['plate_id'] = ['P%04d' % num for num in md_raw.plate_num]
        md_raw['imaging_round_id'] = ['R%02d' % num for num in md_raw.imaging_round_num]

        # reconstruct the raw filepath (relative to the PlateMicroscopy directory)
        for ind, row in md_raw.iterrows():
            md_raw.at[ind, 'raw_filepath'] = os.path.join(
                row.plate_dir, 
                row.exp_dir, 
                row.exp_subdir if not pd.isna(row.exp_subdir) else '',
                row.filename)
    
        # construct an fov_id that should be globally unique
        for ind, row in md_raw.iterrows():
            md_raw.at[ind, 'fov_id'] = '%s-%s-%s' % (row.exp_id, row.well_id, row.site_id)

        # drop non-unique fov_ids
        # TODO: consider removing this since it is redundant with database constraints
        n = md_raw.groupby('fov_id').count()
        degenerate_fov_ids = n.loc[n.filename > 1].index
        md_raw = md_raw.loc[~md_raw.fov_id.isin(degenerate_fov_ids)]
        print('Warning: dropping non-unique fov_ids %s' % list(degenerate_fov_ids))

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

