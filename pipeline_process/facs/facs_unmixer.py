import os
import re
import sys
import glob
import numpy as np

from scipy import interpolate, optimize


class FACSUnmixer(object):
    
    def __init__(self, xref, yref, xs, ys, fit_window=None):
        '''
        This class 'unmixes' a sample FACS distribution using a reference
        (negative-control) distribution. 
        
        By 'unmixing', we mean identifying and removing the portion 
        of the sample distribution that probably corresponds 
        to GFP-negative cells/measurements. 

        The unmixing is accomplished in two steps:
            1) we fit the reference distribution to the left-hand 'side' 
               of the sample distribution
            2) we subtract the full fitted reference distribution 
               from the sample distribution
        
        'Fitting' means finding the offset and scale of the reference distribution
        that yields the best match between the left-hand side of the sample and reference
        distributions. We only consider the left-hand side of the distributions
        because this region corresponds to cells that are almost certainly GFP-negative;
        in many cases, GFP-positive cells are only marginally brighter than GFP-negative cells,
        leading to a subtle 'shoulder' on the *right-hand* side of the sample distribution,
        that we 1) want to avoid fitting the reference distribution to and 
        2) is, in fact, the density that we want/hope to isolate by subtracting 
        the fitted reference distribution
            
        Parameters
        ----------
        xref, yref : the x and y values of the reference distribution
        xs, ys : the x and y values of the sample distribution
        fit_window : the bounds of the left-hand 'side' of the sample distribution,
            as a tuple of (x_min, x_max).
        
        '''
    
        self.fit_window = fit_window
        
        self.xs, self.ys = xs, ys
        self.xref, self.yref = xref, yref
        
        if xref.max() > xs.max():
            print('Warning: reference range exceeds sample range')
            
        # hard-coded intial guess for (offset, scale)
        initial_offset = 2000
        initial_scale = .9
        
        # empirically determined bounds on the offset
        offset_bounds = (1500, 2500)
        
        # the scale corresponds approximately to how 'much' 
        # of the sample is GFP-negative
        scale_bounds = (0, 1)
    
        self.initial_params = (initial_offset, initial_scale)
        self.bounds = (offset_bounds, scale_bounds)

    
    def predict(self, offset, scale):
        '''
        Offset and scale the reference y-values, then interpolate them
        using the sample distribution's x-values
        (enabling us to directly calculate `y_sample - y_ref` in self.cost)
        '''
        
        x = self.xref + offset
        
        # where the reference, once offset, overlaps with the sample
        # because the offset is always positive
        overlap_mask = (self.xs >= x.min()) & (self.xs <= x.max()) 

        # interpolate the reference y-values using the sample x-values
        # where the reference overlaps the sample
        yref_interp_overlap = interpolate.interp1d(x, self.yref)(self.xs[overlap_mask])

        # pad the interpolated y-values with zeros outside of the overlap
        yref_interp = self.ys*0
        yref_interp[overlap_mask] = yref_interp_overlap
        
        # apply the scale
        yref_interp *= scale
        return yref_interp
    

    def cost(self, offset, scale):
        '''
        cost for a given offset/scale of the reference
        '''

        # scale factor to avoid premature stopping because of small absolute y-values
        internal_scale = 1/self.ys.max()

        yref_predict = self.predict(offset, scale)

        mask = (self.xs > self.fit_window[0]) & (self.xs < self.fit_window[1])
        ssq = (self.ys*internal_scale - yref_predict*internal_scale)**2
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