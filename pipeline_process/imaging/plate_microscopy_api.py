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

        # parse the ML experiment ID from the experiment directory name
        # (note that we already implicitly validated the form of the exp_dirs
        # in construct_metadata when we generated the is_raw flags)
        md_raw['exp_id'] = [exp_dir.split('_')[0] for exp_dir in md_raw.exp_dir]

        for column in ['well_id', 'site_num', 'target_name', 'fov_id']:
            md_raw[column] = None
        
        dropped_inds = []
        for ind, row in md_raw.iterrows():        

            # parse the well_id, site_num, and target_name from the filename
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

        # construct an fov_id that should be globally unique
        for ind, row in md_raw.iterrows():
            md_raw.at[ind, 'fov_id'] = '%s-%s-%s' % (row.exp_id, row.well_id, row.site_num)

        # drop non-unique fov_ids
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

        src_root = '' if src_root is None else src_root
        
        # exp_subdir can be missing
        exp_subdir = '' if pd.isna(row.exp_subdir) else row.exp_subdir

        src_filepath = os.path.join(src_root, row.plate_dir, row.exp_dir, exp_subdir, row.filename)
        return src_filepath

    
    def dst_plate_dir(self, row):
        '''
        Construct a dst plate_dir from an src plate_dir

        Destination plate directory names are of the form 'mNG-P0001-E01-R00'
        '''
        
        # parental line is always the mNeonGreen 1-10 line 
        # (here abbreviated 'mNG' for 'split mNeonGreen')
        parental_line = 'mNG'

        # the electroporation ID is always the same
        # (since all plates have been electroporated once)
        ep_id = 'E01'

        plate_id = 'P%04d' % row.plate_num
        imaging_round_id = 'R%02d' % row.imaging_round_num

        dst_plate_dir = f'{parental_line}-{plate_id}-{ep_id}-{imaging_round_id}'
        return dst_plate_dir


    def dst_filepath(self, row, dst_root=None, kind=None, channel=None, axis=None, makedirs=True):
        '''
        Construct the relative directory path and filename for a 'kind' of output file

        The path is of the form {kind}/{channel}/{axis}/{dst_plate_dir}

        dst_plate_dir is of the form 'mNG-P0001-E01-R01'
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
        dst_plate_dir = self.dst_plate_dir(row)

        # construct the destination dirpath
        dst_dirpath = os.path.join(dst_root, *subdir_names, dst_plate_dir)
        if makedirs:
            os.makedirs(dst_dirpath, exist_ok=True)
        
        # construct the destination filename
        site_id = 'S%02d' % int(row.site_num)
        dst_filename = f'{dst_plate_dir}-{row.exp_id}-{row.well_id}-{site_id}-{row.target_name}'
        
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

        # the tiff file must be manually closed
        tiff.tiff.close()

        # save the parsing events
        dst_filepath = self.dst_filepath(row, dst_root=dst_root, kind='metadata')
        events_path = self.tag_filepath(dst_filepath, tag='raw-tiff-processing-events', ext='csv')
        tiff.save_events(events_path)

        # append the fov_id to the tiff metadata
        tiff_metadata = tiff.global_metadata
        tiff_metadata['fov_id'] = row.fov_id
        return tiff_metadata


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
        features['fov_id'] = row.fov_id
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


        
        

