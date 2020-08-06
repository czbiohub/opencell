
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
from opencell.database import operations as ops
from opencell.database import models, utils, uniprot_utils


def parse_args():
    '''
    '''
    parser = argparse.ArgumentParser()

    # deployment mode - one of 'dev', 'test', 'staging', 'prod'
    parser.add_argument('--mode', dest='mode', required=True)

    # path to JSON file with database credentials
    # (if provided, overrides the filepath defined in opencell.api.settings)
    parser.add_argument('--credentials', dest='credentials', required=False)

    # the path to the directory of snapshot/cached opencell metadata
    # (used by populate and insert_plate_microscopy_datasets methods)
    parser.add_argument('--data-dir', dest='data_dir')

    # the filepath to a snapshot of the 'da list' google sheet (used by insert_plate_design)
    parser.add_argument('--library-snapshot-filepath', dest='library_snapshot_filepath')

    # plate_id is used by insert_plate_design and insert_electroporation
    parser.add_argument('--plate-id', dest='plate_id')

    # date is used by insert_electroporation
    parser.add_argument('--date', dest='date')

    # the path to the directory of cached FACS results
    parser.add_argument('--facs-results-dir', dest='facs_results_dir')

    # the filepath to a snapshot of the 'pipeline-microscopy-master-key' google sheet
    parser.add_argument('--microscopy-master-key', dest='microscopy_master_key')


    # optional sql command to execute
    # (if provided, other options/commands are ignored)
    parser.add_argument('--execute-sql', dest='sql_command', required=False)

    # CLI args whose presence in the command sets them to True
    action_arg_dests = [
        'update',
        'drop_all',
        'populate',
        'insert_plate_design',
        'insert_electroporation',
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


def maybe_drop_and_create(engine, drop=False):

    if drop:
        print('Dropping all tables')
        models.Base.metadata.drop_all(engine)

    print('Creating all tables')
    models.Base.metadata.create_all(engine)


def populate(session, data_dir, errors='warn'):
    '''
    Initialize and populate the opencell database,
    using a set of 'snapshot' CSVs of various google spreadsheets

    This inserts the plate designs, crispr designs, electroporations, and polyclonal lines
    for Plates 1-19.

    Note that this method has no ongoing use in production;
    it was used during development and to initialize the original opencell database,
    but is now used only to set up test databases.

    To insert crispr designs for new plates into an existing prod database,
    the `insert_plate_design` method should be used.

    errors : one of 'raise', 'warn', 'ignore'
    '''

    # hard-coded paths to snapshots of google sheets
    library_snapshot_filepath = os.path.join(data_dir, '2019-06-26_mNG11_HEK_library.csv')
    electroporation_history_filepath = os.path.join(data_dir, '2019-06-24_electroporations.csv')

    # create the progenitor cell line used for Plates 1-19
    # (note the hard-coded progenitor cell line name)
    print('Inserting progenitor cell line for plates 1-19')
    ops.get_or_create_progenitor_cell_line(
        session,
        name=constants.PARENTAL_LINE_NAME,
        notes='mNG1-10 in HEK293',
        create=True
    )

    # create the plate and crispr designs
    print('Inserting crispr designs for plates 1-19')
    library_snapshot = file_utils.load_library_snapshot(library_snapshot_filepath)

    plate_ids = sorted(set(library_snapshot.plate_id))
    for plate_id in plate_ids:
        print('Inserting crispr designs for %s' % plate_id)

        # create the plate design
        plate_design = ops.get_or_create_plate_design(session, plate_id, create=True)

        # create the crispr designs
        ops.create_crispr_designs(
            session, plate_design, library_snapshot, drop_existing=False, errors=errors
        )

    # create the electroporations and polyclonal lines
    print('Inserting electroporations and polyclonal lines for plates 1-19')
    electroporation_history = file_utils.load_electroporation_history(
        electroporation_history_filepath
    )

    progenitor_line = ops.get_or_create_progenitor_cell_line(
        session, constants.PARENTAL_LINE_NAME
    )

    for _, row in electroporation_history.iterrows():
        print('Inserting electroporation and cell lines for %s' % row.plate_id)
        plate_design = ops.get_or_create_plate_design(session, row.plate_id)
        ops.create_polyclonal_lines(
            session,
            progenitor_line,
            plate_design,
            date=row.date,
            errors=errors
        )


def insert_plate_design(session, plate_id, library_snapshot_filepath, errors='warn'):
    '''
    Insert a new plate design and its crispr designs
    This method is intended to update an existing opencell database when a new plate is created
    '''

    # the 'library snapshot' is the 'da list' google sheet of all crispr designs
    library_snapshot = file_utils.load_library_snapshot(library_snapshot_filepath)

    print('Inserting crispr designs for plate %s' % plate_id)
    plate_design = ops.get_or_create_plate_design(session, plate_id, create=True)
    ops.create_crispr_designs(
        session, plate_design, library_snapshot, drop_existing=False, errors=errors
    )


def insert_electroporation(session, plate_id, electroporation_date, errors='warn'):
    '''
    Create an electroporation
    '''
    print('Creating electroporation and polyclonal lines for plate %s' % plate_id)

    progenitor_line = ops.get_or_create_progenitor_cell_line(
        session, constants.PARENTAL_LINE_NAME
    )
    plate_design = ops.get_or_create_plate_design(session, plate_id)
    ops.create_polyclonal_lines(
        session,
        progenitor_line,
        plate_design,
        date=electroporation_date,
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
            line_ops = ops.PolyclonalLineOperations.from_plate_well(session, plate_id, well_id)
        except ValueError:
            print('No polyclonal line for (%s, %s)' % (plate_id, well_id))
            continue

        # the histograms (each a dict of 'x', 'y_sample', 'y_fitted_ref')
        # note row.well_id is an unformatted well_id
        histograms = facs_histograms.get((row.plate_id, row.well_id))
        scalars = dict(row.drop(['plate_id', 'well_id']))

        line_ops.insert_facs_dataset(
            session, histograms=histograms, scalars=scalars, errors=errors
        )


def insert_microscopy_datasets(
    session, metadata, root_directory, update=False, errors='warn'
):
    '''
    '''
    for _, row in metadata.iterrows():
        dataset = (
            session.query(models.MicroscopyDataset)
            .filter(models.MicroscopyDataset.pml_id == row.pml_id)
            .one_or_none()
        )
        if dataset:
            if update:
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
        utils.add_and_commit(session, dataset, errors=errors)


def insert_uniprot_metadata_for_crispr_designs(Session):
    '''
    Retrieve and insert uniprot metadata for all crispr designs
    '''
    @dask.delayed
    def create_task(Session, design_id):
        ops.insert_uniprot_metadata_for_crispr_design(Session(), design_id)

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
        ops.insert_uniprot_metadata_from_id(Session(), uniprot_id)

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
    print('Inserting ENSG IDs for %s new uniprot_ids' % len(uniprot_ids))

    parallelize = False
    if not parallelize:
        for uniprot_id in uniprot_ids:
            ops.insert_ensg_id(Session, uniprot_id)
        return

    @dask.delayed
    def create_task(Session, uniprot_id):
        ops.insert_ensg_id(Session(), uniprot_id)

    tasks = [create_task(Session, uniprot_id) for uniprot_id in uniprot_ids]
    with dask.diagnostics.ProgressBar():
        dask.compute(*tasks)


def generate_protein_group_uniprot_metadata_associations(Session):
    '''
    Populate the association table between the mass_spec_protein_group table
    and the uniprot_metadata table, using uniprot_ids.

    The 'raw' uniprot_ids are found in the uniprot_ids column of the protein_group table;
    here, these are parsed to eliminate isoform-specific ids and also ids
    for which no cached uniprot metadata exists (these are rare).

    Note that, when new mass spec protein groups are inserted, it is important
    to first update the cached uniprot_metadata using `insert_uniprot_metadata_for_protein_groups`,
    and only then use this method to rebuild the association table.
    '''

    engine = Session.get_bind()
    print('Truncating the protein_group_uniprot_metadata_association table')
    engine.execute('truncate protein_group_uniprot_metadata_association')

    uniprot_metadata = uniprot_utils.export_uniprot_metadata(engine)
    print('Found metadata for %s uniprot_ids' % uniprot_metadata.shape[0])

    # all (protein_group_id, uniprot_id) pairs
    group_uniprot_ids = pd.read_sql(
        '''
        select id as protein_group_id, unnest(uniprot_ids) as uniprot_id
        from mass_spec_protein_group;
        ''',
        engine
    )

    # drop isoform-specific uniprot_ids
    group_uniprot_ids['uniprot_id'] = group_uniprot_ids.uniprot_id.apply(lambda s: s.split('-')[0])

    # merge uniprot metadata on uniprot_id to get the (group_id, ensg_id) associations
    group_ensg_ids = pd.merge(uniprot_metadata, group_uniprot_ids, on='uniprot_id', how='inner')
    group_ensg_ids = group_ensg_ids.groupby(['protein_group_id', 'ensg_id']).first().reset_index()
    print('Found %s (protein_group_id, ensg_id) pairs' % group_ensg_ids.shape[0])

    # merge reference uniprot_ids on ensg_id to get the final (group_id, uniprot_id) associations
    group_consensus_ids = pd.merge(
        group_ensg_ids[['protein_group_id', 'ensg_id']],
        uniprot_metadata.loc[uniprot_metadata.is_reference],
        on='ensg_id',
        how='inner'
    )

    rows = [
        dict(protein_group_id=row.protein_group_id, uniprot_id=row.uniprot_id)
        for ind, row in group_consensus_ids.iterrows()
    ]

    print(
        'Inserting %s rows into the protein_group_uniprot_metadata_association table'
        % len(rows)
    )
    Session.bulk_insert_mappings(models.ProteinGroupUniprotMetadataAssociation, rows)
    Session.commit()


def generate_protein_group_crispr_design_associations(Session):
    '''
    Populate the association table between mass_spec_protein_group table
    and the crispr_design table using the ENSG IDs cached in the uniprot_metadata table

    Background
    ----------
    Each crispr_design is always associated with one uniprot_id and therefore one ensg_id,
    while each protein_group consists of many uniprot_ids, which may be associated
    with more than one unique ensg_id (though often only one).

    Also, there is more than one crispr_design associated with some ensg_ids.

    Note that, when new protein_groups are inserted, it is necessary
    to first update the cached ensg_ids using `insert_ensg_ids`,
    and only then call this method to rebuild the associations.
    '''

    engine = Session.get_bind()
    print('Truncating the protein_group_crispr_design_association table')
    engine.execute('truncate protein_group_crispr_design_association')

    # all crispr designs for which uniprot_metadata exists
    crispr_designs = pd.read_sql(
        '''select * from crispr_design inner join uniprot_metadata using (uniprot_id)''',
        engine
    )
    print('Found %s crispr designs' % crispr_designs.shape[0])

    # all mass spec protein groups
    groups = (
        Session.query(models.MassSpecProteinGroup)
        .options(
            db.orm.joinedload(models.MassSpecProteinGroup.uniprot_metadata)
        )
        .all()
    )
    print('Found %s protein groups' % len(groups))

    # find the crispr_designs whose ENSG IDs appear in each group's ENSG IDs
    assocs = []
    for group in groups:
        ensg_ids = [d.ensg_id for d in group.uniprot_metadata]
        crispr_design_ids = crispr_designs.loc[crispr_designs.ensg_id.isin(ensg_ids)].id.tolist()
        assocs.extend([
            dict(crispr_design_id=crispr_design_id, protein_group_id=group.id)
            for crispr_design_id in crispr_design_ids
        ])

    print('Inserting %s (protein_group, crispr_design) associations' % len(assocs))
    Session.bulk_insert_mappings(models.ProteinGroupCrisprDesignAssociation, assocs)
    Session.commit()


def main():

    args = parse_args()
    config = settings.get_config(args.mode)

    url = utils.url_from_credentials(args.credentials or config.DB_CREDENTIALS_FILEPATH)
    engine = db.create_engine(url)
    session_factory = db.orm.sessionmaker(bind=engine)
    Session = db.orm.scoped_session(session_factory)

    if args.sql_command:
        print("Executing '%s'" % args.sql_command)
        with engine.connect().execution_options(autocommit=True) as conn:
            conn.execute(db.text(args.sql_command))

    if args.populate:
        if args.drop_all:
            maybe_drop_and_create(engine, drop=True)
        else:
            maybe_drop_and_create(engine, drop=False)
        populate(Session, args.data_dir, errors='warn')

    if args.insert_plate_design:
        insert_plate_design(Session, args.plate_id, args.library_snapshot_filepath, errors='warn')

    if args.insert_electroporation:
        insert_electroporation(
            Session, plate_id=args.plate_id, electroporation_date=args.date, errors='warn'
        )

    if args.insert_facs:
        insert_facs(Session, args.facs_results_dir, errors='warn')

    # insert the 'legacy' pipeline microscopy datasets found in the 'PlateMicroscopy' directory
    # (these are datasets up to PML0179)
    if args.insert_plate_microscopy_datasets:
        filepath = os.path.join(
            args.data_dir,
            '2019-12-05_Pipeline-microscopy-master-key_PlateMicroscopy-MLs-raw.csv'
        )
        metadata = file_utils.load_legacy_microscopy_master_key(filepath)
        insert_microscopy_datasets(
            Session,
            metadata,
            root_directory='plate_microscopy',
            update=False,
            errors='warn'
        )

    # insert pipeline microscopy datasets found in the 'raw-pipeline-microscopy' directory
    # (these datasets start at PML0196 and were acquired using the dragonfly-automation scripts)
    if args.insert_raw_pipeline_microscopy_datasets:
        metadata = pd.read_csv(args.microscopy_master_key)
        metadata.rename(columns={'id': 'pml_id'}, inplace=True)
        metadata.dropna(how='any', subset=['pml_id', 'date'], axis=0, inplace=True)
        insert_microscopy_datasets(
            Session,
            metadata,
            root_directory='raw_pipeline_microscopy',
            update=args.update,
            errors='warn'
        )

    if args.insert_uniprot_metadata_for_crispr_designs:
        insert_uniprot_metadata_for_crispr_designs(Session)

    if args.insert_uniprot_metadata_for_protein_groups:
        insert_uniprot_metadata_for_protein_groups(Session)

    if args.insert_ensg_ids:
        insert_ensg_ids(Session)

    if args.generate_protein_group_associations:
        generate_protein_group_uniprot_metadata_associations(Session)
        generate_protein_group_crispr_design_associations(Session)



if __name__ == '__main__':
    main()
