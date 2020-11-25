import os
import pytest
import logging
from opencell import constants, file_utils
from opencell.database import models, metadata_operations

THIS_DIR = os.path.dirname(os.path.realpath(__file__))

logging.basicConfig(filename='test-log.log')
logger = logging.getLogger(__name__)


@pytest.fixture(scope='function')
def insert_plates(session):

    data_dir = os.path.join(THIS_DIR, '..', '..', 'data')
    library_snapshot = file_utils.load_library_snapshot(
        os.path.join(data_dir, '2019-06-26_mNG11_HEK_library.csv')
    )

    for plate_id in ['P0001', 'P0002']:
        plate_design = metadata_operations.get_or_create_plate_design(
            session, plate_id, create=True
        )
        metadata_operations.create_crispr_designs(
            session, plate_design, library_snapshot, drop_existing=False
        )

    progenitor_line = metadata_operations.get_or_create_progenitor_cell_line(
        session, constants.PARENTAL_LINE_NAME, create=True
    )

    # create cell lines for plate1
    plate_design = metadata_operations.get_or_create_plate_design(session, 'P0001')
    metadata_operations.create_polyclonal_lines(
        session,
        progenitor_line,
        plate_design,
        date='2020-01-01',
    )

    # create cell lines for plate2
    plate_design = metadata_operations.get_or_create_plate_design(session, 'P0002')
    metadata_operations.create_polyclonal_lines(
        session,
        progenitor_line,
        plate_design,
        date='2020-01-01',
    )


def test_get_or_create_progenitor_cell_line(session):

    name = constants.PARENTAL_LINE_NAME
    metadata_operations.get_or_create_progenitor_cell_line(session, name, create=True)
    lines = session.query(models.CellLine).all()
    assert len(lines) == 1
    assert lines[0].name == name
    assert lines[0].line_type.value == 'PROGENITOR'

    # test retrieving the line
    line = metadata_operations.get_or_create_progenitor_cell_line(session, name, create=False)
    assert line.name == name

    # try to get a non-existent line
    line = metadata_operations.get_or_create_progenitor_cell_line(
        session, 'nonexistent-name', create=False
    )
    assert line is None


@pytest.mark.usefixtures('insert_plates')
def test_get_or_create_plate_design(session):

    # check that we can retrieve the plate1 design
    plate_id = session.query(models.PlateDesign).first().design_id
    plate_design = metadata_operations.get_or_create_plate_design(session, plate_id)
    assert plate_design.design_id == plate_id

    # retrieve the plate1 design
    plate_design = metadata_operations.get_or_create_plate_design(session, 'P0001')
    assert plate_design.design_id == 'P0001'

    # create a new plate with a fake design_id
    metadata_operations.get_or_create_plate_design(
        session, 'P0000', date='2020-02-02', notes='design notes!', create=True
    )
    plate_design = (
        session.query(models.PlateDesign)
        .filter(models.PlateDesign.design_id == 'P0000')
        .one()
    )
    assert plate_design.design_id == 'P0000'

    # retrieving a non-existent plate_id should raise an error
    with pytest.raises(ValueError):
        metadata_operations.get_or_create_plate_design(session, 'P001', create=False)


@pytest.mark.usefixtures('insert_plates')
def test_create_crispr_designs(session):

    # check that we inserted 96*2 crispr_designs
    designs = session.query(models.CrisprDesign).all()
    assert len(designs) == 96*2

    # check that they have the expected plate_ids
    plate_ids = [design.plate_design_id for design in designs]
    assert set(plate_ids) == set(['P0001', 'P0002'])


@pytest.mark.usefixtures('insert_plates')
def test_create_polyclonal_lines(session):
    '''
    Test that the expected polyclonal cell lines were inserted
    by the calls to create_polyclonal_lines in the 'insert_plates' fixture

    Note that there is no need to call the fixture again, since pytest called it above,
    when the TestPolyclonalLines class was executed
    '''
    # check that we inserted the correct number of lines
    lines = session.query(models.CellLine).filter(models.CellLine.line_type == 'POLYCLONAL').all()
    assert len(lines) == 96*2
    assert lines[0].parent.name == constants.PARENTAL_LINE_NAME

    # check that the lines have the correct plate_id
    plate_ids = [line.crispr_design.plate_design_id for line in lines]
    assert set(plate_ids) == set(['P0001', 'P0002'])


@pytest.mark.usefixtures('insert_plates')
class TestPolyclonalLineOperations:

    def test_from_line_id(self):
        pass

    def test_from_plate_well(self):
        pass

    def test_from_target_name(self):
        pass
