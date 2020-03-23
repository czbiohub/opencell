import re
import numpy as np
from datetime import datetime

def format_ms_plate(plate_id):
    """
    Format Ms Plates to 'CZBMPI_%04d' % plate_number
    Also allow for 'CZBMPI%04d.d format

    """
    plate_id = str(plate_id)

    result = re.match('^CZBMPI_[0-9]{4}(.[0-9])?$', plate_id)
    if result is None:
        sub_plate = None
        plate_number = None

        # If the plate ends with subheading such as 0009.2, denoted by the
        # decimal, save the decimal
        sub_result = re.search(r'(\.[0-9]+$)', plate_id)
        if sub_result:
            sub_plate = sub_result.groups()[0]

        # Check for plate numbering
        result = re.search(r'([0-9]+)', plate_id)
        if result:
            plate_number = result.groups()[0]

        try:
            plate_number = int(plate_number)
        except Exception:
            # plate_number = 9999
            return None

        plate_id = ('CZBMPI_%04d' % plate_number)
        if sub_plate:
            if sub_plate != '.0':
                plate_id = plate_id + sub_plate

    return plate_id

def reformat_pulldown_table(pulldown_db):
    """
    combine multiple rows with different replicates into a single row,
    and add columns for well info for different replicates"""

    full = pulldown_db.copy()
    abridged = full.copy()

    # drop replicate and pulldown_well_id from abridged, and drop replicates
    abridged.drop(columns= ['replicate', 'pulldown_well_id','note_on_prep'],
        inplace=True)
    abridged = abridged.dropna(how='any', subset=['design_id', 'well_id'])
    abridged.drop_duplicates(inplace=True)

    # add replicates' well number to each row of abridged
    for rep_n  in [1,2,3]:
        rep = full[full['replicate']==rep_n][['design_id',
            'well_id','pulldown_plate_id','pulldown_well_id']]
        col_id = 'pulldown_well_rep' + str(rep_n)
        rep.rename(columns={'pulldown_well_id': col_id},
            inplace=True)
        abridged = abridged.merge(rep, how='inner', on=['design_id',
            'well_id', 'pulldown_plate_id'])


    return abridged
