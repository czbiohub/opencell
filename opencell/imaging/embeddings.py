import io
import os
import sys
import json
import base64
import imageio
import sklearn
import numpy as np
import scipy as sp
import pandas as pd
import scanpy as sc
import anndata as ad
import skimage.morphology
from matplotlib import pyplot as plt


def remove_edge_regions(mask, conn=1):
    '''
    Remove regions in a binary image that touch one or more edges of the image
    '''
    mask_out = mask.copy()
    mask_label = skimage.measure.label(mask, connectivity=conn)
    props = skimage.measure.regionprops(mask_label)
    for prop in props:
        if min(prop.bbox) == 0 or prop.bbox[2] == mask.shape[0] or prop.bbox[3] == mask.shape[1]:
            mask_out[mask_label == prop.label] = False
    return mask_out > 0


class AnnDataManager:

    def __init__(self, adata=None, filepath=None, log_and_scale=False):
        '''
        adata : the anndata object that represents an image embedding
        filepath : the filepath to a cached anndata object (as a .h5ad file)
        '''
        if filepath is not None:
            adata = ad.read_h5ad(filepath)

        # important: reset the index, which gets parsed as a string, not an int
        adata.obs.reset_index(inplace=True)

        # log-transform and scale feature column (for histograms only)
        if log_and_scale:
            sc.pp.log1p(adata)
            sc.pp.scale(adata, max_value=10)

        # PCA (200 PCs is, in practice, enough for both histograms and vectors)
        sc.pp.pca(adata, n_comps=200)
        self.adata = adata


    def run_umap(self, n_neighbors=10, min_dist=0, random_state=42, plot=False):
        '''
        Create a UMAP embedding (this modifies self.adata in-place)
        '''
        sc.pp.neighbors(self.adata, metric='euclidean', n_neighbors=n_neighbors)
        sc.tl.umap(self.adata, min_dist=min_dist, random_state=random_state)

        if plot:
            plt.scatter(*self.adata.obsm['X_umap'].transpose(), alpha=0.3)



class UmapGrid:

    def __init__(self, adata, grid_size):
        '''
        '''
        self.raw_coords = adata.obsm['X_umap'].copy()
        self.target_labels = adata.obs.copy()
        self.grid_size = grid_size


    def load_fov_thumbnails(self, filepath):
        '''
        Load the best-FOV thumbnails from a cache of the /lines payload,
        as a dict of thumbnail images keyed by cell_line_id
        '''
        with open(filepath, 'r') as file:
            thumbnails = json.load(file)

        target_thumbnails = {}
        for cell_line_id in self.target_labels.cell_line_id:
            row = [d for d in thumbnails if d['metadata']['cell_line_id'] == cell_line_id]
            target_thumbnails[cell_line_id] = (
                self.b64decode_image(row[0]['best_fov']['thumbnails']['data']) if row else None
            )
        self.target_thumbnails = target_thumbnails


    def generate_grid_coords(self):
        '''
        Bin the raw coordinates
        '''
        minn = self.raw_coords.min(axis=0)
        maxx = self.raw_coords.max(axis=0)

        bin_size = (maxx - minn)/self.grid_size
        bins_x = np.arange(minn[0], maxx[0], bin_size[0])
        bins_y = np.arange(minn[1], maxx[1], bin_size[1])

        # an array of the indices (or coordinates) of the bins into which each target falls
        self.grid_coords = np.concatenate(
            (
                np.digitize(self.raw_coords[:, 0], bins_x)[:, None],
                np.digitize(self.raw_coords[:, 1], bins_y)[:, None]
            ),
            axis=1
        )

        # list of all grid coords spanned by the grid
        mesh_x, mesh_y = np.meshgrid(
            np.arange(0, self.grid_coords[:, 0].max()), np.arange(0, self.grid_coords[:, 1].max())
        )
        self.all_grid_coords = np.concatenate(
            (mesh_x.flatten()[:, None], mesh_y.flatten()[:, None]), axis=1
        )


    @staticmethod
    def get_target_inds_from_grid_coord(grid_coords, grid_coord):
        '''
        Get the indices of the targets whose umap coordinates
        are in the bin specified by `grid_coord`

        grid_coords : the 2D bin coordinates for each target as an array of shape (num_targets, 2)
        grid_coord : the 2D bin coordinate of the bin
        '''
        return np.argwhere((grid_coords == grid_coord).all(axis=1)).flatten()


    def count_targets_per_grid_coord(self, grid_coords):
        '''
        Count the number of targets that are in each bin or cell of the grid
        '''
        counts = np.zeros((self.grid_size, self.grid_size))
        for grid_coord in self.all_grid_coords:
            counts[tuple(grid_coord)] = len(
                self.get_target_inds_from_grid_coord(grid_coords, grid_coord)
            )
        return counts


    def mask_internal_empty_bins(self, grid_coords, plot=False):
        '''
        Generate a mask in which 'pixels' (grid bins) are True
        if 1) the grid cell has no targets and 2) is not on the edge of the grid
        '''
        counts = self.count_targets_per_grid_coord(grid_coords)

        # a mask of the empty bins that neighbor a non-empty bin
        neighbors = skimage.morphology.dilation(counts > 0, selem=np.ones((3, 3))) ^ (counts > 0)

        # a hackish way to mask the empty bins that are surrounded by non-empty bins
        empty_internal_bins = remove_edge_regions(neighbors > 0)

        if plot:
            plt.figure(figsize=(12, 4))
            plt.imshow(np.concatenate((counts > 0, neighbors > 0, empty_internal_bins > 0), axis=1))

        return empty_internal_bins


    def distribute_extra_targets(self, grid_coords, mask=None):
        '''
        Move 'extra' targets to adjacent empty bins
        mask : optional mask of the empty grid cells to attempt to fill
        '''

        # list of (ind_x, ind_y) pairs for a 3x3 neighborhood
        nx, ny = np.meshgrid([-1, 0, 1], [-1, 0, 1])
        rel_neighbor_grid_coords = np.concatenate(
            (nx.flatten()[:, None], ny.flatten()[:, None]), axis=1
        )

        # drop the the center of the neighborhood
        center = (rel_neighbor_grid_coords == [0, 0]).all(axis=1)
        rel_neighbor_grid_coords = rel_neighbor_grid_coords[~center]

        for grid_coord in self.all_grid_coords:
            target_inds = self.get_target_inds_from_grid_coord(grid_coords, grid_coord)
            if len(target_inds) <= 1:
                continue

            # assign the extra inds to neighboring bins without any inds
            extra_target_inds = list(target_inds[1:])
            for rel_neighbor_grid_coord in rel_neighbor_grid_coords:

                if not len(extra_target_inds):
                    break

                neighbor_grid_coord = grid_coord + rel_neighbor_grid_coord

                # if the neighbor is out of bounds
                if min(neighbor_grid_coord) < 0 or max(neighbor_grid_coord) >= self.grid_size:
                    continue

                # skip the neighbor if it is masked out
                if mask is not None and not mask[tuple(neighbor_grid_coord)]:
                    continue

                neighbor_bin_target_inds = self.get_target_inds_from_grid_coord(
                    grid_coords, neighbor_grid_coord
                )

                # if the neighbor bin has no targets, move one of the extra targets into it
                if not len(neighbor_bin_target_inds):
                    extra_target_ind = extra_target_inds.pop()
                    grid_coords[extra_target_ind, :] = neighbor_grid_coord

        return grid_coords


    def clean_up_grid(self):
        '''
        Attempt to 'clean up' the gridded coordinates
        by filling in some of the empty internal grid bins by moving targets
        from neighboring bins with 'extra' targets (that is, more than one)
        '''
        grid_coords = self.grid_coords.copy()
        internal_empty_bins = self.mask_internal_empty_bins(grid_coords)

        # try to fill the empty internal bins first, then try the perimeter bins
        grid_coords = self.distribute_extra_targets(grid_coords, mask=internal_empty_bins)
        grid_coords = self.distribute_extra_targets(grid_coords, mask=None)

        return grid_coords


    def construct_tile(self, grid_coords, kind='coords', downsample_by=2):
        '''
        Create a tiled array of thumbnails from the grid coordinates
        Note: this is only for offline visualization, not for the opencell frontend

        kind : 'coords' to construct the array of tile coordinates
            'image' to construct the tiled image itself
        downsample_by : integer factor by which to subsample the thumbnail images
            (for constructing the tile itself)
        '''

        # hard-coded thumbnail sizes (for native thumbnail size of 200x200)
        thumb_size = {1: 200, 2: 100}[downsample_by]

        tile_image = np.zeros(
            (thumb_size*self.grid_size, thumb_size*self.grid_size, 3), dtype='uint8'
        )

        tile_coords = []
        for grid_coord in self.all_grid_coords:
            target_inds = self.get_target_inds_from_grid_coord(grid_coords, grid_coord)
            if not len(target_inds):
                continue

            # for now, arbitrarily pick the first target in the bin
            target_ind = target_inds[0]
            cell_line_id = self.target_labels.loc[target_ind].cell_line_id
            tile_coords.append({
                'cell_line_id': cell_line_id,
                'x': grid_coord[0],
                'y': grid_coord[1],
            })

            if kind == 'coords':
                continue

            thumb_image = self.target_thumbnails.get(cell_line_id)
            if thumb_image is None:
                continue

            tile_image[
                grid_coord[0]*thumb_size:(grid_coord[0] + 1)*thumb_size,
                grid_coord[1]*thumb_size:(grid_coord[1] + 1)*thumb_size,
                :
            ] = thumb_image[::downsample_by, ::downsample_by, :]

        if kind == 'coords':
            return tile_coords

        if kind == 'image':
            return tile_image


class TargetThumbnailTile:

    def __init__(self, thumbnail_scale, thumbnail_shape):
        '''
        thumbnail_scale : factor by which to downsample the thumbnails,
            relative to the size of the best-fov thumbnails in the database
        thumbnail_shape : 'square' or 'circle'
        '''
        self.thumbnail_scale = thumbnail_scale
        self.thumbnail_shape = thumbnail_shape


    @staticmethod
    def b64encode_image(image, format):
        with io.BytesIO() as file:
            imageio.imsave(file, image, format=format)
            s = base64.b64encode(file.getvalue()).decode('utf-8')
        return s

    @staticmethod
    def b64decode_image(s, format='jpg'):
        with io.BytesIO(base64.b64decode(bytes(s, encoding='utf-8'))) as file:
            im = imageio.imread(file, format=format)
        return im


    def load_thumbnails_from_cell_line_metadata(self, filepath):
        '''
        Load thumbnails from cached /lines payload
        '''
        with open(filepath, 'r') as file:
            cell_line_metadata = json.load(file)

        thumbnails = {}
        for row in cell_line_metadata:
            cell_line_id = row['metadata']['cell_line_id']
            try:
                thumbnail = row['best_fov']['thumbnails']['data']
            except KeyError:
                thumbnail = None

            if thumbnail is not None:
                thumbnails[cell_line_id] = self.b64decode_image(thumbnail)

        self.thumbnails = thumbnails


    @classmethod
    def load_thumbnails_from_database(self, session):
        '''
        '''
        # get an ROI thumbnail from one of the annotated FOVs for each cell line
        d = pd.read_sql(
            '''
            select tmp.cell_line_id as cell_line_id, thumb.data as thumbnail from (
                select cell_line_id, max(fov.id) as fov_id from microscopy_fov fov
                where fov.id in (select fov_id from microscopy_fov_annotation)
                group by cell_line_id
            ) tmp
            inner join microscopy_fov_roi roi on roi.fov_id = tmp.fov_id
            inner join microscopy_thumbnail thumb on thumb.roi_id = roi.id
            where thumb.channel = 'rgb';
            ''',
            session.get_bind()
        )

        thumbnails = {}
        for _, row in d.iterrows():
            thumbnails[row.cell_line_id] = self.b64decode_image(row.thumbnail)
        self.thumbnails = thumbnails


    def get_tile_filename(self):
        return f'tiled-cell-line-thumbnails--{self.thumbnail_size}px--{self.thumbnail_shape}.jpg'


    def get_circle_mask(self):
        '''
        '''
        radius = int(np.ceil(self.thumbnail_size / 2))
        circle_mask = skimage.morphology.ball(radius)
        return circle_mask[:self.thumbnail_size, :self.thumbnail_size, radius]


    def downsample_thumbnail(self, thumbnail):
        '''
        Downsample the thumbnail by the factor in self.thumbnail_scale
        '''
        if self.thumbnail_scale == 1:
            return thumbnail.copy()

        thumbnail = skimage.transform.downscale_local_mean(
            thumbnail.copy(), factors=(self.thumbnail_scale, self.thumbnail_scale, 1)
        )
        return thumbnail


    def construct_tile(self):

        # get the absolute size of the thumbnails after downsampling
        thumbnail = self.thumbnails[list(self.thumbnails.keys())[0]]
        thumbnail = self.downsample_thumbnail(thumbnail)
        self.thumbnail_size = thumbnail.shape[0]

        # get a mask for making circle-shaped thumbnails
        circle_mask = self.get_circle_mask()

        # the number of rows and column in the tile
        n_rows = 36
        n_cols = int(np.ceil(len(self.thumbnails.keys())/n_rows))
        thumbnail_tile = np.zeros(
            (self.thumbnail_size * n_rows, self.thumbnail_size * n_cols, 3), dtype='uint8'
        )

        thumbnail_tile_positions = []
        for ind, (cell_line_id, thumbnail) in enumerate(self.thumbnails.items()):
            if thumbnail is None:
                continue

            thumbnail = self.downsample_thumbnail(thumbnail)
            if self.thumbnail_shape == 'circle':
                thumbnail = thumbnail * circle_mask[:, :, None]

            row, col = np.unravel_index(ind, (n_rows, n_cols))
            thumbnail_tile[
                row*self.thumbnail_size:(row + 1)*self.thumbnail_size,
                col*self.thumbnail_size:(col + 1)*self.thumbnail_size,
                :
            ] = thumbnail

            thumbnail_tile_positions.append({
                'row': row,
                'col': col,
                'cell_line_id': cell_line_id,
            })

        return thumbnail_tile, thumbnail_tile_positions
