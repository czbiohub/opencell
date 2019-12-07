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


def parse_args():
    '''
    '''
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--src-root', 
        dest='src_root', 
        required=False, 
        default=ESS_ROOT)

    parser.add_argument(
        '--dst-root', 
        dest='dst_root', 
        required=False)

    parser.add_argument(
        '--cache-dir', 
        dest='cache_dir', 
        required=False)

    parser.add_argument(
        '--credentials-path', 
        dest='credentials_path', 
        required=False)
    
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
        '--process-tiffs', 
        dest='process_raw_tiffs', 
        action='store_true',
        required=False)

    parser.add_argument(
        '--aggregate-events', 
        dest='aggregate_processing_events', 
        action='store_true',
        required=False)

    parser.add_argument(
        '--calculate-features', 
        dest='calculate_fov_features', 
        action='store_true',
        required=False)

    parser.set_defaults(inspect_cached_metadata=False)
    parser.set_defaults(construct_metadata=False)
    parser.set_defaults(process_raw_tiffs=False)
    parser.set_defaults(aggregate_processing_events=False)
    parser.set_defaults(calculate_fov_features=False)

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


def add_all(session, rows):
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


def process_raw_tiffs(session, src_root, dst_root):
    '''
    Parse metadata from, and make projections for, all raw TIFFs

    Note that manager.process_raw_tiff returns a dict of raw tiff metadata,
    which we aggregate and save as a CSV

    TODO: figure out how to insert results into the database as they are generated
    (that is, within the method wrapped by dask.delayed)
    '''

    # get all FOVs in the MicroscopyFOV table of opencelldb
    fovs = session.query(models.MicroscopyFOV).all()
    processors = [RawZStackProcessor.from_database(fov) for fov in fovs]

    tasks = []
    for processor in processors:
        task = dask.delayed(processor.process_raw_tiff)(src_root, dst_root)
        tasks.append(task)
    all_raw_tiff_metadata = execute_tasks(tasks)

    # insert the results into the database
    results = []
    for processor, data in zip(processors, all_raw_tiff_metadata):
        data['fov_id'] = processor.fov.id
        results.append(
            models.MicroscopyFOVResult(fov=processor.fov, kind='raw-tiff-metadata', data=data))

    add_all(session, results)

    # cache the results
    pd.DataFrame(data=results).to_csv(os.path.join(dst_root, 'aggregated-raw-tiff-metadata.csv'), index=False)


def calculate_fov_features(session, dst_root):
    '''
    Calculate FOV (features used to generate FOV scores)

    TODO: a lot of this is a direct copy of process_raw_tiffs

    '''
    fov_scorer = PipelineFOVScorer(mode='training')
 
    fovs = session.query(models.MicroscopyFOV).all()
    processors = [RawZStackProcessor.from_database(fov) for fov in fovs]

    tasks = []
    for processor in processors:
        task = dask.delayed(processor.calculate_fov_features)(dst_root, fov_scorer)
        tasks.append(task)
    results = execute_tasks(tasks)

    # insert the results into the database
    results = []
    for processor, data in zip(processors, results):
        data['fov_id'] = processor.fov.id
        results.append(
            models.MicroscopyFOVResult(fov=processor.fov, kind='fov-features', data=data))

    add_all(session, results)

    # cache the features
    pd.DataFrame(data=results).to_csv(os.path.join(dst_root, 'aggregated-fov-features.csv'), index=False)


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
    results = execute_tasks(tasks)

    df = pd.concat([df for df in results if df is not None])
    df.to_csv(os.path.join(dst_root, 'aggregated-processing-events.csv'), index=False)


def main():

    args = parse_args()

    if args.credentials_path:
        url = db_utils.url_from_credentials(args.credentials_path)
        engine = sa.create_engine(url)
        Session = sa.orm.sessionmaker(bind=engine)
        session = Session()

    if args.inspect_cached_metadata:
        manager = PlateMicroscopyManager(args.src_root, args.cache_dir)
        inspect_cached_metadata(manager)

    if args.construct_metadata:
        manager = PlateMicroscopyManager(args.src_root, args.cache_dir)
        construct_and_cache_metadata(manager)

    if args.process_raw_tiffs:
        process_raw_tiffs(session, args.src_root, args.dst_root)

    if args.calculate_fov_features:
        calculate_fov_features(session, args.dst_root)

    if args.aggregate_processing_events:
        aggregate_processing_events(args.dst_root)

if __name__ == '__main__':
    main()
