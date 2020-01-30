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
        for column in self.__table__.columns:  # pylint: disable=no-member
            value = getattr(self, column.name)
            if isinstance(value, enum.Enum):
                value = value.value
            try:
                if pd.isna(value):
                    value = None
            except ValueError:
                pass
            d[column.name] = value
        return d


Base = db.ext.declarative.declarative_base(cls=Base, metadata=metadata)


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
    line_type = db.Column(cell_line_type_enum, nullable=False)

    # optional human-readable name
    name = db.Column(db.String, nullable=True)

    # optional human-readable notes
    notes = db.Column(db.String, nullable=True)

    children = db.orm.relationship('CellLine')
    parent = db.orm.relationship('CellLine', remote_side=[id])

    # electroporation_line that generated the cell line (if any)
    electroporation_line = db.orm.relationship(
        'ElectroporationLine', back_populates='cell_line', uselist=False)

    # manual annotation
    annotation = db.orm.relationship(
        'CellLineAnnotation', back_populates='cell_line', uselist=False)


    def __init__(self, line_type, name=None, notes=None, parent_id=None):
        '''
        For simplicity, we only allow instantiation using an explicit parent_id,
        not by providing a list of children instances or a parent instance
        '''
        if parent_id is None and line_type != CellLineTypeEnum.PROGENITOR.value:
            raise ValueError('A parent_id is required for all derived cell lines')

        self.line_type = line_type
        self.parent_id = parent_id
        self.name = name
        self.notes = notes

    def __repr__(self):
        return "<CellLine(id=%s, parent_id=%s, type='%s')>" % \
            (self.id, self.parent_id, self.line_type)


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

    # the id of the progenitor cell line (the line that was used in the electroporation)
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

    # one-to-one mapping to CellLine
    cell_line_id = db.Column(db.Integer, db.ForeignKey('cell_line.id'), primary_key=True)
    cell_line = db.orm.relationship('CellLine', back_populates='electroporation_line')

    # one-to-many mapping to Electroporation
    electroporation_id = db.Column(db.Integer, db.ForeignKey('electroporation.id'), primary_key=True)
    electroporation = db.orm.relationship('Electroporation', back_populates='electroporation_lines')


class FACSDataset(Base):
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

    TODO: add columns for date_generated, git_commit, and sample/control dirpaths

    '''

    __tablename__ = 'facs_dataset'

    cell_line_id = db.Column(db.Integer, db.ForeignKey('cell_line.id'), primary_key=True)
    cell_line = db.orm.relationship('CellLine', backref='facs_dataset')

    # histograms
    histograms = db.Column(postgresql.JSONB)

    # extracted properties (area, median intensity, etc)    
    scalars = db.Column(postgresql.JSONB)


class SequencingDataset(Base):
    '''
    Some processed results from the sequencing dataset for a single polyclonal cell line
    '''

    __tablename__ = 'sequencing_dataset'

    cell_line_id = db.Column(db.Integer, db.ForeignKey('cell_line.id'), primary_key=True)
    cell_line = db.orm.relationship('CellLine', backref='sequencing_dataset')

    # extracted properties 
    # (percent HDR among all alleles and modified alleles)
    scalars = db.Column(postgresql.JSONB)


class MicroscopyDataset(Base):
    '''
    A confocal microscopy dataset

    These datasets are assumed to correspond to automated acquisitions
    using the confocal (dragonfly) microscope that have PML-style IDs (e.g., PML0123)

    These datasets almost always consist of images from many wells,
    but by definition consist only of images from one imaging plate.

    Note, however, that a single imaging plate may have wells from more than one pipeline plate.

    '''

    __tablename__ = 'microscopy_dataset'

    # the manually-defined pml_id (also called exp_id)
    pml_id = db.Column(db.String, primary_key=True)

    # the manually-defined imaging date
    date = db.Column(db.Date, nullable=False)

    # either 'plate_microscopy' or 'raw_pipeline_microscopy'
    # (the absolute path to these directories is context-dependent)
    root_directory = db.Column(db.String)

    @db.orm.validates('pml_id')
    def validate_pml_id(self, key, value):
        match = re.match(r'^PML[0-9]{4}$', value)
        if match is None:
            raise ValueError('Invalid pml_id %s' % value)
        return value

    @db.orm.validates('root_directory')
    def validate_root_directory(self, key, value):
        if value not in ['plate_microscopy', 'raw_pipeline_microscopy']:
            raise ValueError('Invalid root_directory %s' % value)
        return value


class MicroscopyFOV(Base):
    '''
    A single confocal z-stack of one field of view (FOV)

    Notes
    -----
    One entry in this table corresponds to a single raw TIFF stack
    in the 'PlateMicroscopy' directory
    For example: 'mNG96wp19/ML0137_20190528/mNG96wp19_sortday1/A9_1_BAG6.ome.tif'

    '''

    __tablename__ = 'microscopy_fov'

    id = db.Column(db.Integer, primary_key=True)

    # many-to-one relationship with cell_line
    cell_line_id = db.Column(db.Integer, db.ForeignKey('cell_line.id'))
    cell_line = db.orm.relationship('CellLine', backref='fovs')

    # many-to-one relationship with microscopy_dataset
    pml_id = db.Column(db.String, db.ForeignKey('microscopy_dataset.pml_id'))
    dataset = db.orm.relationship('MicroscopyDataset', backref='fovs')

    # one-to-many relationship with FOV results
    results = db.orm.relationship(
        'MicroscopyFOVResult', back_populates='fov', cascade='all, delete-orphan')

    # one-to-many relationship with FOV ROIs
    rois = db.orm.relationship(
        'MicroscopyFOVROI', back_populates='fov', cascade='all, delete-orphan')

    # one-to-many relationship with thumbnails
    thumbnails = db.orm.relationship(
        'Thumbnail', back_populates='fov', cascade='all, delete-orphan')

    # round_id is either 'R01' (initial post-sort imaging) 
    # or 'R02' (thawed-plate imaging)
    imaging_round_id = db.Column(db.String, nullable=False)

    # the original site number (required to construct unique dst filenames)
    site_num = db.Column(db.Integer, nullable=False)

    # the path to the original raw TIFF, relative to the root_directory
    raw_filename = db.Column(db.String)

    # because we image by plate, each well_id is imaged once per plate
    # this fact can be expressed by the following constraint
    # (assuming that each cell line appears in only one well on each imaging plate)
    __table_args__ = (
        db.UniqueConstraint(pml_id, cell_line_id, site_num),
    )

    @db.orm.validates('pml_id')
    def validate_pml_id(self, key, value):
        match = re.match(r'^PML[0-9]{4}$', value)
        if match is None:
            raise ValueError('Invalid pml_id %s' % value)
        return value

    @db.orm.validates('imaging_round_id')
    def validate_imaging_round_id(self, key, value):
        match = re.match(r'^R[0-9]{2}$', value)
        if match is None:
            raise ValueError('Invalid imaging_round_id %s' % value)
        return value


class MicroscopyFOVResult(Base):
    '''
    Various kinds of data derived from a microscopy FOV as arbitrary JSON objects

    Examples: the metadata generated by FOVProcessor.process_raw_tiff,
    or the features extracted from the Hoechst z-projection used to predict FOV scores
    '''

    __tablename__ = 'microscopy_fov_result'

    id = db.Column(db.Integer, primary_key=True)
    fov_id = db.Column(db.Integer, db.ForeignKey('microscopy_fov.id'))
    timestamp = db.Column(db.DateTime(timezone=True), server_default=db.sql.func.now())

    fov = db.orm.relationship('MicroscopyFOV', back_populates='results', uselist=False)
 
    # the kind or type of the result ('raw-tiff-metadata', 'fov-features', etc)
    # (eventually, this should be changed to an enum)
    kind = db.Column(db.String)

    # the result data
    data = db.Column(postgresql.JSONB)


class MicroscopyFOVROI(Base):
    '''
    An ROI cropped from a raw FOV

    These ROIs are intended specifically for the volume visualization in the frontend

    The crop can be in any or all of the x, y, and z dimensions
    (usually, all crops are at least cropped in z around the cell layer)

    Also, usually, the intensities have been normalized and downsampled to uint8,
    using the min/max intensities and (optionally) a gamma

    '''

    __tablename__ = 'microscopy_fov_roi'

    id = db.Column(db.Integer, primary_key=True)
    fov_id = db.Column(db.Integer, db.ForeignKey('microscopy_fov.id'))
    timestamp = db.Column(db.DateTime(timezone=True), server_default=db.sql.func.now())

    fov = db.orm.relationship('MicroscopyFOV', back_populates='rois', uselist=False)
    thumbnails = db.orm.relationship('Thumbnail', back_populates='roi')

    # kind of ROI: either 'corner', 'top-scoring', 'single-nucleus', 'single-cell'
    kind = db.Column(db.String)

    # all ROI-specific metadata, including the ROI oordinates (position and shape), 
    # the z-coordinate of the center of the cell layer,  and the min/max values 
    # used to downsample the intensities from uint16 to uint8
    props = db.Column(postgresql.JSONB)


class Thumbnail(Base):
    '''
    An image thumbnail of either an ROI or an FOV
    '''

    __tablename__ = 'thumbnail'

    id = db.Column(db.Integer, primary_key=True)
    fov_id = db.Column(db.Integer, db.ForeignKey('microscopy_fov.id'))
    roi_id = db.Column(db.Integer, db.ForeignKey('microscopy_fov_roi.id'))

    fov = db.orm.relationship('MicroscopyFOV', back_populates='thumbnails', uselist=False)
    roi = db.orm.relationship('MicroscopyFOVROI', back_populates='thumbnails', uselist=False)

    # the size (in pixels) of the thumbnail image (which is assumed to be square)
    size = db.Column(db.Integer)

    # either 'dapi', 'gfp', or 'rgb'
    channel = db.Column(db.String)

    # thumbnail itself as a base64-encoded PNG file
    data = db.Column(db.String)


class CellLineAnnotation(Base):
    '''
    '''

    __tablename__ = 'cell_line_annotation'

    id = db.Column(db.Integer, primary_key=True)

    # one-to-one relationship with cell_line
    cell_line_id = db.Column(db.Integer, db.ForeignKey('cell_line.id'))
    cell_line = db.orm.relationship('CellLine', back_populates='annotation', uselist=False)

    date_created = db.Column(db.DateTime(timezone=True), server_default=db.sql.func.now())

    # free-form comments
    comment = db.Column(db.String)

    # the list of categories to which the cell line belongs
    categories = db.Column(postgresql.JSONB)

    # the client-side timestamp, app state, etc
    client_metadata = db.Column(postgresql.JSONB)
