import os
import re
import sys
import glob
import json
import shutil
import pickle
import hashlib
import skimage
import datetime
import tifffile
import numpy as np
import pandas as pd

from scipy import ndimage
from skimage import feature
from skimage import morphology

from . import utils


def generate_background_mask(im, sigma, rel_thresh):
    
    # smooth the raw image
    imf = skimage.filters.gaussian(im, sigma=sigma)

    # background mask from minimum cross-entropy
    thresh = rel_thresh * skimage.filters.threshold_li(imf)
    mask = imf > thresh
    mask = skimage.morphology.erosion(mask)
    return mask


def filter_lg(im, sigma):
    '''
    Laplace transform of gaussian-filtered image
    '''
    
    imf = skimage.filters.gaussian(im, sigma=sigma)
    im_lg = skimage.filters.laplace(imf, ksize=3)
    return im_lg


def generate_lg_mask(im, mask_bg, sigma, radius, percentile, max_area, min_area, debug=False):
    '''
    sigma : radius of gaussian for smoothing
    radius : size of the disk for the closing operation
    percentile : intensity threshold for the local minima mask
    max_area : maximum area of holes to fill
    min_area : minimum area of region in the local minimum mask to remove from the background mask

    Steps 
    1) generate a 'refined' background mask by thresholding the laplace transform at zero
    2) morphologically close this mask and fill holes until there are no intranuclear holes or gaps
       (empirically, this requires closing with disk(4))
    3) multiply this 'refined' mask by the existing crude background mask (`mask_bg`) 
       to restore any 'true' holes/gaps that were present in `mask_bg`
    4) generate a mask of local minima in the laplace transform,
       using a percentile threshold (5%-7% works well)
    5) iterate over regions in this local-minima mask and remove them from the refined mask
       if they partially intersect/overlap with the background of the refined mask

    This procedure helps to capture the narrow regions and gaps between clumped nuclei,
    which dramatically improves the accuracy of the nucleus positions 
    extracted from the distance-transformed mask.

    An alternative and likely better approach would be to find a more sophisticated way
    of 'filling in' the interiors of the nuclei in the refined background mask;
    the use of closing followed by hole-filling here is so crude that the hackish use
    of the local minima mask to add back 'real' gaps between nuclei becomes necessary
    to meaningfully improve over the 'crude' background mask `mask_bg`.

    '''

    # the Laplacian of a Gaussian
    im_lg = filter_lg(im, sigma)
    mask = (im_lg > 0) * mask_bg

    mask = skimage.morphology.closing(mask, skimage.morphology.disk(radius))
    mask = skimage.morphology.remove_small_holes(mask, area_threshold=max_area, connectivity=1)

    # multiply by mask_bg again to retain any holes that were present
    # in the background mask (which we can assume are real)
    mask *= mask_bg

    # create a mask of local minima in the LoG image
    min_mask = im_lg < np.percentile(im_lg, percentile)

    # remove regions in the local minima mask from the foreground of the mask
    # if they partially overlap with the background of mask
    min_mask_l = skimage.measure.label(min_mask, connectivity=1)
    props = skimage.measure.regionprops(min_mask_l)
    for prop in props:
        region_overlaps_background = np.min(mask[prop.coords[:, 0], prop.coords[:, 1]]) == 0
        if region_overlaps_background or prop.area > min_area:
            mask[prop.coords[:, 0], prop.coords[:, 1]] = False

    if debug:
        return mask, min_mask, im_lg
    return mask



def find_nucleus_positions(mask, min_distance):
    
    # smoothed distance transform
    dist = ndimage.distance_transform_edt(mask)
    distf = skimage.filters.gaussian(dist, sigma=1)

    # the positions of the local maximima in the distance transform
    # correspond roughly to the centers of mass of the individual nuclei
    positions = skimage.feature.peak_local_max(
        distf, indices=True, min_distance=min_distance, labels=mask)
    return positions


def generate_watershed_mask(mask, min_distance, mask_bg=None):
    '''
    Watershed a background mask using the distance transform approach
    mask : the background mask to distance-transform
    min_distance : minimum distance between local maxima in the distance transform
        to use as seeds for the watershed
    mask_bg : optional, less stringent mask to use for the watershed itself
    '''

    if mask_bg is None:
        mask_bg = mask

    dist = ndimage.distance_transform_edt(mask)
    distf = skimage.filters.gaussian(dist, sigma=1)

    local_max = skimage.feature.peak_local_max(
        distf, indices=False, min_distance=min_distance, labels=mask)
    labeled_local_max, num_local_max = ndimage.label(local_max)

    mask_labeled = skimage.morphology.watershed(
        -distf.astype(float), 
        mask=mask_bg, 
        markers=labeled_local_max, 
        watershed_line=True,
        compactness=.01)

    mask = utils.remove_edge_regions(mask_labeled)
    mask_labeled = skimage.measure.label(mask, connectivity=1)
    return mask_labeled
