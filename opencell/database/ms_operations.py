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
from opencell.imaging import processors


imp.reload(operations)

class PulldownOperations(operations.PolyclonalLineOperations):
    '''
    '''
    @classmethod
    def from_crispr_plate_well(cls, session, design_id, well_id, target_name):
        '''
        Convenience method to retrieve the cell line corresponding to a plate design and a well id,
        *assuming* that there is only one electroporation of one instance of the plate design.
        '''

        lines = (
            session.query(models.CellLine)
            .join(models.ElectroporationLine)
            .join(models.Electroporation)
            .join(models.PlateInstance)
            .join(models.PlateDesign)
            .join(models.CrisprDesign)
            .filter(models.CrisprDesign.plate_design_id == design_id)
            .filter(models.CrisprDesign.well_id == well_id)
            .filter(models.CrisprDesign.target_name == target_name)
            .all()
        )
        pdb.set_trace()
        if len(lines) > 1:
            raise ValueError('More than one line found for well %s of plate %s' % (well_id, design_id))
        if not lines:
            raise ValueError('No line found for well %s of plate %s' % (well_id, design_id))

        return cls(lines[0])


    def insert_pulldown_plate(self, session, row, errors='warn'):
        """ From a pd row, insert a single pulldown plate data """
        # drop any existing data
        line = (
            session.query(ms_models.PulldownPlate)
            .filter(ms_models.PulldownPlate.id == row.id)
            .all()
        )

        if len(line) == 1:
            operations.delete_and_commit(session, line[0])
        plate_data = ms_models.PulldownPlate(
            id=row.id,
            plate_subset=row.plate_number_subset,
            cell_prep=row.cell_prep,
            ms_prep=row.ms_prep,
            prep_date=row.prep_date,
            ship_date=row.ship_date,
            quant_date=row.quant_date
        )
        operations.add_and_commit(session, plate_data, errors=errors)


    def insert_pulldown_row(self, session, row, errors='warn'):
        """ From a pd row, insert a single pulldown data """

        # drop any row that has same pulldown plate/well & replicate
        for instance in self.line.pulldown:
            replicate_check = (instance.pulldown_plate_id
                == row.pulldown_plate_id) &\
                (instance.pulldown_well_rep1
                == row.pulldown_well_rep1) &\
                (instance.pulldown_well_rep2
                == row.pulldown_well_rep2) &\
                    (instance.pulldown_well_rep3
                == row.pulldown_well_rep3)
            if replicate_check:
                operations.delete_and_commit(session, instance)
                break

        pulldown_data = ms_models.Pulldown(
            cell_line=self.line,
            pulldown_plate_id=row.pulldown_plate_id,
            pulldown_well_rep1=row.pulldown_well_rep1,
            pulldown_well_rep2=row.pulldown_well_rep2,
            pulldown_well_rep3=row.pulldown_well_rep3,)
        operations.add_and_commit(session, pulldown_data, errors=errors)

class HitsOperations():
    '''
    '''

    def insert_protein_group(self, session, row, errors='warn'):
        """
        from a pd row, insert a protein group data
        """
        # remove duplicate entry
        dup_group = (session.query(ms_models.ProteinGroup)\
            .filter(ms_models.ProteinGroup.id == row.name)\
            .all())
        if len(dup_group) == 1:
            operations.delete_and_commit(session, dup_group[0])
        pg_data = ms_models.ProteinGroup(
            id=row.name,
            gene_names=row.gene_names
        )
        operations.add_and_commit(session, pg_data, errors=errors)


    def insert_hits(self, session, row, plate_id, target_name, errors='warn'):
        """
        from a pd row, insert a single hit data
        """
        # get plate_id and target name
        plate_id = plate_id
        target_name = target_name

        # remove duplicate entries
        dup_hit = (session.query(ms_models.Hits)\
            .join(ms_models.Pulldown)\
            .filter(ms_models.Hits.protein_group_id == row.name)\
            .filter(ms_models.Pulldown.pulldown_plate_id == plate_id)
            .all())
        if len(dup_hit) == 1:
            operations.delete_and_commit(session, dup_hit[0])


        # get pulldown_id
        # filter first for specific pulldown plate
        pulldowns = session.query(ms_models.Pulldown)\
            .filter(ms_models.Pulldown.pulldown_plate_id == plate_id)
        for instance in pulldowns:
            if instance.target_name() == target_name:
                break
        try:
            pulldown_id = instance.id
            hits_data = ms_models.Hits(
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

        operations.add_and_commit(session, hits_data, errors=errors)
