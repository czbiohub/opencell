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


def cell_line_payload(cell_line, included_fields):
    '''
    The JSON payload returned by the /lines endpoint of the API
    Note that, awkwardly, the RNAseq data is a column in the crispr_design table
    '''
    design = cell_line.crispr_design

    # metadata object included in every playload
    metadata = {
        'cell_line_id': cell_line.id,
        'sort_count': cell_line.sort_count,
        'well_id': design.well_id,
        'plate_id': design.plate_design_id,
        'target_name': design.target_name,
        'target_family': design.target_family,
        'target_terminus': design.target_terminus.value[0],
        'transcript_id': design.transcript_id,
        'hek_tpm': design.hek_tpm,
    }

    if not design.uniprot_metadata:
        print(design.target_name)

    uniprot_metadata = {
        'uniprot_id': design.uniprot_metadata.uniprot_id,
        'gene_names': design.uniprot_metadata.gene_names.split(' '),
        'protein_name': uniprot_utils.prettify_uniprot_protein_name(
            design.uniprot_metadata.protein_names
        ),
        'annotation': uniprot_utils.prettify_uniprot_annotation(
            design.uniprot_metadata.annotation
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

    # placeholder for FOV counts
    counts = {
        'num_fovs': None,
        'num_fovs_annotated': None,
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
    if 'best-fov' in included_fields:
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


def fov_payload(fov, include_rois=False, include_thumbnails=False):
    '''
    The JSON payload for an FOV (and its ROIs)
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

    # assume there's only one annotated ROI per FOV, and always include the ROI thumbnail
    if include_rois and fov.rois:
        roi = fov.rois[0]
        roi_payload = roi.as_dict()
        roi_payload['thumbnail'] = roi.get_thumbnail('rgb').as_dict()
        payload['rois'] = [roi_payload]

    if include_thumbnails:
        thumbnail = fov.get_thumbnail('rgb')
        payload['thumbnails'] = thumbnail.as_dict() if thumbnail else None

    return payload


def pulldown_hits_payload(pulldown, significant_hits, nonsignificant_hits):
    '''
    The JSON payload for a mass spec pulldown and all of its hits

    pulldown : a models.MassSpecPulldown instance
    significant_hits : a list of models.MassSpecHit instances corresponding to
        the pulldown's significant hits
    nonsignificant_hits : a list of tuples of (pval, enrichment)
        for all of the pulldown's non-significant hits (usually thousands)
    '''

    hit_columns = [
        'pval',
        'enrichment',
        'interaction_stoich',
        'abundance_stoich'
    ]

    significant_hit_payloads = []
    for hit in significant_hits:

        significant_hit_payload = {
            column: getattr(hit, column) for column in hit_columns
        }

        # add the protein group metadata
        significant_hit_payload.update(protein_group_payload(hit.protein_group))

        # whether this hit is the 'bait' - that is, corresponds to the target itself
        design_ids = [design.id for design in hit.protein_group.crispr_designs]
        significant_hit_payload['is_bait'] = pulldown.cell_line.crispr_design.id in design_ids

        significant_hit_payloads.append(significant_hit_payload)

    # hackish way to coerce NaNs and Infs to None
    significant_hit_payloads = json.loads(
        pd.DataFrame(data=significant_hit_payloads).to_json(orient='records')
    )

    # compress the nonsignificant hits by dropping digits
    nonsignificant_hit_payloads = [
        [float('%0.3f' % pval), float('%0.3f' % enrichment)]
        for pval, enrichment in nonsignificant_hits
    ]

    payload = {
        'metadata': pulldown.as_dict(),
        'significant_hits': significant_hit_payloads,
        'nonsignificant_hits': nonsignificant_hit_payloads
    }
    return payload


def protein_group_payload(protein_group):
    '''
    '''
    payload = {}

    # gene names from the reference uniprot metadata
    names = []
    if not protein_group.uniprot_metadata:
        names = ['Unknown']
    for metadata in protein_group.uniprot_metadata:
        if metadata.gene_names != 'NaN':
            name = metadata.gene_names.split(' ')[0]
        else:
            name = metadata.uniprot_id
        names.append(name)
    payload['uniprot_gene_names'] = names

    # target names of the crispr designs that are mapped to this protein group
    payload['opencell_target_names'] = [
        design.target_name for design in protein_group.crispr_designs
    ]
    return payload
