import os
import enum
import json
import logging
import numpy as np
import pandas as pd
import sqlalchemy as db

from opencell.database import models, utils

logger = logging.getLogger(__name__)


def insert_embedding(session, name, grid_size, positions):
    '''
    '''
    logger.info("Inserting an embedding called '%s' with %d positions" % (name, len(positions)))

    embedding = (
        session.query(models.CellLineEmbedding)
        .filter(models.CellLineEmbedding.name == name)
        .filter(models.CellLineEmbedding.grid_size == grid_size)
        .one_or_none()
    )
    if embedding is None:
        embedding = models.CellLineEmbedding(name=name, grid_size=int(grid_size))
    else:
        logger.warning("Overwriting the existing embedding named '%s'" % name)

    embedding.positions = [
        models.CellLineEmbeddingPosition(
            cell_line_id=int(position['cell_line_id']),
            position_x=float(position['x']),
            position_y=float(position['y'])
        ) for position in positions
    ]

    utils.add_and_commit(session, embedding, errors='warn')



def insert_thumbnail_tile(session, filename, thumbnail_positions):
    '''
    '''
    tile = (
        session.query(models.ThumbnailTile)
        .filter(models.ThumbnailTile.filename == filename)
        .one_or_none()
    )
    if tile is None:
        tile = models.ThumbnailTile(filename=filename)
    else:
        logger.warning("Overwriting the existing tile with filename '%s'" % filename)

    tile.positions = [
        models.ThumbnailTilePosition(
            cell_line_id=int(position['cell_line_id']),
            tile_row=int(position['row']),
            tile_column=int(position['col'])
        ) for position in thumbnail_positions
    ]

    utils.add_and_commit(session, tile, errors='warn')
