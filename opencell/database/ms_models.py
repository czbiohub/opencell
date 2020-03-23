import re
import enum
import sys
import numpy as np
import pandas as pd

import sqlalchemy as db
import sqlalchemy.ext.declarative
from sqlalchemy.dialects import postgresql

from opencell import constants
from opencell.database import models
from opencell.database import utils


Base = models.Base
terminus_type_enum = models.terminus_type_enum
cell_line_type_enum = models.cell_line_type_enum
well_id_enum = models.well_id_enum


class Pulldown(Base):
    '''
    every bait (cell_line) used in MS analysis
    '''

    __tablename__ = 'pulldown'

    # Columns
    id = db.Column(db.Integer, primary_key=True)
    cell_line_id = db.Column(db.Integer, db.ForeignKey('cell_line.id'))
    pulldown_plate_id = db.Column(db.String,
        db.ForeignKey('pulldown_plate.id'))

    pulldown_well_rep1 = db.Column(db.String)
    pulldown_well_rep2 = db.Column(db.String)
    pulldown_well_rep3 = db.Column(db.String)


    # dataset_id = db.Column(db.String)


    # Relationships
    cell_line = db.orm.relationship('CellLine', back_populates='pulldown')
    hits = db.orm.relationship('Hits', back_populates='pulldown')
    pulldown_plate = db.orm.relationship("PulldownPlate", back_populates='pulldown')



    def target_name(self):
        """convenience method to get target_name for each pulldown"""
        return self.cell_line.get_crispr_design().target_name

    def __repr__(self):
        return "<Bait(id=%s, pulldown_plate=%s, target=%s)>" % \
            (self.id, self.pulldown_plate_id, self.target_name())



class Hits(Base):
    '''
    every identified hits in the base
    '''

    __tablename__ = 'hits'

    # Columns
    id = db.Column(db.Integer, primary_key=True)

    # target string is ProteinIDs (collection of uniprot protein ids)
    protein_group_id = db.Column(db.String, db.ForeignKey('protein_group.id'))
    pulldown_id = db.Column(db.Integer, db.ForeignKey('pulldown.id'))
    pval = db.Column(db.Float)
    enrichment = db.Column(db.Float)
    hit = db.Column(db.Boolean)
    imputed = db.Column(db.Boolean)

    # Relationships
    pulldown = db.orm.relationship('Pulldown', back_populates='hits')
    protein_group = db.orm.relationship('ProteinGroup', back_populates='hits')

    # constraints
    __table_args__ = (
            db.UniqueConstraint(pulldown_id, protein_group_id),
    )

class ProteinGroup(Base):
    '''
    every protein Group identified by msms in experiments
    '''

    __tablename__ = 'protein_group'

    # Columns
    id = db.Column(db.String, primary_key=True)

    # For now, a list of all proteins mapped to the group
    gene_names = db.Column(db.String)

    # Relationships
    hits = db.orm.relationship('Hits', back_populates='protein_group')


class PulldownPlate(Base):
    '''
    every MS plate prepped by the ML Group

    '''
    __tablename__ = "pulldown_plate"

    # Columns
    id = db.Column(db.String, primary_key=True)
    plate_design_link = db.Column(db.String)
    plate_subset = db.Column(db.String)
    cell_prep = db.Column(db.String)
    ms_prep = db.Column(db.String)
    prep_date = db.Column(db.DateTime)
    ship_date = db.Column(db.DateTime)
    quant_date = db.Column(db.DateTime)

    # Relationships
    pulldown = db.orm.relationship("Pulldown", back_populates='pulldown_plate')
