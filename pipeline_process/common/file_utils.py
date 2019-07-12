import os
import sys
import re
import pandas as pd

from pipeline_process.common import constants


def read_and_validate_platemap(filepath):
    '''
    Do some quick sanity checks
    '''

    platemap = pd.read_csv(filepath, header=None)
    platemap.columns = ['well_id', 'target_name']

    # check well_ids
    if set(platemap.well_id)!=set(constants.WELL_IDS):
        raise ValueError('Unexpected well_ids in platemap %s' % filepath)

    # check for missing target (gene) names
    if pd.isna(platemap.target_name).sum():
        raise ValueError('Missing gene names in platemap %s' % filepath)

    return platemap