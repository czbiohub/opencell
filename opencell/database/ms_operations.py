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
from opencell.database import models
from opencell.database import ms_utils
from opencell.imaging import processors



def insert_pulldown_plate(session, row, errors='warn'):
    """ From a pd row, insert a single pulldown plate data """
    # drop any existing data
    line = (
        session.query(models.MassSpecPulldownPlate)
        .filter(models.MassSpecPulldownPlate.id == row.id)
        .all()
    )

    if len(line) == 1:
        operations.delete_and_commit(session, line[0])
    plate = models.MassSpecPulldownPlate(
        id=row.id,
        plate_design_link=row.plate_design_link,
        description=row.plate_number_subset
    )
    operations.add_and_commit(session, plate, errors=errors)


class MassSpecPolyclonalOperations(operations.PolyclonalLineOperations):
    '''
    '''

    def insert_pulldown(self, session, row, errors='warn'):
        """ From a pd row, insert a single pulldown data """

        # drop any row that has same pulldown information
        if self.line.mass_spec_pulldowns:
            for pulldown in self.line.mass_spec_pulldowns:
                if pulldown.pulldown_plate_id == row.pulldown_plate_id:
                    operations.delete_and_commit(session, pulldown)

        pulldown = models.MassSpecPulldown(
            cell_line=self.line,
            pulldown_plate_id=row.pulldown_plate_id)
        operations.add_and_commit(session, pulldown, errors=errors)


class MassSpecPulldownOperations:
    '''
    '''

    def bulk_insert_hits(self, session, target, target_hits, errors='warn'):
        """
        convenience method tying together multiple definitions
        for each target, add entire rows to the database by bulk_save_objects
        """
        plate_id, target_name = target.split('_')
        plate_id = ms_utils.format_ms_plate(plate_id)

        # remove existing hits under same target
        self.remove_target_hits(session, plate_id, target_name, errors=errors)

        # get the pulldown_id
        pulldown_id = self.get_pulldown_id(session, plate_id, target_name)

        # add all Hit instances to a list
        all_hits = []
        for i, row in target_hits.iterrows():
            hit = self.create_hit(row, plate_id, target_name, pulldown_id, errors=errors)
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
                print('Error in bulk_save: %s' % exception)

    @staticmethod
    def insert_protein_group(session, row, errors='warn'):
        """
        from a pd row, insert a protein group data
        """

        # get hashed protein group id
        protein_group_id, protein_list = ms_utils.hash_protein_group_id(row.name)

        # remove duplicate entry
        dup_groups = (
            session.query(models.MassSpecProteinGroup)
            .filter(models.MassSpecProteinGroup.id == protein_group_id)
            .all())
        if len(dup_groups) == 1:
            operations.delete_and_commit(session, dup_groups[0])
        if row.gene_names:
            gene_names = row.gene_names.split(';')
        else:
            gene_names = None
        protein_group = models.MassSpecProteinGroup(
            id=protein_group_id,
            gene_names=gene_names,
            protein_names=protein_list
        )
        operations.add_and_commit(session, protein_group, errors=errors)

    @staticmethod
    def remove_target_hits(session, plate_id, target_name, errors='warn'):
        # remove duplicate entries / bulk commit
        dup_hits = session.query(models.MassSpecHit)\
            .join(models.MassSpecPulldown)\
            .filter(models.MassSpecPulldown.pulldown_plate_id == plate_id)\
            .all()

        for hit in dup_hits:
            if hit.pulldown.get_target_name() == target_name:
                session.delete(hit)
        try:
            session.commit()
        except Exception as exception:
            session.rollback()
            if errors == 'raise':
                raise
            if errors == 'warn':
                print('Error in bulk_deletion: %s' % exception)

    @staticmethod
    def get_pulldown_id(session, plate_id, target_name):
        # get pulldown_id
        # filter first for specific pulldown plate
        pulldowns = session.query(models.MassSpecPulldown)\
            .filter(models.MassSpecPulldown.pulldown_plate_id == plate_id)\
            .all()
        for pulldown in pulldowns:
            if pulldown.get_target_name() == target_name:
                return pulldown.id

    @staticmethod
    def create_hit(row, plate_id, target_name, pulldown_id, errors='warn'):
        """
        from a pd row, insert a single hit data
        """
        hashed_protein_id, _ = ms_utils.hash_protein_group_id(row.name)

        hit = models.MassSpecHit(
            protein_group_id=hashed_protein_id,
            pulldown_id=pulldown_id,
            pval=row.pvals,
            enrichment=row.enrichment,
            is_significant_hit=row.hits,
            is_minor_hit=row.minor_hits,
            is_imputed=row.imputed)

        return hit
