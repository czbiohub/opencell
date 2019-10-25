import tifffile
import skimage
import numpy as np
import pandas as pd
from scipy import ndimage
from skimage import feature
from skimage import morphology


# for backwards compatibility
def autogain(*args, **kwargs):
    return autoscale(*args, **kwargs)


def load(filepath):
    im = tifffile.TiffFile(filepath)
    im = im.asarray()
    return im


def load_and_downscale_2x(filepath):
    '''
    *** assumes that the dimensions are (z, x, y) ***
    '''
    im = load(filepath)
    im = skimage.transform.downscale_local_mean(im, (1, 2, 2))
    return im


def autoscale(im, percentile=None, dtype='uint8', gamma=None):
    '''
    
    '''
    
    MAX = {'uint8': 255, 'uint16': 65535}
    
    im = im.copy().astype(float)
    if percentile is None:
        percentile = 0

    minn, maxx = np.percentile(im, (percentile, 100 - percentile))
    if minn==maxx:
        return (im * 0).astype(dtype)
        
    im = im - minn
    im[im < minn] = 0
    im = im/(maxx - minn)
    im[im > 1] = 1
    
    if gamma:
        im = im**gamma
    
    im = (im * MAX[dtype]).astype(dtype)
    return im

    
def dilate(im, n):
    for _ in range(n):
        im = skimage.morphology.dilation(im)
    return im


def erode(im, n):
    for _ in range(n):
        im = skimage.morphology.erosion(im)
    return im