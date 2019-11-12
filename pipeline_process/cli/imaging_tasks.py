import os
import re
import sys
import glob
import json
import dask
import shutil
import pickle
import hashlib
import skimage
import datetime
import tifffile
import argparse
import numpy as np
import pandas as pd

import dask.diagnostics

from pipeline_process.imaging import plate_microscopy_api


ESS_ROOT = '/gpfsML/ML_group/PlateMicroscopy/'


def parse_args():
    '''
    '''
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--src-dir', 
        dest='src_dir', 
        required=False, 
        default=ESS_ROOT)

    parser.add_argument(
        '--dst-dir', 
        dest='dst_dir', 
        required=True)

    parser.add_argument(
        '--cache-dir', 
        dest='cache_dir', 
        required=True)

    parser.add_argument(
        '--inspect', 
        dest='inspect_cached_metadata', 
        action='store_true',
        required=False)

    parser.add_argument(
        '--construct-metadata', 
        dest='construct_metadata', 
        action='store_true',
        required=False)

    parser.add_argument(
        '--process-raw-tiffs', 
        dest='process_raw_tiffs', 
        action='store_true',
        required=False)

    parser.add_argument(
        '--aggregate-parsed-metadata', 
        dest='aggregate_parsed_metadata', 
        action='store_true',
        required=False)

    parser.set_defaults(inspect_cached_metadata=False)
    parser.set_defaults(construct_metadata=False)
    parser.set_defaults(process_raw_tiffs=False)
    parser.set_defaults(aggregate_parsed_metadata=False)


    args = parser.parse_args()
    return args


@dask.delayed
def load_json(path):
    if not os.path.isfile(path):
        return None
    with open(path, 'r') as file:
        d = json.load(file)
    return d


@dask.delayed
def load_csv(path):
    if not os.path.isfile(path):
        return None
    df = pd.read_csv(path)
    df['filename'] = path.split(os.sep)[-1]
    df['plate_dir'] = path.split(os.sep)[-2]
    return df


def execute_tasks(tasks):

    with dask.diagnostics.ProgressBar():
        results = dask.compute(*tasks)
    return results


def construct_and_cache_metadata(src_dir, cache_dir):
    '''
    '''
    api = plate_microscopy_api.PlateMicroscopyAPI(src_dir, cache_dir)
    api.cache_os_walk()
    api.construct_metadata()
    api.append_file_info()
    api.cache_metadata(overwrite=True)


def inspect_cached_metadata(src_dir, cache_dir):
    '''
    '''
    api = plate_microscopy_api.PlateMicroscopyAPI(src_dir, cache_dir)
    print(f'''
        Total metadata rows:            {api.md.shape[0]}
        metadata.is_raw.sum():          {api.md.is_raw.sum()}
        Total parsed raw metadata rows: {api.md_raw.shape[0]}
    ''')


def process_raw_tiffs(src_dir, dst_dir, cache_dir):
    '''
    Parse metadata and make projections for all raw TIFFs
    '''
    api = plate_microscopy_api.PlateMicroscopyAPI(src_dir, cache_dir)

    tasks = []
    for _, row in api.md_raw.iterrows():
        task = dask.delayed(api.process_raw_tiff)(row, src_root=api.root_dir, dst_root=dst_dir)
        tasks.append(task)
    execute_tasks(tasks)


def aggregate_processing_events(api, dst_root):

    paths = api.aggregate_filepaths(
        dst_root, kind='metadata', tag='raw-tiff-processing-events', ext='csv')

    tasks = [load_csv(path) for path in paths]
    results = execute_tasks(tasks)

    df = pd.concat([df for df in results if df is not None])
    df.to_csv(os.path.join(dst_root, 'aggregated-processing-events.csv'), index=False)


def aggregate_raw_tiff_metadata(api, dst_root):

    paths = api.aggregate_filepaths(
        dst_root, kind='metadata', tag='raw-tiff-metadata', ext='json')

    tasks = [load_json(path) for path in paths]
    results = execute_tasks(tasks)

    df = pd.DataFrame(data=[d for d in results if d is not None])
    df.drop(labels=['ij_metadata'], axis=1, inplace=True)
    df.to_csv(os.path.join(dst_root, 'aggregated-raw-tiff-metadata.csv'), index=False)


def calculate_fov_features(api, dst_root, dragonfly_automation_path):

    sys.path.append(dragonfly_automation_path)
    from dragonfly_automation.fov_models import PipelineFOVScorer
    scorer = PipelineFOVScorer(mode='training')
 
    tasks = []
    for _, row in api.md_raw.iterrows():
        task = dask.delayed(api.calculate_fov_features)(row, dst_root, scorer)
        tasks.append(task)
    results = execute_tasks(tasks)

    pd.DataFrame(data=results).to_csv(dst_root, 'aggregated-fov-features.csv', index=False)


def main():
    args = parse_args()

    if args.inspect_cached_metadata:
        inspect_cached_metadata(args.src_dir, args.cache_dir)

    if args.construct_metadata:
        pass

    if args.process_raw_tiffs:
        inspect_cached_metadata(args.src_dir, args.cache_dir)
        process_raw_tiffs(args.src_dir, args.dst_dir, args.cache_dir)

    if args.aggregate_parsed_metadata:
        api = plate_microscopy_api.PlateMicroscopyAPI(args.src_dir, args.cache_dir)

        print('Aggregating processing events')
        aggregate_processing_events(api, args.dst_dir)

        print('Aggregating raw TIFF metadata')
        aggregate_raw_tiff_metadata(api, args.dst_dir)


if __name__ == '__main__':
    main()
