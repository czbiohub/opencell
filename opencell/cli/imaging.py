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

import sqlalchemy as sa
import dask.diagnostics

from opencell.database import models, operations
from opencell.database import utils as db_utils
from opencell.imaging.managers import PlateMicroscopyManager
from opencell.imaging.processors import RawZStackProcessor

try:
    sys.path.append('/Users/keith.cheveralls/projects/dragonfly-automation')
    from dragonfly_automation.fov_models import PipelineFOVScorer
except ImportError:
    sys.path.append('/home/projects/dragonfly-automation')
    from dragonfly_automation.fov_models import PipelineFOVScorer
    
# the location of the PlateMicroscopy directory on our ESS partition from `cap`
ESS_ROOT = '/gpfsML/ML_group/PlateMicroscopy/'

def timestamp():
    return datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')


def parse_args():
    '''
    '''
    parser = argparse.ArgumentParser()

    parser.add_argument(dest='src_root', default=ESS_ROOT)
    parser.add_argument(dest='dst_root')

    parser.add_argument(
        '--cache-dir', 
        dest='cache_dir', 
        required=False)

    # path to credentials JSON
    parser.add_argument(
        '--credentials', 
        dest='credentials', 
        required=False)
    
    # CLI args whose presence in the command sets them to True
    action_arg_names = [
        'inspect_cached_metadata', 
        'construct_metadata', 
        'process_raw_tiffs', 
        'aggregate_processing_events',
        'calculate_fov_features',
    ]

    for arg_name in action_arg_names:
        parser.add_argument(
            '--%s' % arg_name.replace('_', '-'), 
            dest=arg_name,
            action='store_true',
            required=False)

    for arg_name in action_arg_names:
        parser.set_defaults(**{arg_name: False})

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


def _execute_tasks(tasks):
    with dask.diagnostics.ProgressBar():
        results = dask.compute(*tasks)
    return results


def _add_all(session, rows):
    try:
        session.add_all(rows)
        session.commit()
    except Exception as exception:
        session.rollback()
        print('Error in add_all: %s' % str(exception))


def construct_and_cache_metadata(manager):
    '''
    '''
    print('Caching os.walk results')
    if not hasattr(manager, 'os_walk'):
        manager.cache_os_walk()

    print('Constructing metadata')    
    manager.construct_metadata()

    print('Appending file info')
    # manager.append_file_info()

    print('Constructing raw metadata')
    manager.construct_raw_metadata()

    print('Caching metadata')
    manager.cache_metadata(overwrite=True)


def inspect_cached_metadata(manager):
    '''
    '''
    print(f'''
        All metadata rows:          {manager.md.shape[0]}
        metadata.is_raw.sum():      {manager.md.is_raw.sum()}
        Parsed raw metadata rows:   {manager.md_raw.shape[0]}
    ''')


class FOVTaskManager:

    def __init__(self, credentials, src_root=None, dst_root=None):

        self.src_root = src_root
        self.dst_root = dst_root
        self.db_url = db_utils.url_from_credentials(credentials)

        with operations.orm_session(self.db_url) as session:
            fovs = session.query(models.MicroscopyFOV).all()
            processors = [RawZStackProcessor.from_database(fov) for fov in fovs]
        self.processors = processors


    def do_tasks(self, task_name, result_name):
        '''
        Parse metadata from, and make projections for, all raw TIFFs

        Note that manager.process_raw_tiff returns a dict of raw tiff metadata,
        which we aggregate and save as a CSV

        TODO: figure out how to insert results into the database as they are generated
        (that is, within the method wrapped by dask.delayed)
        '''

        tasks = []

        if task_name == 'process-raw-tiffs':
            for processor in self.processors:
                task = dask.delayed(processor.process_raw_tiff)(self.src_root, self.dst_root)
                tasks.append(task)

        if task_name == 'calculate-fov-features':
            fov_scorer = PipelineFOVScorer(mode='training')
            for processor in self.processors:
                task = dask.delayed(processor.calculate_fov_features)(self.dst_root, fov_scorer)
                tasks.append(task)

        # perform the tasks (using dask.compute)
        task_results = _execute_tasks(tasks)

        # cache the results locally
        cache_filepath = os.path.join(self.dst_root, '%s_%s.csv' % (timestamp(), result_name))
        pd.DataFrame(data=task_results).to_csv(cache_filepath, index=False)
        print('Saved %s results to %s' % (task_name, cache_filepath))

        print('Inserting %s results into the database' % task_name)
        fov_results = []
        for task_result in task_results:
            fov_results.append(
                models.MicroscopyFOVResult(fov_id=task_result['fov_id'], kind=result_name, data=task_result))

        with operations.orm_session(self.db_url) as session:
            _add_all(session, fov_results)


def aggregate_processing_events(dst_root):
    '''
    'Processing events' are events/errors that occurred in micromanager.RawPipelineTIFF
    (which is called by process_raw_tiffs)

    TODO: refactor this to eliminate the dependence on manager.aggregate_filepaths,
    which no longer exists

    '''
    # paths = manager.aggregate_filepaths(
    #     dst_root, kind='metadata', tag='raw-tiff-processing-events', ext='csv')

    paths = []
    tasks = [load_csv(path) for path in paths]
    results = _execute_tasks(tasks)

    df = pd.concat([df for df in results if df is not None])
    df.to_csv(os.path.join(dst_root, 'aggregated-processing-events.csv'), index=False)


def main():

    args = parse_args()

    if args.inspect_cached_metadata:
        manager = PlateMicroscopyManager(args.src_root, args.cache_dir)
        inspect_cached_metadata(manager)

    if args.construct_metadata:
        manager = PlateMicroscopyManager(args.src_root, args.cache_dir)
        construct_and_cache_metadata(manager)

    if args.process_raw_tiffs:
        task_manager = FOVTaskManager(args.credentials, src_root=args.src_root, dst_root=args.dst_root)
        task_manager.do_tasks(task_name='process-raw-tiffs', result_name='raw-tiff-metadata')

    if args.calculate_fov_features:
        task_manager = FOVTaskManager(args.credentials, src_root=args.src_root, dst_root=args.dst_root)
        task_manager.do_tasks(task_name='calculate-fov-features', result_name='fov-features')

    if args.aggregate_processing_events:
        aggregate_processing_events(args.dst_root)


if __name__ == '__main__':
    main()
