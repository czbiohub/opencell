import os
import re
import enum
import json
import flask
import numpy as np
import pandas as pd
import sqlalchemy as db

from opencell import constants
from opencell.database import models, utils
from opencell.imaging.processors import FOVProcessor


def cell_line_payload(cell_line):
    '''
    The JSON payload returned by the /lines endpoint of the API
    Note that, awkwardly, the RNAseq data is a column in the crispr_design table
    '''
    design = cell_line.crispr_design

    # metadata object included in every playload
    metadata = {
        'cell_line_id': cell_line.id,
        'well_id': design.well_id,
        'plate_id': design.plate_design_id,
        'target_name': design.target_name,
        'target_family': design.target_family,
        'target_terminus': design.target_terminus.value[0],
        'transcript_id': design.transcript_id,
        'hek_tpm': design.hek_tpm,
    }

    # the sequencing percentages
    scalars = {}
    if cell_line.sequencing_dataset:
        scalars.update({
            'hdr_all': cell_line.sequencing_dataset.scalars.get('hdr_all'),
            'hdr_modified': cell_line.sequencing_dataset.scalars.get('hdr_modified')
        })

    # the FACS area and relative median intensity
    if cell_line.facs_dataset:
        scalars.update({
            'facs_area': cell_line.facs_dataset.scalars.get('area'),
            'facs_intensity': cell_line.facs_dataset.scalars.get('rel_median_log')
        })

    payload = {
        'metadata': metadata,
        'scalars': scalars,
        'annotations': cell_line.annotation.categories if cell_line.annotation else None
    }
    return payload


def facs_payload(facs_dataset):
    '''
    '''
    return {'histograms': facs_dataset.simplify_histograms()}


def fov_payload(fov, include):
    '''
    The JSON payload for an FOV (and its ROIs)
    include : an optional list of ['rois', 'thumbnails']
    '''

    # basic metadata
    metadata = {
        'id': fov.id,
        'score': fov.get_score(),
        'pml_id': fov.dataset.pml_id,
        'src_filename': fov.raw_filename,
        'z_step_size': FOVProcessor.z_step_size(fov.dataset.pml_id),
    }

    # the 488 exposure settings
    tiff_metadata = fov.get_result('raw-tiff-metadata')
    if tiff_metadata:
        metadata['laser_power_488'] = tiff_metadata.data.get('laser_power_488_488')
        metadata['exposure_time_488'] = tiff_metadata.data.get('exposure_time_488')
        metadata['max_intensity_488'] = tiff_metadata.data.get('max_intensity_488')

    # the position of the cell layer center, relative to the bottom of the stack
    tiff_metadata = fov.get_result('clean-tiff-metadata')
    if tiff_metadata and tiff_metadata.data.get('cell_layer_center') is not None:
        metadata['cell_layer_center'] = (
            tiff_metadata.data.get('cell_layer_center')*metadata['z_step_size']
        )

    payload = {
        'metadata': metadata,
        'annotation': fov.annotation.as_dict() if fov.annotation else None
    }

    if 'rois' in include:
        payload['rois'] = [roi.as_dict() for roi in fov.rois]

    if 'thumbnails' in include:
        thumbnail = fov.get_thumbnail('rgb')
        payload['thumbnails'] = thumbnail.as_dict() if thumbnail else None

    return payload


def pulldown_payload(pulldown):
    '''
    The JSON payload for a mass spec pulldown and all of its hits
    '''
    payload = {
        'metadata': pulldown.as_dict(),
        'hits': [hit_payload(hit) for hit in pulldown.hits]
    }
    return payload


def hit_payload(hit):
    '''
    JSON payload for a single mass spec hit
    '''
    # the columns from the MassSpecHit table to include directly in the payload
    columns = [
        'pval',
        'enrichment',
        'is_significant_hit',
        'interaction_stoich',
        'abundance_stoich',
    ]

    payload = {}
    for column in columns:
        val = getattr(hit, column)
        # check for infs, which flask.jsonify serializes to 'Infinity',
        # but which cannot be parsed by d3.json in the frontend
        if val is not None:
            if np.isinf(val) or np.isnan(val):
                val = None
        payload[column] = val

    # retrieve the gene_name from the hit's protein group
    payload['gene_name'] = hit.protein_group.gene_names[0] if hit.protein_group else None
    return payload
