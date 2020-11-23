import pytest
import sqlalchemy as sq
from opencell.database import models, utils


@pytest.fixture(scope='session')
def db_credentials():
    yield utils.url_from_credentials('db-credentials-test.json')


@pytest.fixture()
def engine(db_credentials):
    engine = sq.create_engine(db_credentials)
    yield engine
    engine.dispose()


@pytest.fixture()
def session(engine):
    '''
    Set up and tear down a database connection and sqlalchemy session
    '''
    # setup a non-ORM transaction and start a session in a savepoint
    # (this follows the approach taken in imagingdb)
    connection = engine.connect()
    transaction = connection.begin()
    session = sq.orm.sessionmaker()(bind=connection)
    session.begin_nested()

    # create the tables
    models.Base.metadata.create_all(connection)

    yield session

    # close the session and rollback everything (including calls to commit)
    session.close()
    transaction.rollback()
    connection.close()
    engine.dispose()
