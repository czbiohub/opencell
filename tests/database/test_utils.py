import os
import pytest
import opencell.database.utils as db_utils


def test_format_plate_design_id():

    valid_plate_ids = [123, 'plate123', 'Plate 123', 'P0123']
    for plate_id in valid_plate_ids:
        assert db_utils.format_plate_design_id(plate_id) == 'P0123'

    # plate number can be zero
    assert db_utils.format_plate_design_id('0') == 'P0000'

    invalid_plate_ids = ['', 'a', None, 'Plate  1', 'plate']
    for plate_id in invalid_plate_ids:
        with pytest.raises(ValueError):
            db_utils.format_plate_design_id(plate_id)


def test_format_well_id():

    assert db_utils.format_well_id('A1') == 'A01'
    assert db_utils.format_well_id('A9') == 'A09'
    assert db_utils.format_well_id('A10') == 'A10'
    assert db_utils.format_well_id('A99') == 'A99'

    # invalid well_ids are returned unmodified
    assert db_utils.format_well_id('Z1') == 'Z1'
    assert db_utils.format_well_id('Z10') == 'Z10'


def test_is_sequence():

    seqs = ['', 'a', 'c', 't', 'g', 'aaa', 'A', 'Aa', 'acgt', 'ACGT']
    for seq in seqs:
        assert db_utils.is_sequence(seq)

    seqs = [' ', '-', 'b', 'abc', 'a.', 'a ', 'a a']
    for seq in seqs:
        assert not db_utils.is_sequence(seq), "'%s'" % seq
