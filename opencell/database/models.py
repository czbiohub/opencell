import re
import enum
import numpy as np
import pandas as pd
import sqlalchemy as db
import sqlalchemy.orm
import sqlalchemy.ext.declarative
from sqlalchemy.dialects import postgresql

from opencell import constants
from opencell.database import utils


# constraint naming conventions
# see https://alembic.sqlalchemy.org/en/latest/naming.html
metadata = db.MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
    }
)


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

    # the type of cell line (progenitor, polyclonal, and monoconal)
    line_type = db.Column(cell_line_type_enum, nullable=False)

    # the sort count if the line is polyclonal (tracks resorts)
    sort_count = db.Column(db.Integer, nullable=True)

    # the sort date (for polyclonal and monoclonal lines)
    sort_date = db.Column(db.Date, nullable=True)

    # optional human-readable name
    name = db.Column(db.String, nullable=True)

    # optional human-readable notes
    notes = db.Column(db.String, nullable=True)

    # note that these foreign key ids are only null for progenitor cell lines
    parent_id = db.Column(db.Integer, db.ForeignKey('cell_line.id'), nullable=True)
    crispr_design_id = db.Column(db.Integer, db.ForeignKey('crispr_design.id'), nullable=True)

    parent = db.orm.relationship('CellLine', remote_side=[id])
    children = db.orm.relationship('CellLine')

    # the crispr design used to generate the cell line (if any)
    crispr_design = db.orm.relationship(
        'CrisprDesign', back_populates='cell_lines', uselist=False
    )

    # one cell line to one manual annotation
    annotation = db.orm.relationship(
        'CellLineAnnotation', back_populates='cell_line', uselist=False
    )

    # one cell line to one FACS dataset
    facs_dataset = db.orm.relationship(
        'FACSDataset', back_populates='cell_line', uselist=False
    )

    # one cell line to one sequencing dataset
    sequencing_dataset = db.orm.relationship(
        'SequencingDataset', back_populates='cell_line', uselist=False
    )

    # one cell_line to many FOVs
    fovs = db.orm.relationship('MicroscopyFOV', back_populates='cell_line')

    # one cell_line to many pulldowns
    pulldowns = db.orm.relationship('MassSpecPulldown', back_populates='cell_line')

    def __repr__(self):
        return (
            "<CellLine(id=%s, parent_id=%s, type='%s', target='%s')>"
            % (
                self.id,
                self.parent_id,
                self.line_type.value,
                self.crispr_design.target_name if self.crispr_design else None
            )
        )


    def get_best_pulldown(self):
        '''
        Get the 'good' pulldown
        This logic is necessary because there may be multiple pulldowns per cell line,
        but only ever one 'good' one whose hits should be displayed/analyzed
        '''
        if not self.pulldowns:
            return None

        # the manually-flagged 'good' pulldowns
        # (there should be only one of these, but we don't enforce this)
        candidate_pulldowns = [
            pulldown for pulldown in self.pulldowns if pulldown.manual_display_flag
        ]
        if not candidate_pulldowns:
            candidate_pulldowns = self.pulldowns
        return candidate_pulldowns[0]


    def get_top_scoring_fovs(self, ntop=None):
        '''
        Get the n highest-scoring FOVs
        '''
        scores = np.array([fov.get_score() for fov in self.fovs])

        # sort the FOVs by score
        mask = ~pd.isna(scores)
        scores[~mask] = -1
        inds = np.argsort(np.array(scores))[::-1]

        # drop inds without a score
        scores = [score for score in scores if score is not None]
        inds = inds[mask[inds]]

        # the n-highest-scoring FOVs
        ntop = len(inds) if ntop is None else ntop
        top_fovs = [self.fovs[ind] for ind in inds[:ntop]]
        return top_fovs


    def get_best_fov(self):
        '''
        Get the 'best' FOV
        For now, this is the first FOV that is manually annotated
        (using get_top_scoring_fovs is too slow)
        '''
        for fov in self.fovs:
            if fov.annotation:
                return fov
        return None


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

    # one plate design to many crispr designs
    crispr_designs = db.orm.relationship(
        'CrisprDesign',
        back_populates='plate_design',
        cascade='all, delete, delete-orphan'
    )

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

    # gene/protein name
    target_name = db.Column(db.String, nullable=False)

    # gene family (optional)
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

    # transcript expression level from RNAseq data for HEK293
    # HACK: this data really belongs in a separate table of transcript metadata
    hek_tpm = db.Column(db.Float)

    template_name = db.Column(db.String)
    template_notes = db.Column(db.String)
    template_sequence = db.Column(db.String, nullable=False)

    protospacer_name = db.Column(db.String)
    protospacer_notes = db.Column(db.String)
    protospacer_sequence = db.Column(db.String, nullable=False)

    # the plate_design on which this crispr_design appears
    plate_design_id = db.Column(
        db.String, db.ForeignKey('plate_design.design_id'), nullable=False
    )

    # the uniprot_id of the transcript tagged by the design
    uniprot_id = db.Column(
        db.String, db.ForeignKey('uniprot_metadata.uniprot_id')
    )

    # the raw (unprocessed/unparsed) uniprot metadata
    uniprot_metadata = db.orm.relationship(
        'UniprotMetadata', back_populates='crispr_designs', uselist=False
    )

    # many crispr_designs to one plate_design (96 wells per plate)
    plate_design = db.orm.relationship(
        'PlateDesign', back_populates='crispr_designs', uselist=False
    )

    # one crispr_design to many cell lines
    cell_lines = db.orm.relationship('CellLine', back_populates='crispr_design')

    # one crispr design to many mass spec protein groups
    protein_groups = db.orm.relationship(
        'MassSpecProteinGroup',
        secondary='protein_group_crispr_design_association',
        back_populates='crispr_designs'
    )

    # the well_id must be unique in each plate design
    __table_args__ = (
        db.UniqueConstraint(plate_design_id, well_id),
    )

    def __repr__(self):
        return (
            "<CrisprDesign(plate_id='%s', well_id=%s', target_name='%s')>" %
            (self.plate_design_id, self.well_id, self.target_name)
        )

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

    def get_best_cell_line(self):
        '''
        Logic to choose the 'best' cell line when there is more than one
        '''
        if not self.cell_lines:
            return None

        for line in self.cell_lines:
            if line.sort_count > 1:
                return line

        for line in self.cell_lines:
            if line.get_best_pulldown():
                return line

        for line in self.cell_lines:
            if line.fovs:
                return line

        return self.cell_lines[0]


class UniprotMetadata(Base):
    '''
    Cached Uniprot metadata retrieved by querying UniprotKB and the Uniprot mapper API
    (see methods in uniprot_utils for details)
    '''

    __tablename__ = 'uniprot_metadata'
    uniprot_id = db.Column(db.String, primary_key=True)

    # these columns correspond to columns retrieved by UniprotKB queries
    protein_names = db.Column(db.String)
    protein_families = db.Column(db.String)
    gene_names = db.Column(db.String)
    annotation = db.Column(db.String)

    # the ENSG ID is not included in the UniprotKB query results;
    # it must be populated separately using the Uniprot mapper API
    ensg_id = db.Column(db.String)

    date_created = db.Column(db.DateTime(timezone=True), server_default=db.sql.func.now())

    # one uniprot_id to many crispr designs
    crispr_designs = db.orm.relationship('CrisprDesign', back_populates='uniprot_metadata')

    def get_primary_gene_name(self):
        return self.gene_names.split(' ')[0] if self.gene_names != 'NaN' else self.uniprot_id

    def __repr__(self):
        return (
            "<UniprotMetadata(uniprot_id='%s', ensg_id=%s', gene_name='%s')>" %
            (self.uniprot_id, self.ensg_id, self.get_primary_gene_name())
        )


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

    # histograms
    histograms = db.Column(postgresql.JSONB)

    # extracted properties (area, median intensity, etc)
    scalars = db.Column(postgresql.JSONB)

    # one dataset to one cell_line
    cell_line = db.orm.relationship('CellLine', back_populates='facs_dataset', uselist=False)


    def simplify_histograms(self):
        '''
        Downsample and discretize the histograms
        This is intended to reduce the payload size when the histograms
        will only be used to generate thumbnail/sparkline-like plots

        Note that the scaling, rounding, and 2x-subsampling were empirically determined
        as the most extreme downsampling that still yields satisfactory thumbnail-sized plots
        ('thumbnail-sized' means plots on the order of 100px wide)
        '''

        if self.histograms is None:
            return None
        histograms = self.histograms.copy()

        # x-axis values can be safely rounded to ints
        histograms['x'] = [int(x) for x in histograms['x']]

        # y-axis values (densities) must be scaled before rounding
        scale_factor = 1e6
        for key in 'y_sample', 'y_ref_fitted':
            histograms[key] = [int(y*scale_factor) for y in histograms[key]]

        # finally, downsample by 2x
        for key in histograms.keys():
            histograms[key] = histograms[key][::2]
        return histograms


class SequencingDataset(Base):
    '''
    Some processed results from the sequencing dataset for a single polyclonal cell line
    '''

    __tablename__ = 'sequencing_dataset'

    cell_line_id = db.Column(db.Integer, db.ForeignKey('cell_line.id'), primary_key=True)

    # extracted properties (percent HDR among all alleles and modified alleles)
    scalars = db.Column(postgresql.JSONB)

    # one dataset to one cell_line
    cell_line = db.orm.relationship(
        'CellLine', back_populates='sequencing_dataset', uselist=False
    )


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

    # all columns from the pipeline-microscopy-master-key as a JSON object
    # (for reference/convenience only)
    raw_metadata = db.Column(postgresql.JSONB)

    # one dataset to many FOVs
    fovs = db.orm.relationship('MicroscopyFOV', back_populates='dataset')

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

    # many FOVs to one cell_line
    cell_line_id = db.Column(db.Integer, db.ForeignKey('cell_line.id'))
    cell_line = db.orm.relationship('CellLine', back_populates='fovs', uselist=False)

    # many FOVs to one microscopy_dataset
    pml_id = db.Column(db.String, db.ForeignKey('microscopy_dataset.pml_id'))
    dataset = db.orm.relationship('MicroscopyDataset', back_populates='fovs', uselist=False)

    # one FOV to many FOV results
    results = db.orm.relationship(
        'MicroscopyFOVResult', back_populates='fov', cascade='all, delete-orphan'
    )

    # one FOV to many ROIs
    rois = db.orm.relationship(
        'MicroscopyFOVROI', back_populates='fov', cascade='all, delete-orphan'
    )

    # one FOV to many thumbnails
    thumbnails = db.orm.relationship(
        'MicroscopyThumbnail', back_populates='fov', cascade='all, delete-orphan'
    )

    # one FOV to one FOV annotation
    annotation = db.orm.relationship(
        'MicroscopyFOVAnnotation',
        back_populates='fov',
        uselist=False,
        cascade='all, delete-orphan'
    )

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
    __table_args__ = (db.UniqueConstraint(pml_id, cell_line_id, site_num),)

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

    def get_result(self, kind):
        '''
        Retrieve a MicroscopyFOVResult of the given kind
        (Note that this method will be slow without eager-loading)
        '''
        result = [result for result in self.results if result.kind == kind]
        return result[0] if result else None

    def get_result_via_query(self, kind):
        '''
        Retrieve a MicroscopyFOVResult of the given kind
        This is a query-based alternative to get_result that will be faster without eager loading
        '''
        return (
            db.orm.object_session(self)
            .query(MicroscopyFOVResult)
            .filter(MicroscopyFOVResult.fov_id == self.id)
            .filter(MicroscopyFOVResult.kind == kind)
            .one_or_none()
        )

    def get_score(self):
        features = self.get_result('fov-features')
        return features.data.get('score') if features else None

    def get_thumbnail(self, channel):
        '''
        Retrieve the thumbnail of the FOV
        (note that this method uses a subquery because it is unlikely
         that the Thumbnail table will be eager-loaded)
        '''
        return (
            db.orm.object_session(self)
            .query(MicroscopyThumbnail)
            .filter(MicroscopyThumbnail.fov_id == self.id)
            .filter(MicroscopyThumbnail.channel == channel)
            .one_or_none()
        )


class MicroscopyFOVResult(Base):
    '''
    Various kinds of data derived from a microscopy FOV as arbitrary JSON objects

    Examples: the metadata generated by FOVProcessor.process_raw_tiff,
    or the features extracted from the Hoechst z-projection used to predict FOV scores
    '''

    __tablename__ = 'microscopy_fov_result'

    id = db.Column(db.Integer, primary_key=True)
    fov_id = db.Column(db.Integer, db.ForeignKey('microscopy_fov.id'))
    date_created = db.Column(db.DateTime(timezone=True), server_default=db.sql.func.now())

    # many results to one FOV
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
    date_created = db.Column(db.DateTime(timezone=True), server_default=db.sql.func.now())

    # many ROIs to one FOV
    fov = db.orm.relationship('MicroscopyFOV', back_populates='rois', uselist=False)

    # one ROI to many thumbnails
    thumbnails = db.orm.relationship('MicroscopyThumbnail', back_populates='roi')

    # kind of ROI: either 'corner' or 'annotated'
    kind = db.Column(db.String)

    # all ROI-specific metadata, including the ROI coordinates (position and shape),
    # the z-coordinate of the center of the cell layer,  and the min/max values
    # used to downsample the intensities from uint16 to uint8
    props = db.Column(postgresql.JSONB)

    def get_thumbnail(self, channel):
        '''
        Retrieve the thumbnail of the ROI
        (this is an almost direct copy of MicroscopyFOV.get_thumbnail)
        '''
        return (
            db.orm.object_session(self)
            .query(MicroscopyThumbnail)
            .filter(MicroscopyThumbnail.roi_id == self.id)
            .filter(MicroscopyThumbnail.channel == channel)
            .one_or_none()
        )


class MicroscopyThumbnail(Base):
    '''
    A base64-encoded thumbnail of either an ROI or an FOV
    '''

    __tablename__ = 'microscopy_thumbnail'

    id = db.Column(db.Integer, primary_key=True)
    fov_id = db.Column(db.Integer, db.ForeignKey('microscopy_fov.id'))
    roi_id = db.Column(db.Integer, db.ForeignKey('microscopy_fov_roi.id'))
    date_created = db.Column(db.DateTime(timezone=True), server_default=db.sql.func.now())

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

    # one anotation to one cell_line
    cell_line_id = db.Column(db.Integer, db.ForeignKey('cell_line.id'))
    cell_line = db.orm.relationship('CellLine', back_populates='annotation', uselist=False)

    date_created = db.Column(db.DateTime(timezone=True), server_default=db.sql.func.now())

    # free-form comments
    comment = db.Column(db.String)

    # the list of categories to which the cell line belongs
    categories = db.Column(postgresql.JSONB)

    # the client-side timestamp, app state, etc
    client_metadata = db.Column(postgresql.JSONB)


class MicroscopyFOVAnnotation(Base):
    '''
    '''

    __tablename__ = 'microscopy_fov_annotation'
    id = db.Column(db.Integer, primary_key=True)

    # one annotation to one FOV
    fov_id = db.Column(db.Integer, db.ForeignKey('microscopy_fov.id'))
    fov = db.orm.relationship('MicroscopyFOV', back_populates='annotation', uselist=False)

    date_created = db.Column(db.DateTime(timezone=True), server_default=db.sql.func.now())

    # the row and column of the top-left corner of the user-selected ROI
    roi_position_top = db.Column(db.Integer)
    roi_position_left = db.Column(db.Integer)

    # the list of categories to which the FOV belongs (currently unused)
    categories = db.Column(postgresql.JSONB)

    # the client-side timestamp, app state, etc
    client_metadata = db.Column(postgresql.JSONB)


class MassSpecPulldownPlate(Base):
    '''
    A mass spec plate prepped by the ML Group

    Note that these plates consist of sets of pulldowns performed on some subset of cell lines,
    and are totally unrelated to the plates of crispr designs in the plate_design table.
    '''
    __tablename__ = 'mass_spec_pulldown_plate'

    # format is of the form 'CZBMPI_{plate_num:04d}'
    id = db.Column(db.String, primary_key=True)

    # link to the google sheet design of the plate mapping out pulldown
    # target locations by well
    plate_design_link = db.Column(db.String)

    # Description of the pulldown (whether it is a repeat or subset, etc)
    description = db.Column(db.String)

    # timestamp column
    date_created = db.Column(db.DateTime(timezone=True), server_default=db.sql.func.now())

    # one plate to many pulldowns
    pulldowns = db.orm.relationship('MassSpecPulldown', back_populates='pulldown_plate')


class MassSpecPulldown(Base):
    '''
    A pulldown performed on a cell_line and analyzed by ms-ms
    (in which the GFP-tagged target was used as the 'bait')
    '''

    __tablename__ = 'mass_spec_pulldown'
    id = db.Column(db.Integer, primary_key=True)
    cell_line_id = db.Column(db.Integer, db.ForeignKey('cell_line.id'))
    pulldown_plate_id = db.Column(
        db.String, db.ForeignKey('mass_spec_pulldown_plate.id'), nullable=False
    )

    # 1% fdr offset and curvature calculated for this pulldown
    fdr_1_offset = db.Column(db.Float)
    fdr_1_curvature = db.Column(db.Float)

    # 5% fdr offset and curvature calculated for this pulldown
    fdr_5_offset = db.Column(db.Float)
    fdr_5_curvature = db.Column(db.Float)

    # manual flag for the pulldown to be shown in the OC if there are
    # multiple pulldowns per crisprdesign. Boolean variable:
    # pulldown flag with 1 should be displayed, 0 should not be displayed
    manual_display_flag = db.Column(db.Boolean)

    # timestamp column
    date_created = db.Column(db.DateTime(timezone=True), server_default=db.sql.func.now())

    # one pulldown to one cell line
    cell_line = db.orm.relationship('CellLine', back_populates='pulldowns', uselist=False)

    # one pulldown to many hits
    hits = db.orm.relationship('MassSpecHit', back_populates='pulldown')

    # one pulldown to one pulldown_plate
    pulldown_plate = db.orm.relationship(
        'MassSpecPulldownPlate', back_populates='pulldowns', uselist=False
    )

    # the cached cytoscape network for the pulldown
    network = db.orm.relationship(
        'MassSpecPulldownNetwork', back_populates='pulldown', uselist=False
    )

    def get_target_name(self):
        '''Convenience method to get target_name for each pulldown'''
        return self.cell_line.crispr_design.target_name


    def get_significant_hits(self, eagerload=True):
        '''
        Retrieve the significant hits and eager-load their protein groups
        and the protein groups' crispr designs and uniprot metadata
        '''
        query = (
            db.orm.object_session(self).query(MassSpecHit)
            .options(db.orm.joinedload(MassSpecHit.protein_group, innerjoin=True))
            .filter(MassSpecHit.pulldown_id == self.id)
            .filter(db.or_(
                MassSpecHit.is_minor_hit == True,  # noqa
                MassSpecHit.is_significant_hit == True  # noqa
            ))
        )

        if eagerload:
            query = query.options(
                db.orm.joinedload(MassSpecHit.protein_group, innerjoin=True)
                .joinedload(MassSpecProteinGroup.crispr_designs),
                db.orm.joinedload(MassSpecHit.protein_group, innerjoin=True)
                .joinedload(MassSpecProteinGroup.uniprot_metadata),
            )

        significant_hits = query.all()
        return significant_hits


    def get_bait_hit(self, only_one=False):
        '''
        Get the hit(s) that corresponds to the pulldown's target/bait
        Returns none if the bait does not appear among the hits
        '''
        bait_hits = (
            db.orm.object_session(self).query(MassSpecHit)
            .join(MassSpecProteinGroup)
            .join(ProteinGroupCrisprDesignAssociation)
            .join(CrisprDesign)
            .filter(MassSpecHit.pulldown_id == self.id)
            .filter(db.or_(
                MassSpecHit.is_minor_hit == True,  # noqa
                MassSpecHit.is_significant_hit == True  # noqa
            ))
            .filter(CrisprDesign.id == self.cell_line.crispr_design.id)
            .all()
        )

        if not bait_hits:
            return None

        if only_one:
            # return the hit with the greatest enrichment
            bait_hits = sorted(bait_hits, key=lambda hit: -hit.enrichment)
            return bait_hits[0]

        return bait_hits


    def get_interacting_pulldowns(self):
        '''
        '''
        interacting_pulldowns = (
            db.orm.object_session(self).query(MassSpecPulldown).join(MassSpecHit)
            .filter(db.or_(
                MassSpecPulldown.manual_display_flag == None,  # noqa
                MassSpecPulldown.manual_display_flag == True  # noqa
            ))
            .filter(MassSpecPulldown.id != self.id)
            .filter(
                MassSpecHit.protein_group_id.in_(
                    [pg.id for pg in self.cell_line.crispr_design.protein_groups]
                )
            )
            .filter(db.or_(
                MassSpecHit.is_minor_hit == True,  # noqa
                MassSpecHit.is_significant_hit == True  # noqa
            ))
            .all()
        )
        return interacting_pulldowns


    def __repr__(self):
        return (
            "<MassSpecPulldown(id=%s, pulldown_plate_id=%s, target_name=%s)>"
            % (self.id, self.pulldown_plate_id, self.get_target_name())
        )


class MassSpecProteinGroup(Base):
    '''
    A protein group identified by msms in experiments
    '''

    __tablename__ = 'mass_spec_protein_group'

    # id is a hash of unique set of peptide Uniprot ids that compose the protein group
    id = db.Column(db.String, primary_key=True)

    # a list of all uniprot gene names mapped to the protein group
    gene_names = db.Column(postgresql.ARRAY(db.String))

    # a list of all peptide Uniprot ids (including isoforms)
    uniprot_ids = db.Column(postgresql.ARRAY(db.String))

    # timestamp column
    date_created = db.Column(db.DateTime(timezone=True), server_default=db.sql.func.now())

    # one protein_group to many hits
    hits = db.orm.relationship('MassSpecHit', back_populates='protein_group')

    # one protein group to (possibly) more than one crispr design
    crispr_designs = db.orm.relationship(
        'CrisprDesign',
        secondary='protein_group_crispr_design_association',
        back_populates='protein_groups'
    )

    # one protein group to multiple uniprot metadata rows
    uniprot_metadata = db.orm.relationship(
        'UniprotMetadata',
        secondary='protein_group_uniprot_metadata_association'
    )

    def __repr__(self):
        return "<MassSpecProteinGroup(gene_names=[%s])>" % (', '.join(self.gene_names))


class ProteinGroupUniprotMetadataAssociation(Base):
    '''
    The protein_group - uniprot_id associations
    (does not include isoforms - that is, includes only uniprot_ids without dashes)
    '''
    __tablename__ = 'protein_group_uniprot_metadata_association'
    uniprot_id = db.Column(
        db.String, db.ForeignKey('uniprot_metadata.uniprot_id'), primary_key=True
    )
    protein_group_id = db.Column(
        db.String, db.ForeignKey('mass_spec_protein_group.id'), primary_key=True
    )


class ProteinGroupCrisprDesignAssociation(Base):
    '''
    '''
    __tablename__ = 'protein_group_crispr_design_association'
    crispr_design_id = db.Column(
        db.Integer, db.ForeignKey('crispr_design.id'), primary_key=True
    )
    protein_group_id = db.Column(
        db.String, db.ForeignKey('mass_spec_protein_group.id'), primary_key=True
    )


class MassSpecHit(Base):
    '''
    A hit is a protein group identified in a pulldown and associated with a mass-spec intensity.
    Here the table is populated with the pre-computed enrichment and p-value
    of the hit compared to a base distribution.
    '''

    __tablename__ = 'mass_spec_hit'
    id = db.Column(db.Integer, primary_key=True)

    # hashed string of sorted Uniprot peptide IDs that compose the protein group
    protein_group_id = db.Column(db.String, db.ForeignKey('mass_spec_protein_group.id'))

    # foreign key of each pulldown target from pulldown table
    pulldown_id = db.Column(db.Integer, db.ForeignKey('mass_spec_pulldown.id'), nullable=False)

    # p-value of the hit's MS intensity
    pval = db.Column(db.Float, nullable=False)

    # enrichment of the hit's MS intensity
    enrichment = db.Column(db.Float, nullable=False)

    # boolean specifying whether the hit is significant based on FDR threshold
    is_significant_hit = db.Column(db.Boolean)

    # boolean specifying whether the hit is significant based on a lower FDR threshold
    is_minor_hit = db.Column(db.Boolean)

    # interaction stoichiometry of the prey relative to the target
    interaction_stoich = db.Column(db.Float)

    # abundance stoichiometry of the prey relative to the garget
    abundance_stoich = db.Column(db.Float)

    # timestamp column
    date_created = db.Column(db.DateTime(timezone=True), server_default=db.sql.func.now())

    # many hits to one pulldown
    pulldown = db.orm.relationship('MassSpecPulldown', back_populates='hits', uselist=False)

    # one hit to one protein_group
    protein_group = db.orm.relationship(
        'MassSpecProteinGroup', back_populates='hits', uselist=False
    )

    # A hit needs to have a unique set of target (pulldown) and the prey (protein_group)
    __table_args__ = (db.UniqueConstraint(pulldown_id, protein_group_id),)

    def __repr__(self):
        return (
            "<MassSpecHit(bait=%s, pval=%0.2f, enrichment=%0.2f, gene_names=[%s])>"
            % (
                self.pulldown.get_target_name(),
                float(self.pval),
                float(self.enrichment),
                ', '.join(self.protein_group.gene_names)
            )
        )


class MassSpecClusterHeatmap(Base):
    """
    This table contains hard-coded cluster memberships of interactions as well as
    coordinates for hierarchical layout of cluster heatmap. Used for cluster heatmap
    visualization in OpenCell
    """

    __tablename__ = 'mass_spec_cluster_heatmap'
    id = db.Column(db.Integer, primary_key=True)

    # cluster group id - in a numerical range
    cluster_id = db.Column(db.Integer, nullable=False)

    # subcluster group id - in a numerical range
    subcluster_id = db.Column(db.Integer, nullable=True)

    # core complex id - in a numerical range
    core_complex_id = db.Column(db.Integer, nullable=True)

    # hit id that the heatmap coordinate refers to in target-prey match
    hit_id = db.Column(db.Integer, db.ForeignKey('mass_spec_hit.id'), nullable=False)

    # row index of the heat map
    row_index = db.Column(db.Integer, nullable=False)

    # col index of the heatmap
    col_index = db.Column(db.Integer, nullable=False)

    # clustering analysis identifier describing the cluster pipeline used.
    analysis_type = db.Column(db.String, nullable=False)

    # many cluster rows to one mass spec hit
    hit = db.orm.relationship('MassSpecHit', uselist=False)

    # The row and col indexes should be unique within a cluster
    __table_args__ = (db.UniqueConstraint(cluster_id, row_index, col_index, analysis_type),)


class MassSpecPulldownNetwork(Base):
    '''
    Cached cytoscape network and layout (generated by cytoscapejs)
    '''
    __tablename__ = 'mass_spec_pulldown_network'

    id = db.Column(db.Integer, primary_key=True)

    # one network to one pulldown
    pulldown_id = db.Column(db.Integer, db.ForeignKey('mass_spec_pulldown.id'))
    pulldown = db.orm.relationship(
        'MassSpecPulldown', back_populates='network', uselist=False
    )

    date_created = db.Column(db.DateTime(timezone=True), server_default=db.sql.func.now())
    last_modified = db.Column(db.DateTime(timezone=True), server_default=db.sql.func.now())

    # the JSON dump from cy.json()
    cytoscape_json = db.Column(postgresql.JSONB)

    # the client-side timestamp, app state, etc
    client_metadata = db.Column(postgresql.JSONB)
