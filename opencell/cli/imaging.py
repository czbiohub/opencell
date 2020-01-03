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
from opencell.imaging.processors import FOVProcessor
from opencell.imaging.managers import PlateMicroscopyManager

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
        'process_raw_tiff', 
        'calculate_fov_features',
        'crop_cell_layer',
        'generate_nrrd',
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
        pcl_ops.insert_microscopy_fovs(session, group_metadata, errors=errors)

    
@dask.delayed
def do_fov_task(
    Session, 
    fov_processor, 
    fov_operator, 
    processor_method_name, 
    processor_method_kwargs,
    operator_method_name):
    '''
    fov_processor : an instance of the imaging.processor.FOVProcessor class
    fov_operator : an instance of the database.operations.MicroscopyFOVOperations class
    '''

    error_log = {'fov_id': fov_processor.fov_id, 'method': processor_method_name}

    # attempt to call the processing method
    try:
        result = getattr(fov_processor, processor_method_name)(**processor_method_kwargs)
    except Exception as error:
        error_log['processing_error'] = str(error)
        return error_log

    # attempt to insert the processing result into the database
    try:
        getattr(fov_operator, operator_method_name)(Session(), result)
    except Exception as error:
        error_log['database_error'] = str(error)

    return error_log



def do_fov_tasks(Session, method_name, method_kwargs, fovs=None):
    '''
    Call a method of FOVProcessor on all, or a subset of, the raw FOVs

    Parameters
    ----------
    method_name : the name of the FOVProcessor method to call
    method_kwargs : the kwargs for the method (no args are allowed)
    fovs : optional list of FOVs to be processed (if None, all FOVs are processed)

    TODO: handle multiple source directories 
    (that is, plate_microscopy_dir and dragonfly_automation_dir)

    TODO: logic to skip already-processed FOVs
    '''

    # valid methods and their corresponding FOVOperations method
    method_defs = {
        'process_raw_tiff': 'insert_raw_tiff_metadata',
        'calculate_fov_features': 'insert_fov_features',
        'crop_corner_rois': 'insert_rois',
        'crop_best_roi': 'insert_rois',
        'generate_thumbnails': 'insert_thumbnails',
        'generate_ijclean': 'insert_ijclean',
    }

    # the name of the FOVOperations method that inserts the results of the processor method
    operator_method_name = method_defs.get(method_name)

    # if a list of FOVs was not provided, select all FOVs
    if fovs is None:
        fovs = Session.query(models.MicroscopyFOV).all()

    # instantiate a processor and operations class for each FOV
    # (note the awkward nomenclature mismatch here; 
    # we call an instance of the FOVOperations class an `fov_operator`)
    fov_processors = [FOVProcessor.from_database(fov) for fov in fovs]
    fov_operators = [operations.MicroscopyFOVOperations(fov.id) for fov in fovs]

    # create the dask tasks
    tasks = []
    for fov_processor, fov_operator in zip(fov_processors, fov_operators):
        task = do_fov_task(
            Session, fov_processor, fov_operator, method_name, method_kwargs, operator_method_name)
        tasks.append(task)

    # do the tasks
    with dask.diagnostics.ProgressBar():
        error_logs = dask.compute(*tasks)

    # cache the errors locally if possible
    # TODO: check whether any errors actually occurred
    dst_root = method_kwargs.get('dst_root')
    if dst_root is not None:
        cache_filepath = os.path.join(dst_root, '%s_%s-errors.csv' % (timestamp(), method_name))
        pd.DataFrame(data=error_logs).to_csv(cache_filepath, index=False)
        print('Saved %s errors to %s' % (method_name, cache_filepath))



def main():

    args = parse_args()

    # create a scoped_session for opencell database
    if args.credentials:
        db_url = db_utils.url_from_credentials(args.credentials)
        engine = sa.create_engine(db_url)
        session_factory = sa.orm.sessionmaker(bind=engine)
        Session = sa.orm.scoped_session(session_factory)

    # inspect cached plate microscopy metadata
    if args.inspect_plate_microscopy_metadata:
        manager = PlateMicroscopyManager(args.plate_microscopy_dir, args.cache_dir)
        inspect_plate_microscopy_metadata(manager)

    # construct PlateMicroscopy metadata
    if args.construct_plate_microscopy_metadata:
        manager = PlateMicroscopyManager(args.plate_microscopy_dir, args.cache_dir)
        construct_plate_microscopy_metadata(manager)

    # insert PlateMicroscopy metadata into the database
    if args.insert_plate_microscopy_metadata:
        with operations.session_scope(db_url) as session:
            insert_plate_microscopy_metadata(session, cache_dir=args.cache_dir, errors='warn')


    # process all raw tiffs (and parse micromanager metadata)
    if args.process_raw_tiff:
        method_name = 'process_raw_tiff'
        method_kwargs = {
            'dst_root': args.dst_root,
            'src_root': args.plate_microscopy_dir,
        }

        try:
            do_fov_tasks(Session, method_name, method_kwargs)
        except Exception as error:
            with open(os.path.join(args.dst_root, '%s_%s_error.log' % (timestamp(), method_name)), 'w') as file:
                file.write(str(error))


    # calculate FOV features and score
    if args.calculate_fov_features:

        # load and train the FOV scorer 
        # (note the dependence on the path to dragonfly-automation repo)
        fov_scorer = PipelineFOVScorer(mode='training')
        fov_scorer.load(os.path.join(DRAGONFLY_REPO, 'models', '2019-10-08'))
        fov_scorer.train()

        method_name = 'calculate_fov_features'
        method_kwargs = {
            'dst_root': args.dst_root,
            'fov_scorer': fov_scorer,
        }
        do_fov_tasks(Session, method_name, method_kwargs)


    if args.crop_cell_layer:
        method_name = 'crop_cell_layer'
        method_kwargs = {
            'dst_root': args.dst_root,
            'src_root': args.plate_microscopy_dir,
        }
        try:
            do_fov_tasks(Session, method_name, method_kwargs)
        except Exception as error:
            with open(os.path.join(args.dst_root, '%s_%s_error.log' % (timestamp(), method_name)), 'w') as file:
                file.write(str(error))


    if args.generate_nrrd:
        method_name = 'generate_nrrd'
        method_kwargs = {
            'dst_root': args.dst_root,
        }
        try:
            do_fov_tasks(Session, method_name, method_kwargs)
        except Exception as error:
            with open(os.path.join(args.dst_root, '%s_%s_error.log' % (timestamp(), method_name)), 'w') as file:
                file.write(str(error))


if __name__ == '__main__':
    main()
