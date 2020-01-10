
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

    # the location of the cached opencell metadata
    parser.add_argument(
        '--data-dir',
        dest='data_dir')

    # the location of the FACS results
    parser.add_argument(
        '--facs-results-dir',
        dest='facs_results_dir')

    # path to credentials JSON
    parser.add_argument(
        '--credentials', 
        dest='credentials', 
        required=True)

    # CLI args whose presence in the command sets them to True
    action_arg_names = [
        'drop_all', 
        'populate',
        'insert_facs',
        'insert_microscopy'
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

    # -----------------------------------------------------------------------------------
    #
    # create progenitor cell line
    # (this is the parental line for Plates 1-19)
    # Note the hard-coded progenitor cell line name
    #
    # -----------------------------------------------------------------------------------
    print('Inserting progenitor cell line for plates 1-19')
    ops.get_or_create_progenitor_cell_line(
        session, 
        name=constants.PARENTAL_LINE_NAME, 
        notes='mNG1-10 in HEK293', 
        create=True)

    # -----------------------------------------------------------------------------------
    #
    # Insert crispr designs from Library snapshot
    #
    # -----------------------------------------------------------------------------------
    print('Inserting crispr designs for plates 1-19')

    library_snapshot = file_utils.load_library_snapshot(
        os.path.join(data_dir, '2019-06-26_mNG11_HEK_library.csv'))

    plate_ids = sorted(set(library_snapshot.plate_id))
    for plate_id in plate_ids:
        print('Inserting crispr designs for %s' % plate_id)
        plate_ops = ops.PlateOperations.get_or_create_plate_design(session, plate_id)
        plate_ops.create_crispr_designs(session, library_snapshot, drop_existing=False, errors=errors)

    # -----------------------------------------------------------------------------------
    #
    # Insert electroporations and create polyclonal lines
    # Note the hard-coded progenitor line name
    #
    # -----------------------------------------------------------------------------------
    print('Inserting electroporations and polyclonal lines for plates 1-19')

    electroporation_history = file_utils.load_electroporation_history(
        os.path.join(data_dir, '2019-06-24_electroporations.csv'))

    progenitor_line = ops.get_or_create_progenitor_cell_line(session, constants.PARENTAL_LINE_NAME)
    for _, row in electroporation_history.iterrows():
        print('Inserting electroporation of %s' % row.plate_id)

        # get the first (and, we assume, only) plate instance
        # of this electroporations's plate design
        plate_ops = ops.PlateOperations.from_id(session, row.plate_id)
        plate_instance = plate_ops.plate.plate_instances[0]

        ops.ElectroporationOperations.create_electroporation(
            session,
            progenitor_line,
            plate_instance,
            date=row.date,
            errors=errors)


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


def insert_plate_microscopy_datasets(session, data_dir, errors='warn'):
    '''
    Insert microscopy datasets found in the 'PlateMicroscopy' directory    
    (these are datasets up to PML0179)
    '''

    # datasets are all from the PlateMicroscopy directory, 
    # so the root_directory is always the same
    root_directory = 'plate_microscopy'

    filepath = os.path.join(data_dir, '2019-12-05_Pipeline-microscopy-master-key_PlateMicroscopy-MLs-raw.csv')
    exp_md = file_utils.load_microscopy_master_key(filepath)

    for _, row in exp_md.iterrows():
        dataset = models.MicroscopyDataset(
            pml_id=row.pml_id, 
            date=row.date, 
            user=row.imager, 
            description=row.description,
            root_directory=root_directory)

        ops.add_and_commit(session, dataset, errors='warn')


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

    if args.insert_microscopy:
        insert_plate_microscopy_datasets(session, args.data_dir, errors='warn')

if __name__ == '__main__':
    main()