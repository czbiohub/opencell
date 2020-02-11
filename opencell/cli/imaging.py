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
    DRAGONFLY_REPO = '/Users/keith.cheveralls/projects/dragonfly-automation'
    sys.path.append(DRAGONFLY_REPO)
    from dragonfly_automation.fov_models import PipelineFOVScorer
except ImportError:
    DRAGONFLY_REPO = '/gpfsML/ML_group/KC/projects/dragonfly-automation'
    sys.path.append(DRAGONFLY_REPO)
    try:
        from dragonfly_automation.fov_models import PipelineFOVScorer
    except ImportError:
        PipelineFOVScorer = None


def timestamp():
    return datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')


def parse_args():
    '''
    '''
    parser = argparse.ArgumentParser()

    # the location of the 'opencell-microscopy' directory
    parser.add_argument('--dst-root', dest='dst_root')

    # the location of the PlateMicroscopy directory
    parser.add_argument('--plate-microscopy-dir', dest='plate_microscopy_dir')

    # the location of the raw-pipeline-microscopy directory
    parser.add_argument('--raw-pipeline-microscopy-dir', dest='raw_pipeline_microscopy_dir')

    # the pml_id whose FOVs are to be inserted or processed
    parser.add_argument('--pml-id', dest='pml_id')

    # the location of the directory in which to cache the PlateMicroscopy metadata
    parser.add_argument('--cache-dir', dest='cache_dir', required=False)

    # path to JSON file with database credentials
    parser.add_argument('--credentials', dest='credentials', required=False)

    # FOV thumbnail scale and quality
    parser.add_argument('--thumbnail-scale', dest='thumbnail_scale', required=False)
    parser.add_argument('--thumbnail-quality', dest='thumbnail_quality', required=False)

    # CLI args whose presence in the command sets them to True
    action_arg_dests = [
        'inspect_plate_microscopy_metadata',
        'construct_plate_microscopy_metadata',
        'insert_plate_microscopy_fovs',
        'insert_fovs',
        'process_raw_tiffs',
        'calculate_fov_features',
        'generate_fov_thumbnails',
        'calculate_z_profiles',
        'generate_clean_tiffs',
        'crop_corner_rois',
        'process_all_fovs',
    ]

    for dest in action_arg_dests:
        flag = '--%s' % dest.replace('_', '-')
        parser.add_argument(flag, dest=dest, action='store_true', required=False)
        parser.set_defaults(**{dest: False})

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


def insert_plate_microscopy_fovs(session, cache_dir=None, errors='warn'):
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
        group_metadata = metadata.get_group(group)

        try:
            pcl_ops = operations.PolyclonalLineOperations.from_plate_well(session, plate_id, well_id)
        except Exception:
            print('No polyclonal line for (%s, %s)' % group)
            continue
        pcl_ops.insert_microscopy_fovs(session, group_metadata, errors=errors)


def insert_raw_pipeline_microscopy_fovs(session, root_dir, pml_id, errors='warn'):
    '''
    Insert all raw FOVs from a single raw-pipeline-microscopy dataset

    (Note that there is substantial code duplication between this method
    and insert_plate_microscopy_fovs above)

    root_dir : the path to the 'raw-pipeline-microscopy' directory
    pml_id : the ID of the dataset whose FOVs are to be inserted
    '''

    metadata = pd.read_csv(os.path.join(root_dir, pml_id, 'fov-metadata.csv'))

    # drop rows that were manually flagged
    if np.any(metadata.manually_flagged):
        print('Warning: dropping %s manually flagged FOVs' % metadata.manually_flagged.sum())
        metadata = metadata.loc[~metadata.manually_flagged]
    print('Inserting %s FOVs from %s' % (metadata.shape[0], pml_id))

    # the filepath to the raw TIFF file
    metadata['raw_filepath'] = [
        os.path.join(row.src_dirpath, row.src_filename) for ind, row in metadata.iterrows()]

    metadata = metadata.groupby(['plate_id', 'pipeline_well_id'])
    for group in metadata.groups:
        plate_id, well_id = group
        group_metadata = metadata.get_group(group)
        try:
            pcl_ops = operations.PolyclonalLineOperations.from_plate_well(session, plate_id, well_id)
        except Exception:
            print('No polyclonal line for (%s, %s)' % group)
            continue
        pcl_ops.insert_microscopy_fovs(session, group_metadata, errors=errors)


@dask.delayed
def do_fov_task(
    Session,
    fov_processor,
    fov_operator,
    processor_method_name,
    processor_method_kwargs,
    operator_method_name
):
    '''
    fov_processor : an instance of the imaging.processor.FOVProcessor class
    fov_operator : an instance of the database.operations.MicroscopyFOVOperations class
    '''

    error_log = {'fov_id': fov_processor.fov_id, 'method': processor_method_name}

    # attempt to call the processing method
    try:
        result = getattr(fov_processor, processor_method_name)(**processor_method_kwargs)
    except Exception as error:
        error_log['kind'] = 'processing'
        error_log['message'] = str(error)
        return error_log

    # attempt to insert the processing result into the database
    try:
        getattr(fov_operator, operator_method_name)(Session(), result)
    except Exception as error:
        error_log['kind'] = 'database'
        error_log['message'] = str(error)
    return error_log



def do_fov_tasks(Session, args, processor_method_name, processor_method_kwargs, fovs=None):
    '''
    Call a method of FOVProcessor on all, or a subset of, the raw FOVs

    Parameters
    ----------
    Session :
    args : the parsed command-line arguments
        (from which we obtain the paths to the 'plat_microscopy' and 'raw_pipeline_microscopy' dirs)
    processor_method_name : the name of the FOVProcessor method to call
    processor_method_kwargs : the kwargs for the method (no args are allowed)
    fovs : optional list of FOVs to be processed (if None, all FOVs are processed)

    TODO: logic to skip already-processed FOVs
    '''

    # the FOVOperations method corresponding to each FOVProcessor method
    operator_method_names = {
        'process_raw_tiff': 'insert_raw_tiff_metadata',
        'calculate_fov_features': 'insert_fov_features',
        'generate_fov_thumbnails': 'insert_fov_thumbnails',
        'calculate_z_profiles': 'insert_z_profiles',
        'generate_clean_tiff': 'insert_clean_tiff_metadata',
        'crop_corner_rois': 'insert_corner_rois',
    }

    # the name of the FOVOperations method that inserts the results of the processor method
    operator_method_name = operator_method_names.get(processor_method_name)

    # if a list of FOVs was not provided, select all FOVs
    if fovs is None:
        fovs = Session.query(models.MicroscopyFOV).all()

    if not len(fovs):
        print('There are no FOVs to be processed')

    # instantiate a processor and operations class for each FOV
    # (note the awkward nomenclature mismatch here;
    # we call an instance of the FOVOperations class an `fov_operator`)
    fov_processors = [FOVProcessor.from_database(fov) for fov in fovs]
    fov_operators = [operations.MicroscopyFOVOperations(fov.id) for fov in fovs]

    # set the src_roots
    for fov_processor in fov_processors:
        fov_processor.set_src_roots(
            plate_microscopy_dir=args.plate_microscopy_dir,
            raw_pipeline_microscopy_dir=args.raw_pipeline_microscopy_dir)

    # create the dask tasks
    tasks = []
    for fov_processor, fov_operator in zip(fov_processors, fov_operators):
        task = do_fov_task(
            Session,
            fov_processor,
            fov_operator,
            processor_method_name,
            processor_method_kwargs,
            operator_method_name)
        tasks.append(task)

    # do the tasks
    print("Running method '%s' on %s FOVs" % (processor_method_name, len(fovs)))
    with dask.diagnostics.ProgressBar():
        errors = dask.compute(*tasks)

    # cache the errors locally if possible
    errors = pd.DataFrame(data=errors).dropna()
    if 'message' in list(errors.columns):
        print("Errors occurred while running method '%s'" % processor_method_name)
        if args.dst_root is not None:
            cache_filepath = os.path.join(args.dst_root, '%s_%s-errors.csv' %
                (timestamp(), processor_method_name))
            errors.to_csv(cache_filepath, index=False)
            print("Error log was saved to %s" % cache_filepath)
        else:
            print('Argument `dst_root` was not specified, so no error log was saved')
    else:
        print("No errors occurred while running method '%s'" % processor_method_name)


def get_unprocessed_fovs(engine, session, result_kind):
    '''
    Retrieve all FOV instances without any results of the specified kind
    in the MicroscopyFOVResult table
    '''

    query = '''
        select fov.*, res.kind as kind from microscopy_fov fov
        left join (select * from microscopy_fov_result where kind = '%s') res
        on fov.id = res.fov_id
        where kind is null;'''

    d = pd.read_sql(query % result_kind, engine)
    unprocessed_fovs = (
        session.query(models.MicroscopyFOV)
        .filter(models.MicroscopyFOV.id.in_(list(d.id)))
        .all()
    )
    return unprocessed_fovs


def main():

    args = parse_args()

    if args.dst_root:
        os.makedirs(args.dst_root, exist_ok=True)

    # create a scoped_session for opencell database
    if args.credentials:
        db_url = db_utils.url_from_credentials(args.credentials)
        engine = sa.create_engine(db_url)
        models.Base.metadata.create_all(engine)

        session_factory = sa.orm.sessionmaker(bind=engine)
        Session = sa.orm.scoped_session(session_factory)

    # if a pml_id was provided, only process the FOVs from that dataset
    fovs = None
    if args.pml_id:
        dataset = (
            Session.query(models.MicroscopyDataset)
            .filter(models.MicroscopyDataset.pml_id == args.pml_id)
            .first()
        )
        fovs = dataset.fovs

    # construct the PlateMicroscopy metadata
    # (this is a dataframe of FOV metadata with one row per FOV)
    if args.construct_plate_microscopy_metadata:
        manager = PlateMicroscopyManager(args.plate_microscopy_dir, args.cache_dir)
        construct_plate_microscopy_metadata(manager)

    # inspect the cached PlateMicroscopy metadata
    if args.inspect_plate_microscopy_metadata:
        manager = PlateMicroscopyManager(args.plate_microscopy_dir, args.cache_dir)
        inspect_plate_microscopy_metadata(manager)

    # insert all FOVs from the 'PlateMicroscopy' directory
    if args.insert_plate_microscopy_fovs:
        with operations.session_scope(db_url) as session:
            insert_plate_microscopy_fovs(session, cache_dir=args.cache_dir, errors='warn')

    # insert the FOVs from a dataset in the 'raw-pipeline-microscopy' directory
    if args.insert_fovs:
        with operations.session_scope(db_url) as session:
            insert_raw_pipeline_microscopy_fovs(
                session, args.raw_pipeline_microscopy_dir, pml_id=args.pml_id, errors='warn')

    # process all raw tiffs
    if args.process_raw_tiffs:
        method_name = 'process_raw_tiff'
        method_kwargs = {'dst_root': args.dst_root}

        if not args.process_all_fovs:
            fovs = get_unprocessed_fovs(engine, Session, result_kind='raw-tiff-metadata')
        try:
            do_fov_tasks(Session, args, method_name, method_kwargs, fovs=fovs)
        except Exception as error:
            print('FATAL ERROR: an uncaught exception occurred in %s' % method_name)
            print(str(error))
            with open(
                os.path.join(args.dst_root, '%s_%s_uncaught_exception.log' % (timestamp(), method_name)),
                'w'
            ) as file:
                file.write(str(error))


    # calculate z-profiles
    if args.calculate_z_profiles:
        method_name = 'calculate_z_profiles'
        method_kwargs = {}
        if not args.process_all_fovs:
            fovs = get_unprocessed_fovs(engine, Session, result_kind='z-profiles')
        do_fov_tasks(Session, args, method_name, method_kwargs, fovs=fovs)


    # crop around the cell layer in z
    if args.generate_clean_tiffs:
        method_name = 'generate_clean_tiff'
        method_kwargs = {'dst_root': args.dst_root}
        if not args.process_all_fovs:
            fovs = get_unprocessed_fovs(engine, Session, result_kind='clean-tiff-metadata')
        do_fov_tasks(Session, args, method_name, method_kwargs, fovs=fovs)


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
            'fov_scorer': fov_scorer}

        if not args.process_all_fovs:
            fovs = get_unprocessed_fovs(engine, Session, result_kind='fov-features')
        do_fov_tasks(Session, args, method_name, method_kwargs, fovs=fovs)


    # generate thumbnails with a given size and quality
    if args.generate_fov_thumbnails:

        method_name = 'generate_fov_thumbnails'
        method_kwargs = {
            'dst_root': args.dst_root,
            'scale': int(args.thumbnail_scale),
            'quality': int(args.thumbnail_quality),
        }
        do_fov_tasks(Session, args, method_name, method_kwargs, fovs=fovs)


    if args.crop_corner_rois:
        method_name = 'crop_corner_rois'
        method_kwargs = {'dst_root': args.dst_root}

        # only crop ROIs from the two highest-scoring FOVs per line
        fovs_to_crop = []
        for line in Session.query(models.CellLine).all():
            ops = operations.PolyclonalLineOperations(line)
            fovs_to_crop.extend(ops.get_top_scoring_fovs(Session, ntop=2))

        try:
            do_fov_tasks(Session, args, method_name, method_kwargs, fovs=fovs_to_crop)
        except Exception as error:
            print('FATAL ERROR: an uncaught exception occurred in %s' % method_name)
            print(str(error))
            with open(
                os.path.join(args.dst_root, '%s_%s_uncaught_exception.log' % (timestamp(), method_name)),
                'w'
            ) as file:
                file.write(str(error))
            raise


if __name__ == '__main__':
    main()
