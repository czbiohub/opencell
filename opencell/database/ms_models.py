import re
import enum
import numpy as np
import pandas as pd
import sqlalchemy as db
import sys
# import sqlalchemy.org
import sqlalchemy.ext.declarative
from sqlalchemy.dialects import postgresql
from opencell.database import models
from opencell import constants
from opencell.database import utils

# constraint naming conventions
# see https://alembic.sqlalchemy.org/en/latest/naming.html
metadata = db.MetaData(naming_convention={
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
})

Base = db.ext.declarative.declarative_base(cls=models.Base, metadata=metadata)


# enum types
class TerminusTypeEnum(enum.Enum):
    N_TERMINUS = 'N_TERMINUS'
    C_TERMINUS = 'C_TERMINUS'
    INTERNAL = 'INTERNAL'


class CellLineTypeEnum(enum.Enum):
    PROGENITOR = 'PROGENITOR'
    POLYCLONAL = 'POLYCLONAL'
    MONOCLONAL = 'MONOCLONAL'


terminus_type_enum = db.Enum(TerminusTypeEnum, name='terminus_type_enum')
cell_line_type_enum = db.Enum(CellLineTypeEnum, name='cell_line_type_enum')
well_id_enum = db.Enum(*constants.DATABASE_WELL_IDS, name='well_id_type_enum')


class CellLine(Base):
    '''
    All cell lines - progenitor, polyclonal, and monoclonal
    Progenitor cell lines are included here so that parent_id exists for both polyclonal lines
    that are direct descendents of a progenitor line and for monoclonal lines
    (that are, at least for now, descendents of a polyclonal line)
    '''

    __tablename__ = 'cell_line'

    id = db.Column(db.Integer, primary_key=True)

    # parent_id is only null for progenitor cell lines
    parent_id = db.Column(db.Integer, db.ForeignKey('cell_line.id'), nullable=True)
    # line_type = db.Column(cell_line_type_enum, nullable=False)

    # optional human-readable name
    name = db.Column(db.String, nullable=True)

    # optional human-readable notes
    notes = db.Column(db.String, nullable=True)

    children = db.orm.relationship('CellLine')
    parent = db.orm.relationship('CellLine', remote_side=[id])
    pulldown = db.orm.relationship('Pulldown', back_populates='cell_line')


    def __init__(self, line_type, name=None, notes=None, parent_id=None):
        '''
        For simplicity, we only allow instantiation using an explicit parent_id,
        not by providing a list of children instances or a parent instance
        '''
        # if parent_id is None and line_type != CellLineTypeEnum.PROGENITOR.value:
        #     raise ValueError('A parent_id is required for all derived cell lines')

        self.line_type = line_type
        self.parent_id = parent_id
        self.name = name
        self.notes = notes


    def __repr__(self):
        return "<CellLine(id=%s, parent_id=%s, type='%s')>" % \
            (self.id, self.parent_id, self.line_type)


class Pulldown(Base):
    '''
    every bait (cell_line) used in MS analysis
    '''

    __tablename__ = 'pulldown'

    # Columns
    id = db.Column(db.Integer, primary_key=True)
    cell_line_id = db.Column(db.Integer, db.ForeignKey('cell_line.id'))
    replicate = db.Column(db.Integer)
    pulldown_plate_id = db.Column(db.String,
        db.ForeignKey('pulldown_plate.id'))

    pulldown_well_id = db.Column(db.String)
    # flag for quality
    qc_flag = db.Column(db.String)
    # dataset_id = db.Column(db.String)

    # Relationships
    cell_line = db.orm.relationship('CellLine', back_populates='pulldown')
    hits = db.orm.relationship('Hits', back_populates='pulldown')
    pulldown_plate = db.orm.relationship("PulldownPlate", back_populates='pulldown')

    # constraints
    __table_args__ = (
            db.UniqueConstraint(pulldown_plate_id, pulldown_well_id),
    )

    def __repr__(self):
        return "<Bait(id=%s, pulldown_plate=%s, pulldown_well=%s)>" % \
            (self.id, self.pulldown_plate_id, self.pulldown_well_id)


class Hits(Base):
    '''
    every identified hits in the base
    '''

    __tablename__ = 'hits'

    # Columns
    id = db.Column(db.Integer, primary_key=True)
    pulldown_id = db.Column(db.Integer, db.ForeignKey('pulldown.id'))
    # target string is ProteinIDs (collection of uniprot protein ids)
    protein_group_id = db.Column(db.String, db.ForeignKey('protein_group.id'))
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
    cell_prepped_by = db.Column(db.String)
    ms_prepped_by = db.Column(db.String)
    prep_date = db.Column(db.DateTime)
    ship_date = db.Column(db.DateTime)
    run_date = db.Column(db.DateTime)
    quant_date = db.Column(db.DateTime)

    # Relationships
    pulldown = db.orm.relationship("Pulldown", back_populates='pulldown_plate')


class Electroporation(Base):
    '''
    A single electroporation event/experiment

    Although a serial primary key is used, we require that the columns
    (cell_line_id, plate_instance_id, and electroporation_date) be unique
    to reflect the fact that the same plate would/should never be electroporated
    more than once on the same day.

    '''
    __tablename__ = 'electroporation'

    id = db.Column(db.Integer, primary_key=True)
    electroporation_date = db.Column(db.Date, nullable=False)

    plate_instance_id = db.Column(db.Integer, db.ForeignKey('plate_instance.id'), nullable=False)
    plate_instance = db.orm.relationship('PlateInstance', back_populates='electroporations')

    # the id of the progenitor cell line (the line that was used in the electroporation)
    cell_line_id = db.Column(db.Integer, db.ForeignKey('cell_line.id'), nullable=False)
    cell_line = db.orm.relationship('CellLine')

    # constraints
    __table_args__ = (
        db.UniqueConstraint(cell_line_id, plate_instance_id, electroporation_date),
    )

    def __repr__(self):
        return "<Electroporation(cell_line_id=%s, plate_design_id=%s, electroporation_date=%s)>" % \
            (self.cell_line_id, self.plate_instance.plate_design_id, self.electroporation_date)


class PlateInstance(Base):
    '''
    A physical instance of a plate design

    Currently (2019-07-01), there is no meaningful distinction between
    a plate 'design' and a plate 'instance', because there is only one physical instance
    of each design. This table is included in anticipation of future experiments
    in which new physical instances of the same plate design are created and should be tracked.

    Note that, technically, each plate instance is prepared by combining several reagents,
    two of which - the guides and the repair templates - themselves exist on separate plates,
    and it is not yet clear whether a replicate preparation of the same plate design
    from the same physical reagents should correspond to a new 'instance',
    or whether the reagents themselves must be distinct.

    '''
    __tablename__ = 'plate_instance'

    id = db.Column(db.Integer, primary_key=True)
    instance_date = db.Column(db.Date)
    instance_notes = db.Column(db.String)
    plate_design_id = db.Column(db.String, db.ForeignKey('plate_design.design_id'), nullable=False)

    # many-to-one (multiple instances of the same plate design may exist)
    plate_design = db.orm.relationship('PlateDesign', back_populates='plate_instances')

    # one-to-many (the same instance may be electroporated multiple times)
    electroporations = db.orm.relationship('Electroporation', back_populates='plate_instance')

    def __repr__(self):
        return "<PlateInstance(plate_design_id='%s', id=%s)>" % (self.plate_design_id, self.id)


class PlateDesign(Base):
    '''
    Plate designs
    Keyed by a plate_id of the form 'P0001'
    '''
    __tablename__ = 'plate_design'

    # design_id is manually generated and of the form 'P0001'
    design_id = db.Column(db.String, primary_key=True)
    design_date = db.Column(db.Date)
    design_notes = db.Column(db.String)

    # one-to-many relationships with crispr_design and plate_instance
    crispr_designs = db.orm.relationship(
        'CrisprDesign',
        back_populates='plate_design',
        cascade='all, delete, delete-orphan')

    plate_instances = db.orm.relationship(
        'PlateInstance',
        back_populates='plate_design',
        cascade='all, delete, delete-orphan')

    def __repr__(self):
        return "<PlateDesign(design_id='%s')>" % self.design_id

    @db.orm.validates('design_id')
    def validate_design_id(self, key, value):
        '''
        Validate and maybe format the plate design id
        '''
        return utils.format_plate_design_id(value)


class CrisprDesign(Base):
    '''
    Crispr designs

    This table combines three pieces of information:
        1) the crispr design itself (the guide and template sequences)
        2) the target metadata (gene name/family, ensembl ID, etc)
        3) the well in which the crispr design appears on the plate

    In principle, the crispr design and target metadata should have their own tables,
    since multiple crispr designs may (and sometimes do) share the same target,
    and the same design may appear in multiple wells and/or plate designs.

    In practice, however, this kind of overlap is rare enough that, for now,
    we take the shortcut of combining the design, target, and plate layout (well_id)
    into one table. Doing so also eliminates the complexity of
    1) determining how to uniquely identify targets, and
    2) checking whether each design and target is unique when inserting new plate designs.

    Furthermore, we do *not* require that the crispr design be unique
    (i.e., that the (protospacer_sequence, template_sequence) columns be unique),
    because there are several examples from plates 1-19 in which the same sequences
    are associated with distinct target names and metadata. Depending on how
    these apparent discrepancies are resolved, we can later consider placing a unique constraint
    on the guide and template sequences.

    Note that we use a serial primary key, but (well_id, plate_design_id) must be unique.

    '''
    __tablename__ = 'crispr_design'

    id = db.Column(db.Integer, primary_key=True)

    well_id = db.Column(well_id_enum, nullable=False)
    plate_design_id = db.Column(db.String, db.ForeignKey('plate_design.design_id'), nullable=False)

    # gene/protein name
    target_name = db.Column(db.String, nullable=False)

    # optional gene family
    target_family = db.Column(db.String)

    # terminus at which the template was inserted
    # TODO: decide if NOT NULL is appropriate here
    # (currently, some designs from P0016 are null,
    # but only the 'jin' designs that should be ignored anyway)
    target_terminus = db.Column(terminus_type_enum, nullable=False)

    # notes/justification for terminus selection
    terminus_notes = db.Column(db.String)

    # ensemble transcript id
    # (see https://uswest.ensembl.org/info/genome/genebuild/genome_annotation.html)
    transcript_id = db.Column(db.String)

    # 'enst_note' column
    transcript_notes = db.Column(db.String)

    # transcript expression level from an RNAseq experiment for HEK293
    # HACK: this data really belongs in a separate table of transcript metadata
    hek_tpm = db.Column(db.Float)

    template_name = db.Column(db.String)
    template_notes = db.Column(db.String)
    template_sequence = db.Column(db.String, nullable=False)

    protospacer_name = db.Column(db.String)
    protospacer_notes = db.Column(db.String)
    protospacer_sequence = db.Column(db.String, nullable=False)

    # many to one (96 wells per plate)
    plate_design = db.orm.relationship('PlateDesign', back_populates='crispr_designs')

    # constraints
    __table_args__ = (
        db.UniqueConstraint(plate_design_id, well_id),
    )

    def __repr__(self):
        return "<CrisprDesign(target_name='%s')>" % self.target_name


    @db.orm.validates('well_id')
    def format_well_id(self, key, value):
        '''
        Zero-pad well_ids ('A1' -> 'A01')
        '''
        return utils.format_well_id(value)


    @db.orm.validates('target_terminus')
    def format_target_terminus(self, key, value):
        '''
        Coerce values beginning with 'int' to 'INTERNAL'
        '''
        if value is None:
            return value

        value = value.lower()
        if value.startswith('int'):
            print("Warning: terminus type '%s' coerced to INTERNAL" % value)
            value = TerminusTypeEnum.INTERNAL
        elif value.startswith('c'):
            if value != 'c':
                print("Warning: terminus type '%s' coerced to C_TERMINUS" % value)
            value = TerminusTypeEnum.C_TERMINUS
        elif value.startswith('n'):
            if value != 'n':
                print("Warning: terminus type '%s' coerced to N_TERMINUS" % value)
            value = TerminusTypeEnum.N_TERMINUS
        return value


    @db.orm.validates('transcript_id')
    def validate_transcript_id(self, key, value):
        # check that transcript_id is a valid ensembl ID
        if value is not None and not re.match('^ENST[0-9]+$', value):
            raise ValueError('Invalid transcript_id %s' % value)
        return value


    @db.orm.validates('protospacer_sequence')
    def validate_protospacer_sequence(self, key, value):
        if not utils.is_sequence(value):
            raise ValueError('Invalid protospacer sequence %s' % value)
        return value


    @db.orm.validates('template_sequence')
    def validate_template_sequence(self, key, value):
        if not utils.is_sequence(value):
            raise ValueError('Invalid template sequence %s' % value)
        return value
