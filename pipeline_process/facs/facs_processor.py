import os
import re
import sys
import glob
import numpy as np
import pandas as pd

import FlowCytometryTools as fct
from matplotlib import pyplot as plt

from pipeline_process.facs import constants as facs_constants
from pipeline_process.common import constants as common_constants


# FACS dataset channel names
FITC, SSC, FSC = 'FITC-A', 'SSC-A', 'FSC-A'


class FACSProcessor(object):


    def __init__(self, sample_dirpath, control_dirpath):
        '''
        Class to load and process the FACS data from a single pipeline plate

        `sample_dirpath` is the path to a local directory containing the raw FCS data
        for all samples on the plate. There should be one FCS file per well, 
        and the filenames must adhere to the pattern '{well_id}_Data.fcs'

        `control_dirpath` is the path a local directory containing all of the negative control
        data (or 'wt' data) for the plate. The filenames of these files are unimportant; 
        we assume that all FCS files in this directory correspond to a negative control. 

        Internally, samples are identified *only* by the well_id appearing in each FCS filename.


        Parameters
        ----------

        Public methods
        --------------

        '''

        self.sample_dirpath = sample_dirpath
        self.control_dirpath = control_dirpath

        self.well_ids, self.control_filepaths = self._validate()

    
    def _validate(self):
        '''
        Check for missing/unexpected sample datasets
        and the expected number of control datasets
        '''
    
        filenames = glob.glob(os.path.join(self.sample_dirpath, '*.fcs'))
        well_ids = [filename.split(os.sep)[-1].split('_')[0] for filename in filenames]
        missing_well_ids = set(common_constants.WELL_IDS).difference(well_ids)
        unexpected_well_ids = set(well_ids).difference(common_constants.WELL_IDS)

        if missing_well_ids:
            print('Warning: there is no FCS file for some well_ids: %s' % missing_well_ids)
        if unexpected_well_ids:
            print('Warning: FCS files for unexpected well_ids %s' % unexpected_well_ids)
    
        # count the number of negative control datasets
        control_filepaths = glob.glob(os.path.join(self.control_dirpath, '*.fcs'))
        if len(control_filepaths) != facs_constants.NUM_CONTROL_DATASETS:
            raise ValueError('Expected %s control datasets but found %s' % \
                (facs_constants.NUM_CONTROL_DATASETS, len(control_filepaths)))
        
        return well_ids, control_filepaths


    def sample_filepath(self, well_id):
        '''
        Construct the filepath of the dataset for a given well_id    
        '''
        
        if well_id not in common_constants.WELL_IDS:
            raise ValueError('Invalid well_id %s' % well_id)
 
        # we *assume* that the filename is of this form
        filename = '%s_Data.fcs' % well_id
        filepath = os.path.join(self.sample_dirpath, filename)
        return filepath
    

    def load_sample(self, well_id):
        '''
        Load, transform, and gate a sample dataset
        '''
        
        dataset = fct.FCMeasurement(ID=well_id, datafile=self.sample_filepath(well_id))
        dataset = self.transform_and_gate_dataset(dataset)
        return dataset


    def process_sample(self, well_id):
        '''
        '''
        pass


    def load_controls(self):
        '''
        Load, transform, and gate all of the negative control datasets
        '''

        datasets = []
        for ind, filepath in enumerate(self.control_filepaths):
            dataset_id = 'nc-%s' % ind
            dataset = fct.FCMeasurement(ID=dataset_id, datafile=filepath)
            dataset = self.transform_and_gate_dataset(dataset)
            datasets.append(dataset)
        return datasets


    def concatenate_controls(self):
        '''
        Concatenate the mean-subtracted FITC measurements from all control datasets
        '''

        controls = self.load_controls()

        # the means of each dataset (generally around 2000 +/- 200)
        all_means = [control.data[FITC].values.mean() for control in controls]

        all_values = []
        for control in controls:
            values = control.data[FITC].values
            mean = values.mean()
            all_values.append(values - mean)
            print('Control dataset %s: n=%d, mean=%d' % (control.ID, values.shape[0], mean))

        all_values = np.concatenate(tuple(all_values), axis=0)
        return all_values, all_means



    @staticmethod
    def transform_and_gate_dataset(dataset):
        '''
        Apply hard-coded gates to select viable single cells,
        and hlog-transform the dataset

        Parameters
        ----------
        dataset : an FCMeasurement instance

        '''

        # transform first
        dataset = dataset.transform('hlog', channels=[FITC, FSC, SSC], b=facs_constants.HLOG_B)
        
        # apply gates
        dataset = dataset.gate(facs_constants.VIABLE_GATE).gate(facs_constants.SINGLET_GATE)

        return dataset
    