import os
import re
import sys
import glob
import numpy as np
import pandas as pd


def plate_id_from_number(plate_num):
    plate_id = 'P%04d' % plate_num
    return plate_id


CONTROL_DIRNAMES = {
    'P0001': 'WT_plate1redomNG',
    'P0002': 'WT_plate2redomNG',
    'P0003': 'WT_plate3redomNG',
    'P0004': 'WT_plate4redomNG',
}

# TODO: is P0001 data in 'plate1_redo_FCS' or 'plate1_FCS_plate1_mNG'?
SAMPLE_DIRNAMES = {
    'P0001': 'plate1_redo_FCS',
    'P0002': 'plate2_redo_FCS',
    'P0003': 'plate3_redo_FCS',
    'P0004': 'plate4_redo_FCS',
}

# the remaining plates (plate5-plate19) have consistent directory names
# that we can generate programmatically
plate_nums = range(5, 20)
for plate_num in plate_nums:
    plate_id = plate_id_from_number(plate_num)
    SAMPLE_DIRNAMES[plate_id] = 'plate%d_FCS' % plate_num
    CONTROL_DIRNAMES[plate_id] = 'WT_plate%dmNG' % plate_num

# HACK: there was no control for plate18, so we use plate17
CONTROL_DIRNAMES['P0018'] = CONTROL_DIRNAMES['P0017']


class FACSManager(object):

    def __init__(self, box_root):
        '''
        box_root : local path to the Box 'root' directory
        '''
    
        self.box_root = box_root
        self.facs_data_root = os.path.join(self.box_root, 'FACS_data')
    

    def _get_dirpath(self, plate_id, data_type=None):

        if data_type == 'control':
            dirnames = CONTROL_DIRNAMES
        if data_type == 'sample':
            dirnames = SAMPLE_DIRNAMES
    
        if not dirnames.get(plate_id):
            raise ValueError('No %s data dirname for plate %s' % (data_type, plate_id))
    
        path = os.path.join(self.facs_data_root, dirnames[plate_id])
        if data_type == 'sample':
            path = os.path.join(path, 'profile_data')

        if not os.path.isdir(path):
            raise ValueError('Directory %s does not exist' % path)
        return path


    def get_sample_and_control_dirpaths(self, plate_id):
        '''
        Public method to get a tuple of sample and control paths
        to the directories containing the sample and negative control datasets
        for the given plate_id

        plate_id : either a plate_id of the form 'P0001' or a plate number 
        '''

        if isinstance(plate_id, int):
            plate_id = plate_id_from_number(plate_id)

        return (
            self._get_dirpath(plate_id, 'sample'), 
            self._get_dirpath(plate_id, 'control')
        )

