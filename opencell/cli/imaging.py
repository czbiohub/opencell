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
    DRAGONFLY_REPO ='/Users/keith.cheveralls/projects/dragonfly-automation' 
    sys.path.append(DRAGONFLY_REPO)
    from dragonfly_automation.fov_models import PipelineFOVScorer
except ImportError:
    DRAGONFLY_REPO = '/gpfsML/ML_group/KC/projects/dragonfly-automation'
    sys.path.append(DRAGONFLY_REPO)
    from dragonfly_automation.fov_models import PipelineFOVScorer
    

def timestamp():
    return datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')


def parse_args():
    '''
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument(dest='dst_root')

    # the location of the PlateMicroscopy directory
    parser.add_argument(
        '--plate-microscopy-dir',
        dest='plate_microscopy_dir')

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
        'inspect_plate_microscopy_metadata', 
        'construct_plate_microscopy_metadata', 
        'insert_plate_microscopy_metadata',
        'process_raw_tiffs', 
        'calculate_fov_features',
        'aggregate_processing_events',
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


def do_dask_tasks(tasks):
    with dask.diagnostics.ProgressBar():
        results = dask.compute(*tasks)
    return results


def construct_plate_microscopy_metadata(plate_microscopy_manager):
    '''
    '''
    print('Caching os.walk results')
    if not hasattr(plate_microscopy_manager, 'os_walk'):
        plate_microscopy_manager.cache_os_walk()

    print('Constructing metadata')    
    plate_microscopy_manager.construct_metadata()

    print('Constructing raw metadata')
    plate_microscopy_manager.construct_raw_metadata()

    print('Caching metadata')
    plate_microscopy_manager.cache_metadata(overwrite=True)


def inspect_plate_microscopy_metadata(plate_microscopy_manager):
    '''
    '''
    print(f'''
        All metadata rows:          {plate_microscopy_manager.md.shape[0]}
        metadata.is_raw.sum():      {plate_microscopy_manager.md.is_raw.sum()}
        Parsed raw metadata rows:   {plate_microscopy_manager.md_raw.shape[0]}
    ''')


def insert_plate_microscopy_metadata(session, cache_dir=None, errors='warn'):
    '''
    Insert all raw FOVs from the PlateMicroscopy directory

    To speed things up, we group the FOVs by (plate_id, well_id)
    so that all FOVs for each cell_line are inserted together

    cache_dir : local directory in which the results of calling os.walk
        on the PlateMicroscopy directory are cached
    '''

    pm = PlateMicroscopyManager(cache_dir=cache_dir)

    # generate the raw metadata
    pm.construct_metadata()
    pm.construct_raw_metadata()
    metadata = pm.md_raw.groupby(['plate_id', 'well_id'])

    plate_id = None
    for group in metadata.groups:
        if plate_id is None or group[0] != plate_id:
            print('Inserting %s' % group[0])
        plate_id, well_id = group

        try:
            pcl_ops = operations.PolyclonalLineOperations.from_plate_well(session, plate_id, well_id)
        except:
            print('No polyclonal line for (%s, %s)' % group)
            continue

        group_metadata = metadata.get_group(group)
        pcl_ops.insert_microscopy_fovs(session, group_metadata, errors='ignore')


def do_fov_tasks(session, method_name, method_kwargs):
    '''
    Call a method of FOVProcessor on all, or a subset of, the raw FOVs

    TODO: figure out how to insert results into the database as they are generated
    (that is, within the method wrapped by dask.delayed)

    TODO: handle multiple source directories 
    (that is, plate_microscopy_dir and dragonfly_automation_dir)

    TODO: logic to skip already-processed FOVs

    NOTE: the method called must return a JSON-safe dict of 'results' that includes the fov_id,
    because we need this id to insert the results into the database
    (because the results are generated in parallel and then inserted afterwards, all at once)

    '''

    tasks = []
    fovs = session.query(models.MicroscopyFOV).all()
    processors = [RawZStackProcessor.from_database(fov) for fov in fovs]
    
    for processor in processors:
        task = dask.delayed(getattr(processor, method_name))(**method_kwargs)
        tasks.append(task)

    # perform the tasks (using dask.compute)
    task_results = do_dask_tasks(tasks)

    # cache the results locally is possible
    dst_root = method_kwargs.get('dst_root')
    if dst_root is not None:
        cache_filepath = os.path.join(dst_root, '%s_%s-results.csv' % (timestamp(), method_name))
        pd.DataFrame(data=task_results).to_csv(cache_filepath, index=False)
        print('Saved %s results to %s' % (method_name, cache_filepath))

    print('Inserting %s results into the database' % method_name)
    fov_results = []
    for task_result in task_results:
        fov_results.append(
            models.MicroscopyFOVResult(fov_id=task_result['fov_id'], method_name=method_name, data=task_result))

    operations.add_all(session, fov_results)


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
    results = do_dask_tasks(tasks)

    df = pd.concat([df for df in results if df is not None])
    df.to_csv(os.path.join(dst_root, 'aggregated-processing-events.csv'), index=False)


def main():

    args = parse_args()

    db_url = None
    if args.credentials:
        db_url = db_utils.url_from_credentials(args.credentials)

    if args.inspect_plate_microscopy_metadata:
        manager = PlateMicroscopyManager(args.plate_microscopy_dir, args.cache_dir)
        inspect_plate_microscopy_metadata(manager)

    if args.construct_plate_microscopy_metadata:
        manager = PlateMicroscopyManager(args.plate_microscopy_dir, args.cache_dir)
        construct_plate_microscopy_metadata(manager)

    if args.insert_plate_microscopy_metadata:
        with operations.session_scope(db_url) as session:
            insert_plate_microscopy_metadata(session, cache_dir=args.cache_dir, errors='warn')

    if args.process_raw_tiffs:
        method_name = 'process_raw_tiff'
        method_kwargs = {
            'dst_root': args.dst_root,
            'src_root': args.plate_microscopy_dir,
        }
        try:
            with operations.session_scope(db_url) as session:
                do_fov_tasks(session, method_name, method_kwargs)
        except Exception as error:
            with open(os.path.join(args.dst_root, '%s_process_raw_tiffs_error.log' % timestamp()), 'w') as file:
                file.write(str(error))

    if args.calculate_fov_features:

        # load the FOV scorer (note the dependence on the path to dragonfly-automation repo)
        fov_scorer = PipelineFOVScorer(mode='prediction')
        fov_scorer.load(os.path.join(DRAGONFLY_REPO, 'models', '2019-10-08'))
        fov_scorer.train()

        method_name = 'calculate_fov_scores'
        method_kwargs = {
            'dst_root': args.dst_root,
            'fov_scorer': fov_scorer,
        }
        with operations.session_scope(db_url) as session:
            do_fov_tasks(session, method_name, method_kwargs)


if __name__ == '__main__':
    main()
