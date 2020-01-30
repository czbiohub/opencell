
import skimage
import numpy as np
import pandas as pd
import seaborn as sns

from matplotlib import pyplot as plt
from matplotlib import colors as mplcolors

from . import utils


def imshow(im, figsize=12, cmap='gray', colorbar=True):
    '''
    '''
    plt.figure(figsize=(figsize, figsize))
    plt.imshow(im, cmap=cmap)
    if im.dtype != 'bool' and im.ndim == 2 and colorbar:
        plt.colorbar(shrink=.5)

    plt.axis('off')
    plt.gca().set_aspect('equal')
    plt.tight_layout()


def imshow_mask(im, mk, color=None, figsize=12):
    '''
    Overlay a binary mask using the given color
    '''
    black = (0, 0, 0)
    if not color:
        color = (.5, 0, 0)

    im_rgb = skimage.color.label2rgb(mk, image=utils.autogain(im), colors=(black, color))
    imshow(im_rgb, figsize)


def show_mask_props(mask, prop_name='area', label_color='red', conn=1, fmt='%s'):
    '''
    Overlay the values of a regionprops property on the mask itself
    '''

    try:
        props = skimage.measure.regionprops(mask)
    except TypeError:
        print('Warning: mask was not labeled')
        mask = (~~mask).astype(int)
        mask = skimage.measure.label(mask > 0, connectivity=conn)
        props = skimage.measure.regionprops(mask)

    # bounding box properties for plt.text
    bbox = dict(facecolor=label_color, alpha=0.5)

    imshow(mask > 0)
    for prop in props:
        text = fmt % getattr(prop, prop_name)
        plt.text(prop.centroid[1], prop.centroid[0], text, bbox=bbox)


def make_rgb(imr=None, img=None, imb=None, im_bg=None, zaxis=0, gamma=None):
    '''
    imr, img, imb : images to show in red, green, and blue, respectively
    im_bg : image to show in grayscale

    '''

    def _make_projection(im):
        if im.ndim == 3:
            im = im.max(axis=zaxis)
        if im.ndim > 3:
            raise ValueError('An image has more than three dimensions')

        im = utils.autogain(im, gamma=gamma)
        return im


    # get the shape and dtype of the provided arrays
    # TODO check for consistency
    for im in (imr, img, imb):
        if im is not None:
            shape = im.shape
            dtype = im.dtype

    # z-project if necessary
    projs = []
    for im in (imr, img, imb):

        if im is None:
            im = np.zeros(shape, dtype=dtype)

        # z-project if necessary and autogain to force uint8
        im = _make_projection(im)

        # prepare to concatenate
        im = im[:, :, None]
        projs.append(im)

    im_rgb = np.concatenate(tuple(projs), axis=2)

    if im_bg is not None:
        im_bg = _make_projection(im_bg)

        im_rgb = im_rgb.astype(float) + im_bg.astype(float)[:, :, None]
        im_rgb[im_rgb > 255] = 255

    return im_rgb.astype('uint8')


def build_tile(
    data, 
    offset=0, 
    shape=10, 
    figsize=12, 
    show_labels=False, 
    label_column=None, 
    label_format=None,
    im_loader=None,
    plot=True
):
    
    filepath_colummn = 'filename'
    if 'filepath' in data.columns:
        filepath_colummn = 'filepath'
    
    pad = 3
    label_pad = 15
    if not isinstance(shape, tuple) or len(shape) == 1:
        shape = (shape, shape)
    
    scale = 4
    image_size = 1024/scale

    counter = 0
    rows = []
    labels = []
    for row_ind in range(shape[0]):
        cols = []
        for col_ind in range(shape[1]):
            ind = offset + counter
            if ind >= data.shape[0]:
                im = np.zeros((image_size, image_size), dtype='uint8')
            else:
                filepath = data.iloc[ind][filepath_colummn]
                if im_loader:
                    im = im_loader(filepath)
                else:
                    im = utils.load(filepath)
                
                im = im[::scale, ::scale]
                if im.dtype != 'uint8':
                    im = utils.autogain(im, percentile=1)

                if label_column is None:
                    label_text = str(ind)
                elif label_column == 'index':
                    label_text = data.iloc[ind].name
                else:
                    label_text = data.iloc[ind][label_column]
                    if label_format:
                        label_text = label_format % label_text
                
                labels.append({
                    'text': label_text,
                    'x': col_ind * image_size + label_pad,
                    'y': row_ind * image_size + 2.5*label_pad,
                })

            im[:pad, :] = 255
            im[:, :pad] = 255
            im[-pad:, :] = 255
            im[:, -pad:] = 255
            cols.append(im)
            counter += 1

        rows.append(np.concatenate(tuple(cols), axis=1))
    tile = np.concatenate(tuple(rows), axis=0)
    
    if not plot:
        return tile

    imshow(tile, figsize=figsize, cmap='gray', colorbar=False)
    bbox = dict(facecolor='white', edgecolor=None, alpha=0.5)
    if show_labels:
        for label in labels:
            plt.text(label['x'], label['y'], label['text'], bbox=bbox, color='black')

    return tile