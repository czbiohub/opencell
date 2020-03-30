import re
import hashlib
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


    abridged = pulldown_db.copy()

    # drop replicate and pulldown_well_id from abridged, and drop replicates
    abridged.drop(columns= ['replicate', 'pulldown_well_id', 'note_on_prep'],
        inplace=True)
    abridged = abridged.dropna(how='any', subset=['design_id'])
    abridged.drop_duplicates(inplace=True)

    return abridged


def hash_proteingroup_id(protein_id):
    """
    protein group ids are made of a list of uniprot IDs in a strong form, joined by
    a semicolon. this convenience function converts sorts the uniprot IDs by alphabet
    and then hashes it using hashlib
    """

    # split the string into  a list
    prot_list = protein_id.split(';')

    # sort the list of strings, and then convert back to string
    prot_list.sort()
    protein_id = prot_list.join(';')

    # encode into utf-8 bytes
    protein_bytes = bytes(protein_id, 'utf-8')

    # hash the string in SHA-256
    prot_hash = hashlib.sha256(protein_bytes).hexdigest()

    return prot_hash
