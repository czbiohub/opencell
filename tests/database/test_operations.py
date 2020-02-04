import pytest
from opencell.database import models, operations


def test_create_all(engine):

    models.Base.metadata.drop_all(engine)
    models.Base.metadata.create_all(engine)
    models.Base.metadata.drop_all(engine)


def test_get_or_create_progenitor_cell_line(session):

    name = 'best-progenitor-line-ever'
    operations.get_or_create_progenitor_cell_line(session, name, create=True)

    lines = session.query(models.CellLine).all()
    assert len(lines) == 1
    assert lines[0].name == name
