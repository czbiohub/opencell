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
