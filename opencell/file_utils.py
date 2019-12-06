import os
import sys
import re
import pandas as pd

from opencell import constants
from opencell.database import utils

def parseFloat(val):
    try:
        val = float(val)
    except ValueError:
        val = float(str(val).replace(',', ''))
    return val


# map from the column names in the cached CSVs to the column names 
# expected by the database and/or by the methods in opencell.database.operations 
# (all required columns are included, even if their name is unchanged)
LIBRARY_COLUMNS = {
    'plate_id': 'plate_id',
    'well_id': 'well_id',

    'gene_name': 'target_name',
    'family': 'target_family',

    'enst_id': 'transcript_id',
    'enst_note': 'transcript_notes', 

    'hek_tpm': 'hek_tpm',

    'terminus_to_tag': 'target_terminus',
    'terminus_choice': 'terminus_notes',
        
    'protospacer_name': 'protospacer_name', 
    'protospacer_note': 'protospacer_notes',
    'protospacer_sequence': 'protospacer_sequence',

    'ultramer_name': 'template_name',
    'ultramer_note': 'template_notes',
    'ultramer_sequence': 'template_sequence',
}

ELECTROPORATION_COLUMNS = {
    'plate_id': 'plate_id',
    'electroporation_date': 'date',
    'comment': 'notes',
}


def load_library_snapshot(filename):
    '''
    Load and format/reorganize a CSV 'snapshot' of the library spreadsheet
    
    These 'snapshots' are of the google sheet created/maintained by Manu
    that contains all info about plate and crispr design for plate 1 - plate 19.

    The snapshot *must* contain the columns on the left side of the LIBRARY_COLUMNS
    map (see above). 

    '''

    library = pd.read_csv(filename)
    library.rename(columns=LIBRARY_COLUMNS, inplace=True)

    # for clarity, format the plate_ids here
    library['plate_id'] = library.plate_id.apply(utils.format_plate_design_id)

    # parse the hek_tpm column, which should be float but has some strings with commas
    # (e.g., '1,000' instead of '1000') 
    library['hek_tpm'] = library.hek_tpm.apply(parseFloat)

    # retain only the columns we need for the database
    library = library[list(LIBRARY_COLUMNS.values())]

    return library


def load_electroporation_history(filename):
    '''
    Load and format a 'snapshot' of the list of electroporations
    (this is a google sheet from Manu)

    Expected columns: ('plate_id', 'date', 'notes')

    '''

    electroporations = pd.read_csv(filename)
    electroporations.rename(columns=ELECTROPORATION_COLUMNS, inplace=True)

    # format the plate_id
    electroporations['plate_id'] = electroporations.plate_id.apply(
        utils.format_plate_design_id)

    # drop unneeded columns
    electroporations = electroporations[list(ELECTROPORATION_COLUMNS.values())]
 
    return electroporations
    

def load_microscopy_master_key():
    '''
    This is a snapshot of the 'legacy' tab of the 'Pipeline-microscopy-master-key' google sheet
    
    These are all pipeline-related microscopy acquisitions prior to the transition to PML-based IDs
    (which occurred at ML0196)
    '''

    filepath = '../data/2019-12-05_Pipeline-microscopy-master-key_PlateMicroscopy-MLs-raw.csv'

    exp_md = pd.read_csv(filepath)
    exp_md = exp_md.rename(columns={c: c.replace(' ', '_').lower() for c in exp_md.columns})

    exp_md = exp_md.rename(columns={
        'id': 'legacy_id', 
        'automated_acquisition?': 'automation', 
        'acquisition_notes': 'notes',
        'primary_imager': 'imager',})

    exp_md = exp_md.drop(labels=[c for c in exp_md.columns if c.startswith('unnamed')], axis=1)

    # separate the ID from the date
    exp_md['id'] = exp_md.legacy_id.apply(lambda s: s.split('_')[0])

    # TODO: parse the date
    exp_md['date'] = exp_md.legacy_id.apply(lambda s: s.split('_')[1])

    # prepend the P to create the PML ID
    exp_md['pml_id'] = ['P%s' % ml_id for ml_id in exp_md.id]

    # columns to retain
    exp_md = exp_md[['pml_id', 'date', 'automation', 'imager', 'description', 'notes']]
    return exp_md


def read_and_validate_platemap(filepath):
    '''
    A 'platemap' is a CSV of well_ids and target_names
    for a single pipeline plate. Here, we load such a CSV,
    assign column names, and do some quick sanity checks.

    ***WARNING***
    This method *assumes* that the well_id appears in the first column
    and the target name appears in the second column.

    '''

    platemap = pd.read_csv(filepath, header=None)
    platemap.columns = ['well_id', 'target_name']

    # check for missing/unexpected well_ids
    missing_well_ids = set(constants.RAW_WELL_IDS).difference(platemap.well_id)
    if missing_well_ids:
        print('Warning: some well_ids are missing: %s' % missing_well_ids)

    unexpected_well_ids = set(platemap.well_id).difference(constants.RAW_WELL_IDS)
    if unexpected_well_ids:
        print('Warning: unexpected well_ids %s' % unexpected_well_ids)

    # check for missing target (gene) names
    if pd.isna(platemap.target_name).sum():
        raise ValueError('Some target names are missing in platemap %s' % filepath)

    return platemap

