import os
import re
import enum
import json
import numpy as np
import pandas as pd
import sqlalchemy as db

from opencell import constants
from opencell.database import models, utils
from opencell.imaging.processors import FOVProcessor


def construct_payload(cell_line, kind=None):
    '''
    Construct the JSON payload returned by the lines/ endpoint of the API

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
    payload = {'metadata': metadata}

    if kind in ['all', 'scalars']:
        payload['scalars'] = construct_scalars_payload(cell_line)
        payload['annotations'] = cell_line.annotation.categories if cell_line.annotation else None

    if kind in ['all', 'facs'] and cell_line.facs_dataset:
        payload['facs_histograms'] = cell_line.facs_dataset.simplify_histograms()

    if kind in ['all', 'rois', 'thumbnails']:
        payload['fovs'] = construct_fov_payload(cell_line, kind=kind)

    return payload


def construct_scalars_payload(cell_line):
    '''
    Aggregate various scalar properties/features/results
    '''
    scalars = {}

    # the sequencing percentages
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
    return scalars


def construct_fov_payload(cell_line, kind=None):
    '''
    JSON payload describing the FOVs and ROIs
    '''
    payload = []
    for fov in cell_line.fovs:
        fov_payload = {}

        # basic metadata
        fov_metadata = {
            'id': fov.id,
            'score': fov.get_score(),
            'pml_id': fov.dataset.pml_id,
            'src_filename': fov.raw_filename,
            'z_step_size': FOVProcessor.z_step_size(fov.dataset.pml_id),
        }

        fov_payload['annotation'] = fov.annotation.as_dict() if fov.annotation else None

        # append the 488 exposure settings
        metadata = fov.get_result('raw-tiff-metadata')
        if metadata:
            fov_metadata['laser_power_488'] = metadata.data.get('laser_power_488_488')
            fov_metadata['exposure_time_488'] = metadata.data.get('exposure_time_488')
            fov_metadata['max_intensity_488'] = metadata.data.get('max_intensity_488')

        # the position of the cell layer center (relative to the bottom of the stack)
        metadata = fov.get_result('clean-tiff-metadata')
        if metadata and metadata.data.get('cell_layer_center') is not None:
            fov_metadata['cell_layer_center'] = (
                metadata.data.get('cell_layer_center') * fov_metadata['z_step_size']
            )

        if kind in ['all', 'rois']:
            fov_payload['rois'] = [roi.as_dict() for roi in fov.rois]

        if kind in ['all', 'thumbnails']:
            thumbnail = fov.get_thumbnail('rgb')
            fov_payload['thumbnails'] = thumbnail.as_dict() if thumbnail else None

        fov_payload['metadata'] = fov_metadata
        payload.append(fov_payload)

    # sort FOVs by score (unscored FOVs last)
    payload = sorted(payload, key=lambda row: row['metadata'].get('score') or -2)[::-1]
    return payload
