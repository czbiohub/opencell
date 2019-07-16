import os
import re
import sys
import glob
import numpy as np
import pandas as pd

import FlowCytometryTools as fct
from matplotlib import pyplot as plt
from scipy import interpolate, optimize

from pipeline_process.facs.unmixer import FACSUnmixer
from pipeline_process.facs import constants as facs_constants
from pipeline_process.common import constants as common_constants

# FACS dataset channel names
FITC, SSC, FSC = 'FITC-A', 'SSC-A', 'FSC-A'



class FACSProcessor(object):


    def __init__(self, samples_dirpath, controls_dirpath):
        '''
        Class to load and process the FACS data from a single pipeline plate

        `samples_dirpath` is the path to a local directory containing the raw FCS data
        for all samples on the plate. There should be one FCS file per well, 
        and the filenames must adhere to the pattern '{well_id}_Data.fcs'

        `controls_dirpath` is the path a local directory containing all of the negative controls
        (that is, wild-type samples) for the plate. The filenames of these files are unimportant; 
        we assume that all FCS files in this directory correspond to a negative control. 

        Internally, samples are identified *only* by the well_id appearing in each FCS filename.


        Parameters
        ----------

        Public methods
        --------------

        '''

        self.samples_dirpath = samples_dirpath
        self.controls_dirpath = controls_dirpath

        self.well_ids, self.control_filepaths = self._validate_datasets()

        # load negative controls
        self.controls = self._load_controls()

        # concatenate controls and calc global mean/std
        control_values, control_mean, control_std = self._concatenate_controls()
    
        # generate the reference (negative control) histogram
        self.x_ref, self.y_ref = self.generate_control_histogram(control_values)

        # we'll also need the mean/std during sample processing
        self.ref_mean, self.ref_std = control_mean, control_std


    def _validate_datasets(self):
        '''
        Check for missing/unexpected sample datasets
        and the expected number of control datasets
        '''
    
        filenames = glob.glob(os.path.join(self.samples_dirpath, '*.fcs'))
        well_ids = [filename.split(os.sep)[-1].split('_')[0] for filename in filenames]

        # check for missing/unexpected well_ids
        missing_well_ids = set(common_constants.WELL_IDS).difference(well_ids)
        if missing_well_ids:
            print('Warning: there is no FCS file for some well_ids: %s' % missing_well_ids)

        unexpected_well_ids = set(well_ids).difference(common_constants.WELL_IDS)
        if unexpected_well_ids:
            print('Warning: FCS files for unexpected well_ids %s' % unexpected_well_ids)
    
        # count the number of negative control datasets
        control_filepaths = glob.glob(os.path.join(self.controls_dirpath, '*.fcs'))
        if len(control_filepaths) != facs_constants.NUM_CONTROL_DATASETS:
            print('Warning: expected %s control datasets but found %s' % \
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
        filepath = os.path.join(self.samples_dirpath, filename)
        return filepath
    

    def load_sample(self, well_id):
        '''
        Load, transform, and gate a sample dataset
        '''
        
        dataset = fct.FCMeasurement(ID=well_id, datafile=self.sample_filepath(well_id))
        dataset = self.transform_and_gate_dataset(dataset)
        return dataset



    def _load_controls(self):
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


    def _concatenate_controls(self):
        '''
        Concatenate the mean-subtracted FITC measurements from all control datasets
        '''

        ns, means, all_values = [], [], []
        for control in self.controls:
            values = control.data[FITC].values
            n = values.shape[0]
            mean = values.mean()

            ns.append(n)
            means.append(mean)
            all_values.append(values - mean)

            print('Loaded control dataset %s: n=%d, mean=%d' % (control.ID, n, mean))

        all_values = np.concatenate(tuple(all_values), axis=0)

        # calculate global mean and std
        ns = np.array(ns)
        means = np.array(means)
        global_mean = (means * ns).sum() / ns.sum()
        global_std = np.std(all_values)

        return all_values, global_mean, global_std


    @classmethod
    def generate_control_histogram(cls, values):
        '''
        Generate the reference (negative-control) histogram
        using percentile-based x-axis range to eliminate outliers
        '''

        # percentile=.2 corresponds to a bit more than +/- 3 standard deviations
        x, y = cls.generate_histogram(values, percentile=.2)
        return x, y


    @classmethod
    def generate_sample_histogram(cls, values):
        '''
        Generate a sample histogram using an absolute hard-coded x-axis range,
        based on empirical observation
        '''
        x, y = cls.generate_histogram(values, xrange=(0, 10000), nbins=None)
        return x, y


    @staticmethod
    def generate_histogram(values, xrange=None, nbins=None, percentile=0, verbose=False):
        '''
        Helper method to generate a histogram given either an explicit min/max range
        or a percentile range and, maybe, the number of bins

        Returns a pair of (x, y) vectors corresponding to the bin centers
        and the normalized counts in each bin.
        '''

        if nbins is None and xrange is not None and verbose:
            print('Warning: a range was provided but the number of bins was not provided')

        # calculate the x-range from the percentile 
        # (defaults to max/min because percentile=1)
        if xrange is None:
            xrange = np.percentile(values, (percentile, 100 - percentile))
        minn, maxx = xrange

        # if nbins is not specified, use the 'Rice Rule' to estimate the optimal number of bins
        # (this assumes that `xrange` spans most of the data; otherwise, `len(values)`
        # will not correspond to the number of data points present in the histogram)
        # also, note that if `xrange` is proportional to the standard deviation,
        # then this rule is similar to "Scott's rule" for the optimal bin width.
        if nbins is None:
            nbins = 2 * len(values)**(1/3)
            if verbose:
                print('Using nbins=%d' % nbins)

        bin_width = (maxx - minn)/nbins
        bins = np.arange(minn, maxx, bin_width)
        bin_counts, bin_edges = np.histogram(values, bins=bins, density=True)

        bin_centers = bin_edges[1:] - bin_width/2
        return bin_centers, bin_counts


    @staticmethod
    def transform_and_gate_dataset(dataset):
        '''
        Apply hard-coded gates to select viable single cells,
        and hlog-transform the dataset

        Parameters
        ----------
        dataset : an FCMeasurement instance

        '''

        # transform first...
        dataset = dataset.transform('hlog', channels=[FITC, FSC, SSC], b=facs_constants.HLOG_B)
        
        # ...and then apply the gates
        dataset = dataset.gate(facs_constants.VIABLE_GATE).gate(facs_constants.SINGLET_GATE)

        return dataset
    
    

    def process_sample(self, well_id, show_plots=True):
        '''
        '''
        
        # load the dataset and generate its histogram
        dataset = self.load_sample(well_id)
        x_sample, y_sample = self.generate_sample_histogram(dataset.data[FITC])

        # parameters for fitting the control (reference) histogram to the sample histogram
        offset_guess = self.ref_mean
        offset_bounds = (self.ref_mean - self.ref_std, self.ref_mean + self.ref_std)

        # this window defines the extent of the 'left side' of the sample histogram,
        # to which we will fit the reference histogram
        fit_window = (0, self.ref_mean + self.ref_std)

        unmixer = FACSUnmixer(
            self.x_ref,
            self.y_ref, 
            x_sample,
            y_sample, 
            offset_guess=offset_guess, 
            offset_bounds=offset_bounds, 
            fit_window=fit_window)
        
        # do the fit
        result = unmixer.fit()

        # extract the offset and scale of the fitted reference
        self.best_offset, self.best_scale = result.x

        # the fitted reference histogram
        y_ref_fitted = unmixer.predict(*result.x)

        # the unmixed sample histogram
        y_sample_unmixed = y_sample - y_ref_fitted

        if show_plots:
            plt.plot(x_sample, y_sample)
            plt.plot(x_sample, y_ref_fitted)
            plt.plot(x_sample, y_sample_unmixed)

        # use the fit parameters to define a boundary between the left and right hand 'sides'
        # (that is, between GFP-negative and -positive populations)
        left_right_boundary = self.best_offset + self.ref_std

        # calculate stats of the right-hand side of the unmixed histogram
        stats = self.calc_unmixed_stats(x_sample, y_sample_unmixed, left_right_boundary)
        return stats


    @staticmethod
    def calc_unmixed_stats(x, y, left_right_boundary):
        '''
        '''

        def as_int(value):
            try:
                value = int(value)
            except ValueError:
                value = None
            return value

        mask = x > left_right_boundary
        x = x[mask]
        y = y[mask]

        # default values
        area = 0
        mean, std, median, p99 = None, None, None, None

        # the area of the right-hand side of the unmixed sample histogram
        area = y.sum() * (x[1] - x[0])

        # if the area is less than zero, there's no distribution to quantify
        if area > 0:
    
            # the mean/std of the right-hand side of the unmixed sample histogram
            mean = (y * x).sum() / y.sum()
            std = ((y * x**2).sum() / y.sum() - mean**2)**.5

            # median and 99th percentile of the right-hand side 
            # (by interpolating the cumulative histogram)
            y_c = np.cumsum(y)
            y_c /= y_c.max()
            median, p99 = interpolate.interp1d(y_c, x)([.5, .99])

        stats = {
            'area': as_int(area*100),
            'intensity_mean': as_int(mean),
            'intensity_std': as_int(std),
            'intensity_median': as_int(median),
            'intensity_p99': as_int(p99),
        }

        return stats