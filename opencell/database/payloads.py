import os
import re
import enum
import json
import flask
import numpy as np
import pandas as pd
import sqlalchemy as db

from opencell import constants
from opencell.database import models, utils, uniprot_utils
from opencell.imaging.processors import FOVProcessor


def cell_line_payload(cell_line, optional_fields):
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

    if not design.raw_uniprot_metadata:
        print(design.target_name)

    uniprot_metadata = {
        'uniprot_id': design.raw_uniprot_metadata.uniprot_id,
        'gene_names': design.raw_uniprot_metadata.gene_names.split(' '),
        'protein_name': uniprot_utils.prettify_uniprot_protein_name(
            design.raw_uniprot_metadata.protein_names
        ),
        'annotation': uniprot_utils.prettify_uniprot_annotation(
            design.raw_uniprot_metadata.annotation
        ),
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
        'uniprot_metadata': uniprot_metadata,
    }

    # get the thumbnail of the annotated ROI from the 'best' FOV
    if 'best-fov' in optional_fields:
        fov = cell_line.get_best_fov()
        if fov and fov.rois:
            # hack: we assume there is only one ROI (the annotated ROI)
            thumbnail = fov.rois[0].get_thumbnail('rgb')
            payload['best_fov'] = {
                'thumbnails': thumbnail.as_dict() if thumbnail else None
            }
    return payload


def facs_payload(facs_dataset):
    '''
    '''
    return {'histograms': facs_dataset.simplify_histograms()}


def fov_payload(fov, optional_fields):
    '''
    The JSON payload for an FOV (and its ROIs)
    optional_fields : an optional list of ['rois', 'thumbnails']
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

    if 'rois' in optional_fields:
        payload['rois'] = [roi.as_dict() for roi in fov.rois]

    if 'thumbnails' in optional_fields:
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
        select pg.gene_names, hit.* from mass_spec_hit hit
        inner join mass_spec_protein_group pg on pg.id = hit.protein_group_id
        where hit.pulldown_id = %d
        ''' % pulldown.id,
        engine
    )

    hits = hits[[
        'gene_names',
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
