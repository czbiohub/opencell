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



def insert_pulldown_plate(session, row, errors='warn'):
    """ From a pd row, insert a single pulldown plate data """

    # drop any existing data
    plate = (
        session.query(models.MassSpecPulldownPlate)
        .filter(models.MassSpecPulldownPlate.id == row.id)
        .one_or_none()
    )
    if plate:
        utils.delete_and_commit(session, plate)

    plate = models.MassSpecPulldownPlate(
        id=row.id,
        plate_design_link=row.plate_design_link,
        description=row.plate_number_subset
    )
    utils.add_and_commit(session, plate, errors=errors)


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
    '''

    def bulk_insert_hits(self, session, target, target_hits, pulldown_df, errors='warn'):
        """
        convenience method tying together multiple definitions
        for each target, add entire rows to the database by bulk_save_objects
        """
        plate_id, target_name = target.split('_')
        plate_id = ms_utils.format_ms_plate(plate_id)

        # get the pulldown for this plate_id and target_name
        pulldown_meta = pulldown_df.loc[
            (pulldown_df['pulldown_plate_id'] == plate_id)
            & (pulldown_df['target_name'] == target_name)
        ]

        # retrieve the design id and well id
        design_id, well_id = pulldown_meta.design_id.item(), pulldown_meta.well_id.item()

        # get the cellline_id
        pull_cls = MassSpecPolyclonalOperations.from_plate_well(session, design_id, well_id)
        cell_line_id = pull_cls.line.id

        # get the pulldown_id
        pulldown = (
            session.query(models.MassSpecPulldown)
            .filter(models.MassSpecPulldown.cell_line_id == cell_line_id)
            .filter(models.MassSpecPulldown.pulldown_plate_id == plate_id)
            .one()
        )
        pulldown_id = pulldown.id

        # remove existing hits under same pulldown
        self.remove_target_hits(session, pulldown_id, errors=errors)

        # add all Hit instances to a list
        all_hits = []
        for _, row in target_hits.iterrows():
            hit = self.create_hit(row, pulldown_id)
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


    @staticmethod
    def insert_protein_group(session, row, errors='warn'):
        """
        from a pd row, insert a protein group data
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
            utils.delete_and_commit(session, existing_group)

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


    @staticmethod
    def remove_target_hits(session, pulldown_id, errors='warn'):
        '''
        remove duplicate entries
        '''
        duplicate_hits = (
            session.query(models.MassSpecHit)
            .join(models.MassSpecPulldown)
            .filter(models.MassSpecPulldown.id == pulldown_id)
            .all()
        )
        for hit in duplicate_hits:
            session.delete(hit)

        try:
            session.commit()
        except Exception as exception:
            session.rollback()
            if errors == 'raise':
                raise
            if errors == 'warn':
                print('Error in remove_target_hits: %s' % exception)


    @staticmethod
    def create_hit(row, pulldown_id):
        """
        From a pd row, create a MassSpecHit instance
        """
        protein_group_id, _ = ms_utils.create_protein_group_id(row.name)

        hit = models.MassSpecHit(
            protein_group_id=protein_group_id,
            pulldown_id=pulldown_id,
            pval=row.pvals,
            enrichment=row.enrichment,
            is_significant_hit=row.hits,
            is_minor_hit=row.minor_hits,
            is_imputed=row.imputed,
            interaction_stoich=row.interaction_stoi,
            abundance_stoich=row.abundance_stoi
        )

        return hit
