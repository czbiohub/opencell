import re
import enum

import pandas as pd
import sqlalchemy as db
import sqlalchemy.orm
import sqlalchemy.ext.declarative
from sqlalchemy.dialects import postgresql

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


class Base(object):

    # TODO: decide whether we need to keep `extend_existing` here 
    # (originally for autoreloading during development)
    __table_args__ = {'extend_existing': True}

    def as_dict(self):
        '''
        Rudimentary object serialization, intended to facilitate
        the construction of JSON-able objects
        '''
        d = {}
        for column in self.__table__.columns: # pylint: disable=no-member
            value = getattr(self, column.name)
            if isinstance(value, enum.Enum):
                value = value.value
            if pd.isna(value):
                value = None
            d[column.name] = value
        return d


Base = db.ext.declarative.declarative_base(cls=Base, metadata=metadata)


# enum types
well_id_enum = db.Enum(*constants.DATABASE_WELL_IDS, name='well_id_type_enum')
terminus_type_enum = db.Enum(constants.TerminusTypeEnum, name='terminus_type_enum')
cell_line_type_enum = db.Enum(constants.CellLineTypeEnum, name='cell_line_type_enum')


class MasterCellLine(Base):
    '''
    Table of master cell lines
    (cell lines on which electroporations were performed)
    '''

    __tablename__ = 'master_cell_line'

    # human-readable nickname; this is also the primary key
    nickname = db.Column(db.String, primary_key=True)

    # optional human-readable notes
    notes = db.Column(db.String)

    # the id of this cell line in the cell_line table
    cell_line_id = db.Column(db.Integer, db.ForeignKey('cell_line.id'), nullable=False)
    cell_line = db.orm.relationship('CellLine', backref='master_cell_line')

    def __repr__(self):
        return "<MasterCellLine(nickname='%s')>" % self.nickname


class CellLine(Base):
    '''
    All cell lines - master, polyclonal, and monoclonal
    
    Master cell lines are included here so that parent_id exists for both polyclonal lines
    that are direct descendents of a master cell line and for monoclonal lines 
    (that are, at least for now, descendents of a polyclonal line)

    '''

    __tablename__ = 'cell_line'

    id = db.Column(db.Integer, primary_key=True)
    
    # parent_id is only null for master cell lines
    parent_id = db.Column(db.Integer, db.ForeignKey('cell_line.id'), nullable=True)
    line_type = db.Column(cell_line_type_enum, nullable=False)

    children = db.orm.relationship('CellLine')
    parent = db.orm.relationship('CellLine', remote_side=[id])

    def __repr__(self):
        return "<CellLine(id=%s, parent_id=%s, type='%s')>" % \
            (self.id, self.parent_id, self.line_type)

    def __init__(self, line_type, parent_id=None):
        '''
        For simplicity, we only allow instantiation using an explicit parent_id,
        not by providing a list of children instances or a parent instance
        '''
        if parent_id is None and line_type!=constants.CellLineTypeEnum.MASTER:
            raise ValueError('A parent_id is required for all derived cell lines')
        self.line_type = line_type
        self.parent_id = parent_id


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
        Transform well_ids like 'A1' to 'A01'
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
            value = constants.TerminusTypeEnum.INTERNAL
        elif value.startswith('c'):
            if value!='c':
                print("Warning: terminus type '%s' coerced to C_TERMINUS" % value)
            value = constants.TerminusTypeEnum.C_TERMINUS
        elif value.startswith('n'):
            if value!='n':
                print("Warning: terminus type '%s' coerced to N_TERMINUS" % value)
            value = constants.TerminusTypeEnum.N_TERMINUS
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

    # the id of the master cell line that was electroporated
    cell_line_id = db.Column(db.Integer, db.ForeignKey('cell_line.id'), nullable=False)
    cell_line = db.orm.relationship('CellLine')

    # all of the cell lines directly generated by the electroporations
    electroporation_lines = db.orm.relationship('ElectroporationLine', back_populates='electroporation')

    # constraints
    __table_args__ = (
        db.UniqueConstraint(cell_line_id, plate_instance_id, electroporation_date),
    )

    def __repr__(self):
        return "<Electroporation(cell_line_id=%s, plate_design_id=%s, electroporation_date=%s)>" % \
            (self.cell_line_id, self.plate_instance.plate_design_id, self.electroporation_date)


class ElectroporationLine(Base):
    '''
    Association table that maps cell lines to the electroporation and well_id 
    from which they originated. 

    We use a composite primary key on (electroporation_id, cell_line_id).
    
    Note that there are no constraints on the type or number of cell lines 
    associated with an electroporation, even though currently (July 2019),
    only a single polyclonal line is generated from each electroporation and well_id. 
    This flexibility is intended to anticipate a possibly future workflow 
    in which multiple monoclonal lines are generated from each electroporation,
    without an intermediate polyclonal line. 
    
    '''

    __tablename__ = 'electroporation_line'

    well_id = db.Column(well_id_enum, nullable=False)

    cell_line_id = db.Column(db.Integer, db.ForeignKey('cell_line.id'), primary_key=True)
    cell_line = db.orm.relationship('CellLine', backref='electroporation')

    electroporation_id = db.Column(db.Integer, db.ForeignKey('electroporation.id'), primary_key=True)
    electroporation = db.orm.relationship('Electroporation', back_populates='electroporation_lines')


class FACSResults(Base):
    '''
    A single FACS dataset, consisting of 
        1) the sample and fitted reference histograms
        2) various extracted properties (GFP-positive area, median/max intensities, etc)

    Each of these datasets must correspond to a single cell line,
    and there should be only one dataset per cell line, though this may change 
    and is currently not enforced.

    In practice, and possibly also in principle, FACS datasets should exist 
    only for polyclonal lines, though this is not currently enforced.

    For now, we use the cell_line_id as the primary key. 

    TODO: add columns for date_generated, git_commit, and sample/control dirpathas

    '''

    __tablename__ = 'facs_results'

    cell_line_id = db.Column(db.Integer, db.ForeignKey('cell_line.id'), primary_key=True)
    cell_line = db.orm.relationship('CellLine', backref='facs_results')

    # histograms
    histograms = db.Column(postgresql.JSONB)

    # extracted properties/features    
    scalar_columns = [
        'fitted_offset',
        'left_right_boundary',
        'area',
        'raw_mean',
        'raw_std',
        'raw_median',
        'raw_percentile99',
        'rel_mean_linear',
        'rel_mean_log',
        'rel_mean_hlog',
        'rel_median_linear',
        'rel_median_log',
        'rel_median_hlog',
        'rel_percentile99_linear',
        'rel_percentile99_log',
        'rel_percentile99_hlog',
    ]

# programmatically create all of the numeric columns
for column in FACSResults.scalar_columns:
    setattr(FACSResults, column, db.Column(db.Float))


class SequencingResults(Base):
    '''
    A set of final/processed sequencing results for a single polyclonal cell line. 

    TODO: finish implementing this!
    '''

    __tablename__ = 'sequencing_results'

    cell_line_id = db.Column(db.Integer, db.ForeignKey('cell_line.id'), primary_key=True)
    cell_line = db.orm.relationship('CellLine', backref='sequencing_results')

    # percent HDR of all sequenced alleles
    hdr_all = db.Column(db.Float)

    # percent HDR of all modified alleles
    hdr_modified = db.Column(db.Float)


class ImagingExperiment(Base):
    '''
    An imaging 'experiment'
    These are imaging 'events' with ML-style IDs (e.g., ML0001, ML0002, etc)

    '''

    __tablename__ = 'imaging_experiment'

    # the manually-defined ML-style experiment_id
    id = db.Column(db.String, primary_key=True)

    # the manually-defined imaging date
    date = db.Column(db.Date, nullable=False)

    # the primary user/imager
    user = db.Column(db.String, nullable=False)

    # user-defined description of what plate/wells were imaged
    description = db.Column(db.String)

    # other user-defined notes/comments
    user_notes = db.Column(db.String)


class Image(Base):
    '''
    A single z-stack of one field of view

    Notes
    -----
    In the 'PlateMicroscopy' directory, one image here corresponds 
    to a single raw TIFF stack in PlateMicroscopy, e.g.,
    'mNG96wp19/ML0137_20190528/mNG96wp19_sortday1/A9_1_BAG6.ome.tif'

    '''

    __tablename__ = 'image'

    id = db.Column(db.Integer, primary_key=True)

    # many-to-one relationship with cell_line
    cell_line_id = db.Column(db.Integer, db.ForeignKey('cell_line.id'))
    cell_line = db.orm.relationship('CellLine', backref='images')

    # many-to-one relationship with imaging_experiment
    imaging_experiment_id = db.Column(db.String, db.ForeignKey('imaging_experiment.id'))
    imaging_experiment = db.orm.relationship('ImagingExperiment', backref='images')

    # file hash
    sha1_hash = db.Column(db.String)

    # TIFF stack filename
    filename = db.Column(db.String)
