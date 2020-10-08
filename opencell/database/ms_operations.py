import os
import re
import enum
import json
import pdb
import numpy as np
import pandas as pd
import sqlalchemy as db
from contextlib import contextmanager

from opencell import constants
from opencell.database import operations
from opencell.database import models, utils
from opencell.database import ms_utils
from opencell.imaging import processors


def bulk_insert_cluster_heatmap(session, cluster_table, cluster_str, errors='warn'):
    """
    insert every row of cluster table
    """
    # a list of all clusters to add
    all_clusters = []
    for ind, row in cluster_table.iterrows():

        # if there is no subcluster identification, input None
        subcluster_id = None
        if np.isfinite(row.subcluster_id):
            subcluster_id = int(row.subcluster_id)

        # if there is no core_complex identification, input None
        core_complex_id = None
        if np.isfinite(row.core_complex_id):
            core_complex_id = int(row.core_complex_id)

        cluster = models.MassSpecClusterHeatmap(
            cluster_id=int(row.cluster_id),
            subcluster_id = subcluster_id,
            core_complex_id = core_complex_id,
            hit_id=int(row.hit_id),
            row_index=int(row.row_index),
            col_index=int(row.col_index),
            analysis_type = cluster_str
        )
        all_clusters.append(cluster)
     # bulk save
    try:
        session.bulk_save_objects(all_clusters)
        session.commit()
    except Exception as exception:
        session.rollback()
        if errors == 'raise':
            raise
        if errors == 'warn':
            print('Error in bulk_insert_hits: %s' % exception)


def insert_pulldown_plate(session, row, errors='warn'):
    """ From a pd row, insert a row into the pulldown_plate table """

    # drop any existing data
    plate = (
        session.query(models.MassSpecPulldownPlate)
        .filter(models.MassSpecPulldownPlate.id == row.id)
        .one_or_none()
    )
    if plate:
        # utils.delete_and_commit(session, plate)
        return

    plate = models.MassSpecPulldownPlate(
        id=row.id,
        plate_design_link=row.plate_design_link,
        description=row.plate_number_subset
    )
    utils.add_and_commit(session, plate, errors=errors)


def insert_protein_group(session, row, errors='warn'):
    """
    from a pd row, insert a row into the protein group table
    """

    # create the id from the concatenated uniprot_ids
    protein_group_id, uniprot_ids = ms_utils.create_protein_group_id(row.name)

    # remove duplicate entry
    existing_group = (
        session.query(models.MassSpecProteinGroup)
        .filter(models.MassSpecProteinGroup.id == protein_group_id)
        .one_or_none()
    )
    if existing_group:
        return
        # utils.delete_and_commit(session, existing_group)

    if row.gene_names:
        gene_names = row.gene_names.split(';')
    else:
        gene_names = None

    protein_group = models.MassSpecProteinGroup(
        id=protein_group_id,
        gene_names=gene_names,
        uniprot_ids=uniprot_ids
    )
    utils.add_and_commit(session, protein_group, errors=errors)


class MassSpecPolyclonalOperations(operations.PolyclonalLineOperations):
    '''
    '''
    def insert_pulldown(self, session, row, errors='warn'):
        """ From a pd row, insert a single pulldown data """

        # drop any row that has same pulldown information
        if self.line.pulldowns:
            for pulldown in self.line.pulldowns:
                if pulldown.pulldown_plate_id == row.pulldown_plate_id:
                    utils.delete_and_commit(session, pulldown)

        pulldown = models.MassSpecPulldown(
            cell_line=self.line,
            pulldown_plate_id=row.pulldown_plate_id
        )
        utils.add_and_commit(session, pulldown, errors=errors)


class MassSpecPulldownOperations:
    '''
    Database operations related to a single pulldown
    '''

    def __init__(self, pulldown):
        self.pulldown = pulldown


    @classmethod
    def from_ids(cls, session, plate_design_id, well_id, sort_count, pulldown_plate_id):
        '''
        Get a pulldown from a combination of
        plate_design_id, well_id, and pulldown_plate_id, and sort_count
        '''

        # get the cell_line_id
        pull_cls = MassSpecPolyclonalOperations.from_plate_well(
            session, plate_design_id, well_id, sort_count
        )

        pulldown = (
            session.query(models.MassSpecPulldown)
            .filter(models.MassSpecPulldown.cell_line_id == pull_cls.line.id)
            .filter(models.MassSpecPulldown.pulldown_plate_id == pulldown_plate_id)
            .one()
        )
        return cls(pulldown)


    @classmethod
    def from_target(cls, session, target, pulldown_df):
        '''
        Get a pulldown from a target name, given a pulldown dataframe and a sort_count
        '''
        pulldown_plate_id, target_name = target.split('_', 1)
        pulldown_plate_id = ms_utils.format_ms_plate(pulldown_plate_id)

        # get the pulldown for this plate_id and target_name
        pulldown_row = pulldown_df.loc[
            (pulldown_df['pulldown_plate_id'] == pulldown_plate_id) &
            (pulldown_df['target_name'] == target_name)
        ]
        try:
            plate_design_id, well_id, sort_count = (
                pulldown_row.design_id.item(), 
                pulldown_row.well_id.item(), 
                pulldown_row.sort_count.item()
            )
        except Exception:
            print(target)
            return None
        return cls.from_ids(session, plate_design_id, well_id, sort_count, pulldown_plate_id)

    def update_to_resorted_line(self, session, plate_design_id, well_id, new_sort_count):
        """
        pulldown data from old sorts of a cell line should be migrated to the
        most recently sorted line. This method updates the cell_line_id of the
        pulldown to the pre-queried cell line
        """
        # get the cell_line_id
        pull_cls = MassSpecPolyclonalOperations.from_plate_well(
            session, plate_design_id, well_id, new_sort_count
        )
        # new cell_line id
        new_cell_line_id = pull_cls.line.id

        self.cell_line_id = new_cell_line_id

        session.commit()

    def bulk_insert_hits(self, session, target_hits, errors='warn'):
        """
        convenience method tying together multiple definitions
        for each target, add entire rows to the database by bulk_save_objects
        """

        # remove existing hits under same pulldown
        self.remove_all_hits(session, errors=errors)

        # add all Hit instances to a list
        all_hits = []
        for _, row in target_hits.iterrows():
            hit = self.create_hit(row)
            all_hits.append(hit)

        # bulk save
        try:
            session.bulk_save_objects(all_hits)
            session.commit()
        except Exception as exception:
            session.rollback()
            if errors == 'raise':
                raise
            if errors == 'warn':
                print('Error in bulk_insert_hits: %s' % exception)


    def insert_fdrs(self, session, row):
        """
        Insert Dynamic FDR values
        """

        self.pulldown.fdr_1_offset = row.fdr1[1]
        self.pulldown.fdr_1_curvature = row.fdr1[0]

        self.pulldown.fdr_5_offset = row.fdr5[1]
        self.pulldown.fdr_5_curvature = row.fdr5[0]

        session.add(self.pulldown)
        session.commit()


    def manually_flag_pulldown(self, session, errors='warn'):
        '''
        Because some crispr designs have multiple pulldowns,
        this method manually flags self.pulldown to indicate
        that it should be the one returned by the /pulldowns API endpoint
        '''

        # reset the manual flags for all pulldowns from the pulldown's cell line
        for pulldown in self.pulldown.cell_line.pulldowns:
            pulldown.manual_display_flag = False
            session.add(pulldown)
            session.commit()

        # flag the current pulldown
        self.pulldown.manual_display_flag = True
        session.add(self.pulldown)
        session.commit()


    def remove_all_hits(self, session, errors='warn'):
        '''
        Remove all of the pulldown's hits
        '''
        for hit in self.pulldown.hits:
            session.delete(hit)

        try:
            session.commit()
        except Exception as exception:
            session.rollback()
            if errors == 'raise':
                raise
            if errors == 'warn':
                print('Error in remove_target_hits: %s' % exception)


    def create_hit(self, row):
        """
        From a pd row, create a MassSpecHit instance
        """
        protein_group_id, _ = ms_utils.create_protein_group_id(row.name)

        hit = models.MassSpecHit(
            protein_group_id=protein_group_id,
            pulldown_id=self.pulldown.id,
            pval=row.pvals,
            enrichment=row.enrichment,
            is_significant_hit=row.hits,
            is_minor_hit=row.minor_hits,
            interaction_stoich=row.interaction_stoi,
            abundance_stoich=row.abundance_stoi
        )
        return hit
