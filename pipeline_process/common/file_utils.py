import os
import sys
import re
import pandas as pd

from pipeline_process.common import constants


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
    missing_well_ids = set(constants.WELL_IDS).difference(platemap.well_id)
    if missing_well_ids:
        print('Warning: some well_ids are missing: %s' % missing_well_ids)

    unexpected_well_ids = set(platemap.well_id).difference(constants.WELL_IDS)
    if unexpected_well_ids:
        print('Warning: unexpected well_ids %s' % unexpected_well_ids)

    # check for missing target (gene) names
    if pd.isna(platemap.target_name).sum():
        raise ValueError('Some target names are missing in platemap %s' % filepath)

    return platemap

