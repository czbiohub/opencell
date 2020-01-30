import os
import re
import sys
import glob
import numpy as np

from scipy import interpolate, optimize


class FACSUnmixer(object):
    
    def __init__(self, xref, yref, xs, ys, offset_guess, offset_bounds, fit_window):
        '''
        This class 'unmixes' a sample FACS distribution using a reference
        (negative-control) distribution. 
        
        By 'unmixing', we mean identifying and removing the portion 
        of the sample distribution that corresponds to the GFP-negative population. 
        This is not as straightforward as simply subtracting a reference distribution
        from the sample distribution, because 1) the mean intensity of the GFP-negative population
        shifts (by ~10 percent) from sample to sample, due to biological variability,
        and 2) the magnitude of the GFP-negative peak in the sample distribution
        depends on the magnitude of the GFP-positive peak. 

        To address these complexities, the unmixing is accomplished by 'fitting'
        a reference distribution to the left-hand 'side' of the sample distribution.

        'Fitting' means finding the offset and scale of the reference distribution
        that yields the best match between the left-hand side of the sample and reference
        distributions. We only consider the left-hand side of the distributions
        because this region corresponds to cells that are almost certainly GFP-negative;
        in some cases, GFP-positive cells are only marginally brighter than GFP-negative cells,
        leading to a subtle 'shoulder' on the *right-hand* side of the sample distribution,
        that we want to avoid fitting the reference distribution 
        (especially because this shoulder is, in fact, the density that we hope to isolate 
        by subtracting the fitted reference distribution). 

        Parameters
        ----------
        xref, yref : the x and y values of the mean-subtracted reference distribution
        xs, ys : the x and y values of the sample distribution
        offset_guess : initial guess for the offset parameter;
            should be equal to the reference mean
        offset_bounds : min/max bounds for the offset parameter;
            should be given by the reference mean +/- the reference standard deviation. 
        fit_window : the bounds of the left-hand 'side' of the sample distribution,
            as a tuple of (x_min, x_max). Should generally be (0, ref_mean + ref_std).
        
        '''
        
        if xref.max() > xs.max():
            print('Warning: reference range exceeds sample range')
            
        self.xs, self.ys = xs, ys
        self.xref, self.yref = xref, yref
            
        self.fit_window = fit_window

        # hard-coded bounds for the scale factor, 
        # which roughly corresponds to how 'much' of the sample is GFP-negative
        scale_guess = .9
        scale_bounds = (0, 1)
    
        self.bounds = (offset_bounds, scale_bounds)
        self.initial_params = (offset_guess, scale_guess)

    
    def predict(self, offset, scale):
        '''
        Offset and scale the reference y-values, then interpolate them
        using the sample distribution's x-values
        (so that we can directly calculate `y_sample - y_ref` in self.cost)
        '''
        
        x = self.xref + offset
        
        # the x-range where the reference, once offset, overlaps with the sample
        overlap_mask = (self.xs >= x.min()) & (self.xs <= x.max()) 

        # sanity check that there is not none overlap
        if not overlap_mask.sum():
            raise ValueError('The reference does not overlap the sample at an offset of %0.2f' % offset)

        # interpolate the reference y-values using the sample x-values
        # where the reference overlaps the sample
        yref_interp_overlap = interpolate.interp1d(x, self.yref)(self.xs[overlap_mask])

        # pad the interpolated y-values with zeros outside of the overlap
        yref_interp = self.ys * 0
        yref_interp[overlap_mask] = yref_interp_overlap
        
        # apply the scale
        yref_interp *= scale
        return yref_interp
    

    def cost(self, offset, scale):
        '''
        Cost for a given offset/scale of the reference
        '''

        # scale factor to avoid premature stopping because of small absolute y-values
        internal_scale = 1 / self.ys.max()

        yref_predict = self.predict(offset, scale)

        ssq = (self.ys * internal_scale - yref_predict * internal_scale)**2
        mask = (self.xs > self.fit_window[0]) & (self.xs < self.fit_window[1])
        cost = ssq[mask].sum()
        return cost
        
        
    def fit(self):
        
        def cost_function(params):
            return self.cost(*params)
    
        result = optimize.minimize(
            cost_function, 
            self.initial_params, 
            method='L-BFGS-B',
            bounds=self.bounds)
        
        return result