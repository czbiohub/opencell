import io
import base64
import skimage
import imageio
import tifffile
import numpy as np
import pandas as pd
from scipy import ndimage
from skimage import feature
from skimage import morphology


def load(filepath):
    im = tifffile.TiffFile(filepath)
    im = im.asarray()
    return im


def load_and_downscale_2x(filepath):
    '''
    Load a 3D TIFF stack and downsample it by a factor of two in x and y
    (assumes that the order of dimensions is (z, x, y))
    '''
    im = load(filepath)
    im = skimage.transform.downscale_local_mean(im, (1, 2, 2))
    return im


def b64encode_image(image, format, **kwargs):
    with io.BytesIO() as file:
        imageio.imsave(file, image, format=format, **kwargs)
        s = base64.b64encode(file.getvalue()).decode('utf-8')
    return s


def autoscale(im, percentile=None, p=None, dtype='uint8', gamma=None):
    '''
    '''

    max_values = {'float': 1.0, 'uint8': 255, 'uint16': 65535}

    if p is not None:
        percentile = p
    if percentile is None:
        percentile = 0

    im = im.copy().astype(float)
    minn, maxx = np.percentile(im, (percentile, 100 - percentile))
    if minn == maxx:
        return (im * 0).astype(dtype)

    im = im - minn
    im[im < 0] = 0
    im = im/(maxx - minn)
    im[im > 1] = 1
    if gamma is not None:
        im = im**gamma

    im = (im * max_values[dtype]).astype(dtype)
    return im


# alias for autoscale, for backwards compatibility
def autogain(*args, **kwargs):
    return autoscale(*args, **kwargs)


def remove_small_regions(mask, min_area, conn=1):
    '''
    Remove regions that are too small or too large from the mask
    '''
    mask_label = skimage.measure.label(mask, connectivity=conn)
    props = skimage.measure.regionprops(mask_label)
    for prop in props:
        if prop.area < min_area:
            mask[mask_label == prop.label] = False
    return mask > 0


def remove_large_regions(mask, max_area, conn=1):
    '''
    Remove regions whose area is greater than max_area from the mask
    '''
    mask_label = skimage.measure.label(mask, connectivity=conn)
    props = skimage.measure.regionprops(mask_label)
    for prop in props:
        if prop.area > max_area:
            mask[mask_label == prop.label] = False
    return mask > 0


def remove_edge_regions(mask, conn=1):
    '''
    Remove regions in the mask that touch one or more edges of the image
    '''
    mask_out = mask.copy()
    mask_label = skimage.measure.label(mask, connectivity=conn)
    props = skimage.measure.regionprops(mask_label)
    for prop in props:
        if min(prop.bbox) == 0 or prop.bbox[2] == mask.shape[0] or prop.bbox[3] == mask.shape[1]:
            mask_out[mask_label == prop.label] = False
    return mask_out > 0
