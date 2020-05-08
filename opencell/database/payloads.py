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


def cell_line_payload(cell_line, include):
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

    # summary stats for FOVs and pulldowns
    counts = {
        'num_fovs': len(cell_line.fovs),
        'num_fovs_annotated': len([fov for fov in cell_line.fovs if fov.annotation]),
        'num_pulldowns': len(cell_line.pulldowns),
    }

    # all of the manual annotation categories
    annotation = {
        'categories': cell_line.annotation.categories if cell_line.annotation else None
    }

    payload = {
        'metadata': metadata,
        'scalars': scalars,
        'counts': counts,
        'annotation': annotation,
    }

    # the 'best'/representative FOV for the cell line
    if 'best-fov' in include:
        fov = cell_line.get_best_fov()
        if fov:
            payload['best_fov'] = fov_payload(fov, include=['thumbnails'])

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


def pulldown_payload(pulldown, engine):
    '''
    The JSON payload for a mass spec pulldown and all of its hits
    For speed, we use a direct query to retrieve and serialize the hits
    '''

    # TODO: which gene_name to select?
    # (note that postgres uses one-based indexing)
    hits = pd.read_sql(
        '''
        select pg.gene_names[1] as gene_name, hit.* from mass_spec_hit hit
        inner join mass_spec_protein_group pg on pg.id = hit.protein_group_id
        where hit.pulldown_id = %d
        ''' % pulldown.id,
        engine
    )

    hits = hits[[
        'gene_name',
        'pval',
        'enrichment',
        'abundance_stoich',
        'interaction_stoich',
        'is_significant_hit',
    ]]

    payload = {
        'metadata': pulldown.as_dict(),
        'hits': json.loads(hits.to_json(orient='records')),
    }
    return payload
