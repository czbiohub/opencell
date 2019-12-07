
import os
import sys
import json
import pandas as pd
import sqlalchemy as db
import sqlalchemy.orm
import sqlalchemy.ext.declarative

from opencell import constants, file_utils
from opencell.database import models, utils
from opencell.database import operations as ops
from opencell.imaging.managers import PlateMicroscopyManager


def populate(url, drop_all=False, errors='warn'):
    '''

    Initialize and populate the opencell database
    from a set of 'snapshot' CSVs of various google spreadsheets

    This loads the crispr designs, plates, electroporations, polyclonal lines,
    for Plates 1-19

    TODO: insert FACS results and microscopy datasets

    errors : one of 'raise', 'warn', 'ignore'
    '''
    engine = db.create_engine(url)

    # -----------------------------------------------------------------------------------
    #
    # Set up tables and session
    #
    # -----------------------------------------------------------------------------------
    if drop_all:
        print('Dropping all tables')
        models.Base.metadata.drop_all(engine)

        print('Creating all tables')
        models.Base.metadata.create_all(engine)

    Session = db.orm.sessionmaker(bind=engine)
    session = Session()


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
        '../data/2019-06-26_mNG11_HEK_library.csv')

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
        '../data/2019-06-24_electroporations.csv')

    progenitor_line = ops.get_or_create_progenitor_cell_line(session, constants.PARENTAL_LINE_NAME)
    for ind, row in electroporation_history.iterrows():
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


def insert_facs(session, errors='warn'):
    '''
    Insert FACS results and histograms for each polyclonal cell line
    '''

    results_filepath = '../results/2019-07-16_all-facs-results.csv'
    histograms_filepath = '../../opencell-off-git/results/2019-07-16_all-dists.json'

    # load the cached FACS results
    facs_properties = pd.read_csv(results_filepath)
    with open(histograms_filepath, 'r') as file:
        facs_histograms = json.load(file)

    # key the histograms by tuples of (plate_id, well_id)
    d = {}
    for row in facs_histograms:
        d[(row['plate_id'], row['well_id'])] = row
    facs_histograms = d

    for ind, row in facs_properties.iterrows():
        plate_id = row.plate_id
        well_id = utils.format_well_id(row.well_id)

        # the polyclonal line
        try:
            pcl_ops = ops.PolyclonalLineOperations.from_plate_well(session, plate_id, well_id)
        except ValueError as error:
            print('No polyclonal line for (%s, %s)' % (plate_id, well_id))
            continue

        # the histograms (dict of 'x', 'y_sample', 'y_fitted_ref')
        # note: keyed by unformatted well_id
        histograms = facs_histograms.get((plate_id, well_id))

        row = row.drop(['plate_id', 'well_id'])
        pcl_ops.insert_facs_results(session, histograms, row, errors=errors)


def insert_microscopy_datasets(session, errors='warn'):
    '''
    Insert pipeline microscopy datasets 
    
    Currently, only inserts datasets up to PML0179
    (these datasets correspond to all datasets in the PlateMicroscopy directory)
    '''

    filepath = '../data/2019-12-05_Pipeline-microscopy-master-key_PlateMicroscopy-MLs-raw.csv'
    exp_md = file_utils.load_microscopy_master_key(filepath)

    for ind, row in exp_md.iterrows():
        dataset = models.MicroscopyDataset(
            pml_id=row.pml_id, 
            date=row.date, 
            user=row.imager, 
            description=row.description,
            root_directory='plate_microscopy')

        ops.add_and_commit(session, dataset, errors='warn')


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
    md_raw = pm.md_raw.groupby(['plate_id', 'well_id'])

    plate_id = None
    for group in md_raw.groups:
        if plate_id is None or group[0] != plate_id:
            print('Inserting %s' % group[0])
        plate_id, well_id = group

        try:
            pcl_ops = ops.PolyclonalLineOperations.from_plate_well(session, plate_id, well_id)
        except:
            print('No polyclonal line for (%s, %s)' % group)
            continue

        md_raw_crop = md_raw.get_group(group)
        pcl_ops.insert_microscopy_fovs(session, md_raw_crop, errors='ignore')
