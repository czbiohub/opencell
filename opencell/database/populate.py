'''
Initialize and populate a new pipeline database
from a set of 'snapshot' CSVs of various google spreadsheets

Keith Cheveralls
July 2019

'''

import os
import sys
import sqlalchemy as db
import sqlalchemy.orm
import sqlalchemy.ext.declarative

from opencell.database import models
from opencell.database import operations as ops
from opencell import file_utils


def populate(url, drop_all=False, errors='warn'):
    '''

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
    #
    # -----------------------------------------------------------------------------------
    print('Inserting master cell line')

    master_nickname = 'mNG1-10'
    ops.get_or_create_master_cell_line(
        session, 
        nickname=master_nickname, 
        notes='HEK-293 background', 
        create=True)


    # -----------------------------------------------------------------------------------
    #
    # Insert crispr designs from Library snapshot
    #
    # -----------------------------------------------------------------------------------
    print('Inserting crispr designs')

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
    print('Inserting electroporations and polyclonal lines')

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
