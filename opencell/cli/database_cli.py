
import os
import sys
import dask
import json
import argparse
import pandas as pd
import sqlalchemy as db

import dask.diagnostics
import sqlalchemy.orm
import sqlalchemy.ext.declarative

from opencell import constants, file_utils
from opencell.api import settings
from opencell.database import metadata_operations, uniprot_operations, fov_operations
from opencell.database import models, utils, uniprot_utils

import logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s in %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def parse_args():
    '''
    '''
    parser = argparse.ArgumentParser()

    # deployment mode - one of 'dev', 'test', 'staging', 'prod'
    parser.add_argument('--mode', dest='mode', required=True)

    # path to JSON file with database credentials
    # (if provided, overrides the filepath defined in opencell.api.settings)
    parser.add_argument('--credentials', dest='credentials', required=False)

    # the filepath to a snapshot of a google sheet, for methods that need one
    # (e.g. the 'da list' sheet, the pipeline-microscopy-master-key, or the resorted lines sheet)
    parser.add_argument('--snapshot-filepath', dest='snapshot_filepath')

    # plate_id is used by insert_plate_design and insert_electroporation
    parser.add_argument('--plate-id', dest='plate_id')

    # date is used by insert_electroporation
    parser.add_argument('--date', dest='date')

    # the path to the directory of cached FACS results
    parser.add_argument('--facs-results-dir', dest='facs_results_dir')

    # optional sql command to execute
    # (if provided, other options/commands are ignored)
    parser.add_argument('--execute-sql', dest='sql_command', required=False)

    # CLI args whose presence in the command sets them to True
    action_arg_dests = [
        'update',
        'drop_all',
        'create_all',
        'populate',
        'insert_plate_design',
        'insert_electroporation',
        'insert_resorted_lines',
        'insert_facs',
        'insert_plate_microscopy_datasets',
        'insert_raw_pipeline_microscopy_datasets',
        'insert_uniprot_metadata_for_crispr_designs',
        'insert_uniprot_metadata_for_protein_groups',
        'insert_ensg_ids',
        'generate_protein_group_associations',
    ]

    for dest in action_arg_dests:
        flag = '--%s' % dest.replace('_', '-')
        parser.add_argument(flag, dest=dest, action='store_true', required=False)
        parser.set_defaults(**{dest: False})

    args = parser.parse_args()
    return args


def populate(session, data_dir):
    '''
    Initialize and populate the opencell database,
    using a set of 'snapshot' CSVs of various google spreadsheets

    This inserts the plate designs, crispr designs, and polyclonal lines
    for Plates 1-19.

    Note that this method has no ongoing use in production;
    it was used during development and to initialize the original opencell database,
    but is now used only to set up test databases.

    To insert crispr designs for new plates into an existing prod database,
    the `insert_plate_design` method should be used.
    '''
    # hard-coded paths to snapshots of google sheets
    library_snapshot_filepath = os.path.join(data_dir, '2019-06-26_mNG11_HEK_library.csv')
    electroporation_history_filepath = os.path.join(data_dir, '2019-06-24_electroporations.csv')

    # create the progenitor cell line used for Plates 1-19
    # (note the hard-coded progenitor cell line name)
    metadata_operations.get_or_create_progenitor_cell_line(
        session,
        name=constants.PARENTAL_LINE_NAME,
        notes='mNG1-10 in HEK293',
        create=True
    )

    # insert the plate designs and crispr designs
    library_snapshot = file_utils.load_library_snapshot(library_snapshot_filepath)
    plate_ids = sorted(set(library_snapshot.plate_id))
    for plate_id in plate_ids:
        insert_plate_design(session, plate_id, library_snapshot_filepath)

    # insert the electroporations and polyclonal lines
    electroporation_history = file_utils.load_electroporation_history(
        electroporation_history_filepath
    )
    for _, row in electroporation_history.iterrows():
        insert_electroporation(session, row.plate_id, row.date)


def insert_plate_design(session, plate_id, library_snapshot_filepath):
    '''
    Insert a new plate design and its crispr designs
    This method is intended to update an existing opencell database when a new plate is created
    '''
    # the 'library snapshot' is the 'da list' google sheet of all crispr designs
    library_snapshot = file_utils.load_library_snapshot(library_snapshot_filepath)

    logger.info('Inserting crispr designs for plate %s' % plate_id)
    plate_design = metadata_operations.get_or_create_plate_design(session, plate_id, create=True)
    metadata_operations.create_crispr_designs(
        session, plate_design, library_snapshot, drop_existing=False
    )


def insert_electroporation(session, plate_id, electroporation_date):
    '''
    Create the polyclonal lines generated by electroporating and sorting a single plate
    '''
    logger.info('Creating polyclonal lines for plate %s' % plate_id)
    progenitor_line = metadata_operations.get_or_create_progenitor_cell_line(
        session, constants.PARENTAL_LINE_NAME
    )
    plate_design = metadata_operations.get_or_create_plate_design(session, plate_id)
    metadata_operations.create_polyclonal_lines(
        session,
        progenitor_line,
        plate_design,
        date=electroporation_date,
    )


def insert_resorted_lines(session, resorts_snapshot):
    '''
    Insert once-resorted polyclonal cell lines from a google sheet snapshot
    (that is, lines with sort_count = 2)

    resorts_snapshot : snapshot of the google sheet of resorted lines,
        with columns 'plate_id', 'pipeline_well_id', and 'resorting_date'
    '''
    resorts_snapshot.dropna(how='any', axis=0, inplace=True)

    # zero-pad the well_ids
    resorts_snapshot['pipeline_well_id'] = resorts_snapshot.pipeline_well_id.apply(
        utils.format_well_id
    )
    for ind, row in resorts_snapshot.iterrows():
        logger.info('Inserting resorted cell line for (%s, %s)' % (row.plate_id, row.pipeline_well_id))
        line_operations = metadata_operations.PolyclonalLineOperations.from_plate_well(
            session, row.plate_id, row.pipeline_well_id, sort_count=1
        )
        line_operations.insert_resorted_line(
            session, sort_count=2, sort_date=row.resorting_date
        )


def insert_facs(session, facs_results_dir):
    '''
    Insert FACS results and histograms for the original polyclonal cell lines from Plates 1-19
    '''
    # hard-coded filenames of the cached FACS results
    results_filepath = os.path.join(facs_results_dir, '2019-07-16_all-facs-results.csv')
    histograms_filepath = os.path.join(facs_results_dir, '2019-07-16_all-dists.json')

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
        try:
            line_ops = metadata_operations.PolyclonalLineOperations.from_plate_well(
                session, plate_id, well_id, sort_count=1
            )
        except ValueError:
            logger.error('No polyclonal line for (%s, %s)' % (plate_id, well_id))
            continue

        # the histograms are dicts of 'x', 'y_sample', 'y_fitted_ref'
        # (note row.well_id is an unformatted well_id)
        histograms = facs_histograms.get((row.plate_id, row.well_id))
        scalars = dict(row.drop(['plate_id', 'well_id']))
        line_ops.insert_facs_dataset(session, histograms=histograms, scalars=scalars)


def insert_uniprot_metadata_for_crispr_designs(Session):
    '''
    Retrieve and insert uniprot metadata for all crispr designs
    '''
    @dask.delayed
    def create_task(Session, design_id):
        uniprot_operations.insert_uniprot_metadata_for_crispr_design(Session(), design_id)

    designs = Session.query(models.CrisprDesign).all()
    tasks = [create_task(Session, design.id) for design in designs]

    with dask.diagnostics.ProgressBar():
        dask.compute(*tasks)


def insert_uniprot_metadata_for_protein_groups(Session):
    '''
    Insert uniprot metadata for all uniprot_ids that appear in at least one
    mass spec protein group and for which metadata does not already exist
    '''
    engine = Session.get_bind()

    # all uniprot_ids from all mass spec protein groups
    all_uniprot_ids = (
        pd.read_sql(
            'select unnest(uniprot_ids) as uniprot_id from mass_spec_protein_group',
            engine
        )
        .uniprot_id
        .tolist()
    )

    # unique ids, ignoring isoforms (which are indicated by trailing dashed numbers)
    all_uniprot_ids = set([uniprot_id.split('-')[0] for uniprot_id in all_uniprot_ids])

    new_uniprot_ids = all_uniprot_ids.difference([
        row.uniprot_id for row in Session.query(models.UniprotMetadata).all()
    ])

    @dask.delayed
    def create_task(Session, uniprot_id):
        uniprot_operations.insert_uniprot_metadata_from_id(Session(), uniprot_id)

    tasks = [create_task(Session, uniprot_id) for uniprot_id in new_uniprot_ids]
    with dask.diagnostics.ProgressBar():
        dask.compute(*tasks)


def insert_ensg_ids(Session):
    '''
    Populate the ENSG ID column of the uniprot_metadata table
    '''
    uniprot_ids = [
        row.uniprot_id
        for row in (
            Session.query(models.UniprotMetadata)
            .filter(models.UniprotMetadata.ensg_id.is_(None))
            .all()
        )
    ]
    logger.info('Inserting ENSG IDs for %s new uniprot_ids' % len(uniprot_ids))

    parallelize = False
    if not parallelize:
        for uniprot_id in uniprot_ids:
            uniprot_operations.insert_ensg_id(Session, uniprot_id)
        return

    @dask.delayed
    def create_task(Session, uniprot_id):
        uniprot_operations.insert_ensg_id(Session(), uniprot_id)

    tasks = [create_task(Session, uniprot_id) for uniprot_id in uniprot_ids]
    with dask.diagnostics.ProgressBar():
        dask.compute(*tasks)


def main():
    # TODO: add optional file handler to the logger

    args = parse_args()
    config = settings.get_config(args.mode)

    url = utils.url_from_credentials(args.credentials or config.DB_CREDENTIALS_FILEPATH)
    engine = db.create_engine(url)
    session_factory = db.orm.sessionmaker(bind=engine)
    Session = db.orm.scoped_session(session_factory)

    if args.create_all:
        models.Base.metadata.create_all(engine)

    if args.sql_command:
        logger.info("Executing '%s'" % args.sql_command)
        with engine.connect().execution_options(autocommit=True) as conn:
            conn.execute(db.text(args.sql_command))

    if args.populate:
        if args.drop_all:
            models.Base.metadata.drop_all(engine)
        models.Base.metadata.create_all(engine)
        data_dir = os.path.join(config.PROJECT_ROOT, 'data')
        populate(Session, data_dir)

    if args.insert_plate_design:
        insert_plate_design(Session, args.plate_id, args.snapshot_filepath)

    if args.insert_electroporation:
        insert_electroporation(
            Session, plate_id=args.plate_id, electroporation_date=args.date
        )

    if args.insert_resorted_lines:
        platemap = pd.read_csv(args.snapshot_filepath)
        insert_resorted_lines(Session, platemap)

    if args.insert_facs:
        insert_facs(Session, args.facs_results_dir)

    # insert the 'legacy' pipeline microscopy datasets in the 'PlateMicroscopy' directory
    # (these are datasets up to PML0179)
    if args.insert_plate_microscopy_datasets:
        filepath = os.path.join(
            config.PROJECT_ROOT,
            'data',
            '2019-12-05_Pipeline-microscopy-master-key_PlateMicroscopy-MLs-raw.csv'
        )
        plate_microscopy_metadata = file_utils.load_legacy_microscopy_master_key(filepath)
        for _, metadata_row in plate_microscopy_metadata.iterrows():
            fov_operations.insert_microscopy_dataset(
                Session, metadata_row, root_directory='plate_microscopy', update=False
            )

    # insert pipeline microscopy datasets in the 'raw-pipeline-microscopy' directory
    # (these datasets start at PML0196 and were acquired using the dragonfly-automation scripts)
    if args.insert_raw_pipeline_microscopy_datasets:
        pml_metadata = pd.read_csv(args.snapshot_filepath)
        pml_metadata.rename(columns={'id': 'pml_id'}, inplace=True)
        pml_metadata.dropna(how='any', subset=['pml_id', 'date'], axis=0, inplace=True)
        for _, metadata_row in pml_metadata.iterrows():
            fov_operations.insert_microscopy_dataset(
                Session, metadata_row, root_directory='raw_pipeline_microscopy', update=args.update
            )

    if args.insert_uniprot_metadata_for_crispr_designs:
        insert_uniprot_metadata_for_crispr_designs(Session)

    if args.insert_uniprot_metadata_for_protein_groups:
        insert_uniprot_metadata_for_protein_groups(Session)

    if args.insert_ensg_ids:
        insert_ensg_ids(Session)

    if args.generate_protein_group_associations:
        uniprot_operations.generate_protein_group_uniprot_metadata_associations(Session)
        uniprot_operations.generate_protein_group_crispr_design_associations(Session)


if __name__ == '__main__':
    main()
