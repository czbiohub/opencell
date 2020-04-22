
import os
import sys
import json
import argparse
import pandas as pd
import sqlalchemy as db

import sqlalchemy.orm
import sqlalchemy.ext.declarative

from opencell import constants, file_utils
from opencell.database import models, utils
from opencell.database import operations as ops


def parse_args():
    '''
    '''
    parser = argparse.ArgumentParser()

    # path to credentials JSON
    parser.add_argument(
        '--credentials',
        dest='credentials',
        required=True)

    # the path to the directory of snapshot/cached opencell metadata
    parser.add_argument(
        '--data-dir',
        dest='data_dir')

    # the path to the directory of cached FACS results
    parser.add_argument(
        '--facs-results-dir',
        dest='facs_results_dir')

    # the filepath to a snapshot of the 'pipeline-microscopy-master-key' google sheet
    parser.add_argument(
        '--microscopy-master-key',
        dest='microscopy_master_key')

    # CLI args whose presence in the command sets them to True
    action_arg_dests = [
        'update',
        'drop_all',
        'populate',
        'insert_facs',
        'insert_plate_microscopy_datasets',
        'insert_raw_pipeline_microscopy_datasets',
    ]

    for dest in action_arg_dests:
        flag = '--%s' % dest.replace('_', '-')
        parser.add_argument(flag, dest=dest, action='store_true', required=False)
        parser.set_defaults(**{dest: False})

    args = parser.parse_args()
    return args


def maybe_drop_and_create(engine, drop=False):

    if drop:
        print('Dropping all tables')
        models.Base.metadata.drop_all(engine)

    print('Creating all tables')
    models.Base.metadata.create_all(engine)


def populate(session, data_dir, errors='warn'):
    '''
    Initialize and populate the opencell database
    from a set of 'snapshot' CSVs of various google spreadsheets

    This loads the crispr designs, plates, electroporations, polyclonal lines,
    for Plates 1-19

    errors : one of 'raise', 'warn', 'ignore'
    '''

    # create the progenitor cell line used for Plates 1-19
    # (note the hard-coded progenitor cell line name)
    print('Inserting progenitor cell line for plates 1-19')
    ops.get_or_create_progenitor_cell_line(
        session,
        name=constants.PARENTAL_LINE_NAME,
        notes='mNG1-10 in HEK293',
        create=True
    )

    # create the crispr designs
    print('Inserting crispr designs for plates 1-19')
    library_snapshot = file_utils.load_library_snapshot(
        os.path.join(data_dir, '2019-06-26_mNG11_HEK_library.csv'))

    plate_ids = sorted(set(library_snapshot.plate_id))
    for plate_id in plate_ids:
        print('Inserting crispr designs for %s' % plate_id)
        plate_ops = ops.PlateOperations.get_or_create_plate_design(session, plate_id)
        plate_ops.create_crispr_designs(
            session, library_snapshot, drop_existing=False, errors=errors)

    # create the electroporations and polyclonal lines
    print('Inserting electroporations and polyclonal lines for plates 1-19')
    electroporation_history = file_utils.load_electroporation_history(
        os.path.join(data_dir, '2019-06-24_electroporations.csv'))

    progenitor_line = ops.get_or_create_progenitor_cell_line(
        session, constants.PARENTAL_LINE_NAME)

    for _, row in electroporation_history.iterrows():
        print('Inserting electroporation of %s' % row.plate_id)

        # we assume here that there is only one plate instance
        # of the electroporation plate design
        plate_design = ops.PlateOperations.from_id(session, row.plate_id).plate_design
        ops.create_electroporation(
            session,
            progenitor_line,
            plate_design,
            date=row.date,
            errors=errors
        )


def insert_facs(session, facs_results_dir, errors='warn'):
    '''
    Insert FACS results and histograms for each polyclonal cell line
    '''

    results_filepath = os.path.join(facs_results_dir, '2019-07-16_all-facs-results.csv')
    histograms_filepath = os.path.join(facs_results_dir, '2019-07-16_all-dists.json')

    # load the cached FACS results
    facs_properties = pd.read_csv(results_filepath)
    with open(histograms_filepath, 'r') as file:
        facs_histograms = json.load(file)

    # key the histograms by tuples of (plate_id, well_id)
    d = {}
    for row in facs_histograms:
        d[(row['plate_id'], row['well_id'])] = row
    facs_histograms = d

    for _, row in facs_properties.iterrows():
        plate_id = row.plate_id
        well_id = utils.format_well_id(row.well_id)

        # the polyclonal line
        try:
            pcl_ops = ops.PolyclonalLineOperations.from_plate_well(session, plate_id, well_id)
        except ValueError:
            print('No polyclonal line for (%s, %s)' % (plate_id, well_id))
            continue

        # the histograms (dict of 'x', 'y_sample', 'y_fitted_ref')
        # note: keyed by unformatted well_id
        histograms = facs_histograms.get((row.plate_id, row.well_id))

        scalars = dict(row.drop(['plate_id', 'well_id']))
        pcl_ops.insert_facs_dataset(session, histograms=histograms, scalars=scalars, errors=errors)


def insert_microscopy_datasets(session, metadata, root_directory, update=False, errors='warn'):
    '''
    '''
    for _, row in metadata.iterrows():
        dataset = (
            session.query(models.MicroscopyDataset)
            .filter(models.MicroscopyDataset.pml_id == row.pml_id)
            .all()
        )
        if dataset:
            if update:
                dataset = dataset.pop()
                print('Warning: updating existing entry for %s' % row.pml_id)
            else:
                print('Warning: dataset %s already exists' % row.pml_id)
                continue
        else:
            dataset = models.MicroscopyDataset(pml_id=row.pml_id)
            print('Inserting new dataset %s' % row.pml_id)

        dataset.date = row.date
        dataset.root_directory = root_directory
        dataset.raw_metadata = json.loads(row.to_json())
        ops.add_and_commit(session, dataset, errors=errors)


def main():
    '''

    Returns
    -------

    '''
    args = parse_args()

    url = utils.url_from_credentials(args.credentials)
    engine = db.create_engine(url)
    Session = db.orm.sessionmaker(bind=engine)
    session = Session()

    if args.drop_all:
        maybe_drop_and_create(engine, drop=True)
    else:
        maybe_drop_and_create(engine, drop=False)

    if args.populate:
        populate(session, args.data_dir, errors='warn')

    if args.insert_facs:
        insert_facs(session, args.facs_results_dir, errors='warn')


    # insert the 'legacy' pipeline microscopy datasets found in the 'PlateMicroscopy' directory
    # (these are datasets up to PML0179)
    if args.insert_plate_microscopy_datasets:
        filepath = os.path.join(
            args.data_dir,
            '2019-12-05_Pipeline-microscopy-master-key_PlateMicroscopy-MLs-raw.csv')
        metadata = file_utils.load_legacy_microscopy_master_key(filepath)
        insert_microscopy_datasets(
            session,
            metadata,
            root_directory='plate_microscopy',
            update=False,
            errors='warn')


    # insert pipeline microscopy datasets found in the 'raw-pipeline-microscopy' directory
    # (these datasets start at PML0196 and were acquired using the dragonfly-automation scripts)
    if args.insert_raw_pipeline_microscopy_datasets:
        metadata = pd.read_csv(args.microscopy_master_key)
        metadata.rename(columns={'id': 'pml_id'}, inplace=True)
        metadata.dropna(how='any', subset=['pml_id'], axis=0, inplace=True)
        insert_microscopy_datasets(
            session,
            metadata,
            root_directory='raw_pipeline_microscopy',
            update=args.update,
            errors='warn')


if __name__ == '__main__':
    main()
