
import os
import click
import json
import logging

import pandas as pd
import sqlalchemy as sa
import sqlalchemy.orm
import sqlalchemy.ext.declarative
from contextlib import contextmanager

from opencell.api import settings
from opencell.database import models, utils, embedding_operations
from opencell.imaging.embeddings import UmapGrid, AnnDataManager, TargetThumbnailTile

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s %(levelname)s in %(name)s: %(message)s"
)
logger = logging.getLogger('opencell.cli.embedding_cli')


@contextmanager
def scoped_session(engine):
    session = sa.orm.sessionmaker(bind=engine)()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@click.group()
@click.option('--mode', default='dev')
@click.option('--credentials', type=click.Path(exists=True))
@click.pass_context
def cli(ctx, mode, credentials):
    ctx.ensure_object(dict)
    config = settings.get_config(mode)
    url = utils.url_from_credentials(credentials or config.DB_CREDENTIALS_FILEPATH)
    engine = sa.create_engine(url)
    ctx.obj['ENGINE'] = engine


@cli.command('create-image-umap')
@click.option('--adata-filepath', required=True, type=click.Path(exists=True))
@click.option('--adata-description', required=True)
@click.option('--grid-size', required=False, type=int)
@click.pass_context
def create_image_umap(ctx, adata_filepath, adata_description, grid_size):
    '''
    '''
    adm = AnnDataManager(filepath=adata_filepath, log_and_scale=False)

    # if we are binning the UMAP coordinates into a grid,
    # first generate a non-clumpy UMAP, then bin its coordinates
    if grid_size:
        logger.info('Generating a grid-able UMAP embedding')
        n_neighbors, min_dist = 30, 0.3
        adm.run_umap(n_neighbors=n_neighbors, min_dist=min_dist)

        logger.info('Binning the UMAP coordinates on a %dx%d grid' % (grid_size, grid_size))
        grid = UmapGrid(adata=adm.adata, grid_size=grid_size)
        grid.generate_grid_coords()
        grid_coords_cleaned = grid.clean_up_grid()
        target_coords = grid.construct_tile(grid_coords_cleaned, kind='coords')

    # if we are not using a grid, then generate a 'normal' clumpy UMAP
    # and manually construct the target_coords array from the 'raw' UMAP coords
    else:
        logger.info('Generating a normal UMAP embedding')
        n_neighbors, min_dist = 10, 0.0
        adm.run_umap(n_neighbors=n_neighbors, min_dist=min_dist)

        raw_umap_coords = adm.adata.obsm['X_umap']
        target_coords = []
        for ind, row in adm.adata.obs.iterrows():
            target_coords.append({
                'cell_line_id': row.cell_line_id,
                'x': raw_umap_coords[ind, 0],
                'y': raw_umap_coords[ind, 1],
            })

        # use a grid_size of 0 to represent un-gridded coordinates
        grid_size = 0

    # append the umap parameters to the embedding name
    name = '%s--umap--n_neighbors=%d--min_dist=%0.1f' % (adata_description, n_neighbors, min_dist)

    with scoped_session(ctx.obj['ENGINE']) as session:
        embedding_operations.insert_embedding(
            session, name=name, grid_size=grid_size, positions=target_coords
        )


@cli.command('create-thumbnail-tile')
@click.option('--thumbnail-scale', type=int, required=True)
@click.pass_context
def create_thumbnail_tile(ctx, thumbnail_scale):

    tile = TargetThumbnailTile(thumbnail_scale=thumbnail_scale, thumbnail_shape=None)

    with scoped_session(ctx.obj['ENGINE']) as session:
        tile.load_thumbnails_from_database(session)

        logger.info('Creating tile of square thumbnails')
        tile.thumbnail_shape = 'square'
        tile_image, thumbnail_positions = tile.construct_tile()
        embedding_operations.insert_thumbnail_tile(
            session,
            filename=tile.get_tile_filename(),
            thumbnail_positions=thumbnail_positions
        )

        logger.info('Creating tile of circular thumbnails')
        tile.thumbnail_shape = 'circle'
        tile_image, thumbnail_positions = tile.construct_tile()
        embedding_operations.insert_thumbnail_tile(
            session,
            filename=tile.get_tile_filename(),
            thumbnail_positions=thumbnail_positions
        )


if __name__ == '__main__':
    cli()
