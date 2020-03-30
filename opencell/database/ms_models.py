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


class MassSpecPulldown(Base):
    '''
    every bait (cell_line) used in MS analysis
    '''

    __tablename__ = 'ms_pulldown'

    # Columns
    id = db.Column(db.Integer, primary_key=True)
    # polyclonal cell line from OpenCell
    cell_line_id = db.Column(db.Integer, db.ForeignKey('cell_line.id'))

    # MS pulldown plates prepped by the ML group, ID takes format of CZBMPI_###
    ms_pulldown_plate_id = db.Column(db.String,
        db.ForeignKey('ms_pulldown_plate.id'))


    # Relationships
    cell_line = db.orm.relationship('CellLine', back_populates='ms_pulldown')
    ms_hits = db.orm.relationship('MassSpecHits', back_populates='ms_pulldown')
    ms_pulldown_plate = db.orm.relationship("MassSpecPulldownPlate",
        back_populates='ms_pulldown')



    def target_name(self):
        """convenience method to get target_name for each pulldown"""
        return self.cell_line.get_crispr_design().target_name

    def __repr__(self):
        return "<Bait(id=%s, pulldown_plate=%s, target=%s)>" % \
            (self.id, self.pulldown_plate_id, self.target_name())



class MassSpecHits(Base):
    '''
    every identified hits in the base
    '''

    __tablename__ = 'ms_hits'

    # Columns
    id = db.Column(db.Integer, primary_key=True)

    # hased string of sorted Uniprot peptide IDs that compose the protein group
    ms_protein_group_id = db.Column(db.String, db.ForeignKey('ms_protein_group.id'))

    # foreign key of each pulldown target from pulldown table
    ms_pulldown_id = db.Column(db.Integer, db.ForeignKey('ms_pulldown.id'))

    # p value of the specific prey's MS intensity
    pval = db.Column(db.Float)

    # enrichment of the prey's MS intensity
    enrichment = db.Column(db.Float)

    # boolean specifying whether the hit is significant based on FDR threshold
    is_significant_hit = db.Column(db.Boolean)

    # boolean specifying whether the hit is composed only of imputed values
    is_imputed = db.Column(db.Boolean)

    # Relationships
    ms_pulldown = db.orm.relationship('MassSpecPulldown', back_populates='ms_hits')
    ms_protein_group = db.orm.relationship('MassSpecProteinGroup', back_populates='ms_hits')

    # constraints
    __table_args__ = (
            db.UniqueConstraint(ms_pulldown_id, ms_protein_group_id),
    )

class MassSpecProteinGroup(Base):
    '''
    every protein Group identified by msms in experiments
    '''

    __tablename__ = 'ms_protein_group'

    # id is a hash of unique set of peptide Uniprot ids that compose the protein group
    id = db.Column(db.String, primary_key=True)

    # a list of all proteins mapped to the protein group
    gene_names = db.Column(db.ARRAY(db.String))

    # Relationships
    ms_hits = db.orm.relationship('MassSpecHits', back_populates='ms_protein_group')


class MassSpecPulldownPlate(Base):
    '''
    every MS plate prepped by the ML Group

    '''
    __tablename__ = "ms_pulldown_plate"

    # Columns
    id = db.Column(db.String, primary_key=True)

    # link to the google sheet design of the plate mapping out pulldown
    # target locations by well
    plate_design_link = db.Column(db.String)

    # Description of the pulldown (whether it is a repeat or subset, etc)
    plate_subset = db.Column(db.String)

    # Relationships
    ms_pulldown = db.orm.relationship("MassSpecPulldown",
        back_populates='ms_pulldown_plate')
