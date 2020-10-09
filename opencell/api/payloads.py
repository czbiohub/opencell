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


def generate_cell_line_payload(cell_line, included_fields, fov_count=None):
    '''
    The JSON payload returned by the /lines endpoint of the API
    Note that, awkwardly, the RNAseq data is a column in the crispr_design table

    included_fields : a list of optional fields to include
    fov_count : optional pandas series of FOV counts for the cell line
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
        'ensg_id': design.uniprot_metadata.ensg_id,
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

    # The FOV counts (`fov_count` is a pd.Series)
    counts = fov_count.to_dict() if fov_count is not None else {}

    # all of the manual annotation categories
    categories = cell_line.annotation.categories if cell_line.annotation else []
    annotation = {
        'categories': categories or None,
        'has_graded_annotations': bool(np.any([
            re.match('.*_[1,2,3]$', cat) is not None for cat in categories
        ]))
    }

    # the id of the 'best' pulldown
    pulldown = cell_line.get_best_pulldown()
    pulldown_id = pulldown.id if pulldown else None

    payload = {
        'metadata': metadata,
        'scalars': scalars,
        'counts': counts,
        'annotation': annotation,
        'uniprot_metadata': uniprot_metadata,
        'best_pulldown': {'id': pulldown_id}
    }

    # get the thumbnail of the annotated ROI from the 'best' FOV
    if 'best-fov' in included_fields:
        fov = cell_line.get_best_fov()
        if fov and fov.rois:
            # hack: assume there is only one ROI (the annotated ROI)
            thumbnail = fov.rois[0].get_thumbnail('rgb')
            payload['best_fov'] = {
                'thumbnails': thumbnail.as_dict() if thumbnail else None
            }
    return payload


def generate_facs_payload(facs_dataset):
    '''
    '''
    return {'histograms': facs_dataset.simplify_histograms()}


def generate_fov_payload(fov, include_rois=False, include_thumbnails=False):
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

    fov_payload = {
        'metadata': metadata,
        'annotation': fov.annotation.as_dict() if fov.annotation else None
    }

    # assume there's only one annotated ROI per FOV, and always include the ROI thumbnail
    if include_rois and fov.rois:
        roi = fov.rois[0]
        roi_payload = roi.as_dict()
        roi_payload['thumbnail'] = roi.get_thumbnail('rgb').as_dict()
        fov_payload['rois'] = [roi_payload]

    if include_thumbnails:
        thumbnail = fov.get_thumbnail('rgb')
        fov_payload['thumbnails'] = thumbnail.as_dict() if thumbnail else None

    return fov_payload


def generate_pulldown_hits_payload(pulldown, significant_hits, nonsignificant_hits):
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

        significant_hit_payload.update(
            generate_protein_group_payload(
                hit.protein_group, pulldown.cell_line.crispr_design_id
            )
        )
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

    pulldown_hits_payload = {
        'metadata': pulldown.as_dict(),
        'significant_hits': significant_hit_payloads,
        'nonsignificant_hits': nonsignificant_hit_payloads
    }
    return pulldown_hits_payload


def generate_protein_group_payload(protein_group, pulldown_crispr_design_id=None):
    '''
    '''

    # the 'primary' gene name for each uniprot_id in the protein group
    gene_names = ['Unknown']
    if protein_group.uniprot_metadata:
        gene_names = list(set([d.get_primary_gene_name() for d in protein_group.uniprot_metadata]))

    # the target names of the crispr designs that are associated with this protein group
    # (these are not always unique, because there are multiple designs for some targets)
    target_names = list(set([design.target_name for design in protein_group.crispr_designs]))

    payload = {
        'uniprot_gene_names': gene_names,
        'opencell_target_names': target_names,
        'is_bait': False,
    }

    # use the crispr_design_id of the pulldown to determine
    # whether this protein group corresponds to the pulldown's bait
    if pulldown_crispr_design_id is not None:
        design_ids = [design.id for design in protein_group.crispr_designs]
        payload['is_bait'] = pulldown_crispr_design_id in design_ids

    return payload
