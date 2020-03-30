import os
import re
import enum
import json
import pdb
import imp
import numpy as np
import pandas as pd
import sqlalchemy as db
from contextlib import contextmanager

from opencell import constants
from opencell.database import operations
from opencell.database import models
from opencell.database import ms_models
from opencell.database import ms_utils
from opencell.imaging import processors


imp.reload(operations)

class MassSpecPolyclonalOperations(operations.PolyclonalLineOperations):
    '''
    '''

    def insert_pulldown_row(self, session, row, errors='warn'):
        """ From a pd row, insert a single pulldown data """

        # drop any row that has same pulldown information
        if self.line.pulldown:
            operations.delete_and_commit(session, self.line.pulldown)

        pulldown_data = ms_models.MassSpecPulldown(
            cell_line=self.line,
            pulldown_plate_id=row.pulldown_plate_id)
        operations.add_and_commit(session, pulldown_data, errors=errors)

    @staticmethod
    def insert_pulldown_plate(session, row, errors='warn'):
        """ From a pd row, insert a single pulldown plate data """
        # drop any existing data
        line = (
            session.query(ms_models.MassSpecPulldownPlate)
            .filter(ms_models.MassSpecPulldownPlate.id == row.id)
            .all()
        )

        if len(line) == 1:
            operations.delete_and_commit(session, line[0])
        plate_data = ms_models.MassSpecPulldownPlate(
            id=row.id,
            plate_subset=row.plate_number_subset

        )
        operations.add_and_commit(session, plate_data, errors=errors)


class MassSpecPulldownOperations():
    '''
    '''

    def bulk_insert_hits(self, session, target, target_hits, errors='warn'):
        """
        convenience method tying together multiple definitions
        for each target, add entire rows to the database by bulk_save_objects
        """
        split = target.split('_')
        plate_id, target_name = split[0], split[1]
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
        # remove duplicate entry
        dup_group = (session.query(ms_models.MassSpecProteinGroup)\
            .filter(ms_models.MassSpecProteinGroup.id == row.name)\
            .all())
        if len(dup_group) == 1:
            operations.delete_and_commit(session, dup_group[0])
        pg_data = ms_models.MassSpecProteinGroup(
            id=row.name,
            gene_names=row.gene_names.split(';')
        )
        operations.add_and_commit(session, pg_data, errors=errors)

    @staticmethod
    def remove_target_hits(session, plate_id, target_name, errors='warn'):
        # remove duplicate entries / bulk commit
        dup_hits = session.query(ms_models.MassSpecHits)\
            .join(ms_models.MassSpecPulldown)\
            .filter(ms_models.MassSpecPulldown.pulldown_plate_id == plate_id)\
            .all()

        for instance in dup_hits:
            if instance.pulldown.target_name() == target_name:
                session.delete(instance)
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
        pulldowns = session.query(ms_models.MassSpecPulldown)\
            .filter(ms_models.MassSpecPulldown.pulldown_plate_id == plate_id)\
            .all()
        for instance in pulldowns:
            if instance.target_name() == target_name:
                break
        return instance.id

    @staticmethod
    def create_hit(row, plate_id, target_name, pulldown_id, errors='warn'):
        """
        from a pd row, insert a single hit data
        """

        try:
            hits_data = ms_models.MassSpecHits(
                protein_group_id=row.name,
                pulldown_id=pulldown_id,
                pval=row.pvals,
                enrichment=row.enrichment,
                hit=row.hits,
                imputed=row.imputed)
        except Exception:
            if errors == 'raise':
                raise
            if errors == 'warn':
                print("Pulldown id not found %s, %s" % plate_id, target_name)

        return hits_data
