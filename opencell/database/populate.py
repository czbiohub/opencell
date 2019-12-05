
import os
import sys
import sqlalchemy as db
import sqlalchemy.orm
import sqlalchemy.ext.declarative

from opencell import constants, file_utils
from opencell.database import models
from opencell.database import operations as ops


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
    # create master cell line
    # (this is the parental line for Plates 1-19)
    #
    # -----------------------------------------------------------------------------------
    print('Inserting master cell line for plates 1-19')

    master_nickname = constants.PARENTAL_LINE
    ops.get_or_create_master_cell_line(
        session, 
        nickname=master_nickname, 
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
    #
    # -----------------------------------------------------------------------------------
    print('Inserting electroporations and polyclonal lines for plates 1-19')

    electroporation_history = file_utils.load_electroporation_history(
        '../data/2019-06-24_electroporations.csv')

    master_line = ops.get_or_create_master_cell_line(session, master_nickname)
    for ind, row in electroporation_history.iterrows():
        print('Inserting electroporation of %s' % row.plate_id)

        # get the first (and, we assume, only) plate instance
        # of this electroporations's plate design
        plate_ops = ops.PlateOperations.from_id(session, row.plate_id)
        plate_instance = plate_ops.plate.plate_instances[0]

        ops.ElectroporationOperations.create_electroporation(
            session,
            master_line,
            plate_instance,
            date=row.date,
            errors=errors)


    # -----------------------------------------------------------------------------------
    #
    # cleanup
    #
    # -----------------------------------------------------------------------------------
    session.close()
