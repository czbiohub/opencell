import os
import re
import enum
import json
import numpy as np
import pandas as pd
import sqlalchemy as db
from contextlib import contextmanager

from opencell import constants
from opencell.database import models
from opencell.imaging.processors import FOVProcessor


@contextmanager
def session_scope(url, echo=False):

    engine = db.create_engine(url, echo=echo)
    Session = db.orm.sessionmaker(bind=engine)
    session = Session()

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def add_all(session, rows):
    try:
        session.add_all(rows)
        session.commit()
    except Exception as exception:
        session.rollback()
        print('Error in add_all: %s' % str(exception))


def add_and_commit(session, instances, errors='raise'):
    '''
    Add and commit instances (rows) one at a time,
    raising or warning about any errors that occur
    '''
    if not isinstance(instances, list):
        instances = [instances]

    for instance in instances:
        try:
            session.add(instance)
            session.commit()
        except Exception as exception:
            session.rollback()
            if errors == 'raise':
                raise
            if errors == 'warn':
                print('Error in add_and_commit: %s' % exception)


def delete_and_commit(session, instances):

    if not isinstance(instances, list):
        instances = [instances]

    for instance in instances:
        try:
            session.delete(instance)
            session.commit()
        except Exception:
            session.rollback()
            raise


def to_jsonable(data):
    '''
    hackish way to make a dict JSON-safe
    '''
    return json.loads(pd.Series(data=data).to_json())


def get_or_create_progenitor_cell_line(session, name, notes=None, create=False):
    '''
    Get or create a progenitor cell line by manual entry

    'Progenitor' cell lines are strictly those used for electroporations;
    they are therefore the root nodes in the self-referential cell_line table
    (which contains predominately polyclonal and monoclonal lines).

    The use of a human-readable name here is just for convenience and is intended
    to facilitate the creation/retrieval of the progenitor cell lines used for electroporation
    (of which we can assume there will be very few).

    Parameters
    ----------
    name : required human-readable and unique name for the cell_line
    notes : optional human-readable notes about the cell line
    create : whether to create a cell line with the given name if one does not already exist

    Returns
    -------
    A CellLine instance corresponding to the progenitor cell line

    '''

    # check whether the progenitor cell line already exists
    cell_line = (
        session.query(models.CellLine)
        .filter(models.CellLine.name == name)
        .one_or_none()
    )
    if cell_line is not None:
        print("Warning: a cell line with the name '%s' already exists" % name)

    elif create:
        print("Creating progenitor cell line with name '%s'" % name)
        cell_line = models.CellLine(name=name, notes=notes, line_type='PROGENITOR')
        add_and_commit(session, cell_line, errors='raise')

    else:
        cell_line = None
        print(
            "No progenitor cell line with name '%s' found; use create=True to force its creation"
            % name)

    return cell_line


class PlateOperations:
    '''
    Operations that create or modify a particular plate design

    Methods
    -------
    from_id
    get_or_create_plate_design
    create_crispr_designs
    '''

    def __init__(self, plate_design):
        self.plate_design = plate_design


    @classmethod
    def from_id(cls, session, design_id):
        '''
        Initialize from a design_id
        '''

        plate_design = (
            session.query(models.PlateDesign)
            .filter(models.PlateDesign.design_id == design_id)
            .one_or_none()
        )
        if plate_design is None:
            raise ValueError('Plate design %s does not exist' % design_id)
        return cls(plate_design)


    @classmethod
    def get_or_create_plate_design(cls, session, design_id, date=None, notes=None):
        '''
        Get or create a new plate design
        Note that this method is intended to be the only way
        in which new plate designs are created

        If the design_id already exists, we issue a warning
        but load and instantiate from the existing plate
        '''

        try:
            plate_operations = cls.from_id(session, design_id)
            print('Warning: design_id %s already exists; loading existing design' % design_id)
            return plate_operations
        except ValueError:
            pass

        # note that date and notes may be None
        plate_design = models.PlateDesign(
            design_id=design_id, design_date=date, design_notes=notes)
        try:
            add_and_commit(session, plate_design)
        except Exception:
            print('Error creating design %s' % plate_design.design_id)
            raise

        return cls(plate_design)


    def create_crispr_designs(
        self,
        session,
        library_snapshot,
        drop_existing=False,
        errors='warn'
    ):
        '''
        Convenience method to insert all crispr designs for the current plate
        from a snapshot of the library spreadsheet.

        Parameters
        ----------
        session : sqlalchemy session
        library_snapshot : a snapshot of the library spreadsheet as a pandas dataframe
        drop_existing : whether to drop any existing crispr designs linked to this plate

        '''

        # crop the library to the current plate
        designs = library_snapshot.loc[
            library_snapshot.plate_id == self.plate_design.design_id
        ].copy()

        # discard the plate_id
        designs.drop(labels=['plate_id'], axis=1, inplace=True)

        # coerce nan to None (sqlalchemy doesn't coerce np.nan to NULL)
        designs.replace({pd.np.nan: None}, inplace=True)

        # check that we have the expected number of designs/wells
        if designs.shape[0] != len(constants.DATABASE_WELL_IDS):
            raise ValueError('%s designs found; expected 96' % designs.shape[0])

        # drop the negative (empty) controls
        designs = designs.loc[designs.target_name != 'empty_control']

        # delete all existing crispr designs
        if drop_existing:
            delete_and_commit(session, self.plate_design.crispr_designs)

        # create all designs and maybe warn about errors
        for _, design in designs.iterrows():
            self.plate_design.crispr_designs.append(models.CrisprDesign(**design))
            add_and_commit(session, self.plate_design, errors=errors)


def create_polyclonal_lines(
    session,
    progenitor_cell_line,
    plate_design,
    date,
    errors='warn'
):
    '''
    Create the polyclonal lines generated by electroporating a single plate

    Parameters
    ----------
    progenitor_cell_line : the CellLine instance corresponding to the electroporated cell line
    plate_design : the PlateDesign instance corresponding to the electroporated plate
    date : the date, as a string, of the electroporation
            (required to disambiguate electroporations of the same plate)
    '''

    # create the electroporation
    electroporation = models.Electroporation(
        progenitor_cell_line=progenitor_cell_line,
        plate_design=plate_design,
        date_performed=date
    )
    add_and_commit(session, electroporation, errors=errors)

    # create a polyclonal line for each crispr design
    for crispr_design in plate_design.crispr_designs:
        cell_line = models.CellLine(
            parent_id=progenitor_cell_line.id,
            electroporation=electroporation,
            crispr_design=crispr_design,
            line_type='POLYCLONAL',
        )
        add_and_commit(session, cell_line, errors=errors)


class PolyclonalLineOperations:
    '''
    '''

    def __init__(self, line):
        self.line = line


    @classmethod
    def from_line_id(cls, session, line_id, eager=False):
        '''
        '''
        query = session.query(models.CellLine)
        if eager:
            query = query.options(
                db.orm.joinedload(models.CellLine.fovs, innerjoin=True)
                .joinedload(models.MicroscopyFOV.results, innerjoin=True)
            )
        return cls(query.get(line_id))


    @classmethod
    def from_plate_well(cls, session, design_id, well_id):
        '''
        Convenience method to retrieve the cell line
        corresponding to a plate design and a well id
        (assuming that there is only one such cell line)
        '''

        design = (
            session.query(models.CrisprDesign)
            .filter(models.CrisprDesign.plate_design_id == design_id)
            .filter(models.CrisprDesign.well_id == well_id)
            .one_or_none()
        )
        if not design or not design.cell_lines:
            raise ValueError('No cell line found for well %s of plate %s' %
                (well_id, design_id))

        if len(design.cell_lines) > 1:
            raise ValueError('More than one cell line exists for well %s of plate %s' %
                (well_id, design_id))

        return cls(design.cell_lines[0])


    @classmethod
    def from_target_name(cls, session, target_name):
        '''
        Convenience method to retrieve the cell line for the given target_name

        If there is more than one cell_line for the target_name,
        then the PolyClonalLineOperations class is instantiated using the first such cell_line
        '''

        designs = (
            session.query(models.CrisprDesign)
            .filter(db.func.lower(models.CrisprDesign.target_name) == db.func.lower(target_name))
            .all()
        )

        lines = []
        [lines.extend(design.cell_lines) for design in designs]

        if len(lines) > 1:
            print('Warning: %s cell lines found for target_name %s' % (len(lines), target_name))
        if not lines:
            raise ValueError('No cells lines found for target %s' % target_name)

        return cls(lines[0])


    def insert_facs_dataset(self, session, histograms, scalars, errors='warn'):
        '''
        Insert the processed FACS data for a single polyclonal cell line
        '''

        # drop any existing data
        if self.line.facs_dataset:
            delete_and_commit(session, self.line.facs_dataset)

        facs_dataset = models.FACSDataset(
            cell_line=self.line,
            scalars=to_jsonable(scalars),
            histograms=to_jsonable(histograms))
        add_and_commit(session, facs_dataset, errors=errors)


    def insert_sequencing_dataset(self, session, scalars, errors='warn'):
        '''
        Insert a limited set of the sequencing results - just the HDR/all and HDR/modified ratios
        '''

        # drop any existing data
        if self.line.sequencing_dataset:
            delete_and_commit(session, self.line.sequencing_dataset)

        sequencing_dataset = models.SequencingDataset(
            cell_line=self.line,
            scalars=to_jsonable(scalars))
        add_and_commit(session, sequencing_dataset, errors=errors)


    def insert_microscopy_fovs(self, session, metadata, errors='warn'):
        '''
        Insert a set of microscopy FOVs for the cell line

        metadata : dataframe of raw FOV metadata with the following columns:
        pml_id, imaging_round_id, site_num, raw_filepath
        '''

        fovs = self.line.fovs
        for _, row in metadata.iterrows():
            fov = models.MicroscopyFOV(
                cell_line=self.line,
                pml_id=row.pml_id,
                site_num=row.site_num,
                raw_filename=row.raw_filepath,
                imaging_round_id=row.imaging_round_id,
            )
            fovs.append(fov)
        add_and_commit(session, fovs, errors=errors)


    def construct_payload(self, kind=None):
        '''
        Construct the JSON payload returned by the lines/ endpoint of the API

        Note that, awkwardly, the RNAseq data is a column in the crispr_design table
        '''
        design = self.line.crispr_design

        # metadata object included in every playload
        metadata = {
            'cell_line_id': self.line.id,
            'well_id': design.well_id,
            'plate_id': design.plate_design_id,
            'target_name': design.target_name,
            'target_family': design.target_family,
            'target_terminus': design.target_terminus.value[0],
            'transcript_id': design.transcript_id,
            'hek_tpm': design.hek_tpm,
        }
        payload = {'metadata': metadata}

        if kind in ['all', 'scalars']:
            payload['scalars'] = self.construct_scalars_payload()
            payload['annotations'] = self.line.annotation.categories if self.line.annotation else None

        if kind in ['all', 'facs'] and self.line.facs_dataset:
            payload['facs_histograms'] = self.line.facs_dataset.simplify_histograms()

        if kind in ['all', 'rois', 'thumbnails']:
            payload['fovs'] = self.construct_fov_payload(kind=kind)

        return payload


    def construct_scalars_payload(self):
        '''
        Aggregate various scalar properties/features/results
        '''
        scalars = {}

        # the sequencing percentages
        if self.line.sequencing_dataset:
            scalars.update({
                'hdr_all': self.line.sequencing_dataset.scalars.get('hdr_all'),
                'hdr_modified': self.line.sequencing_dataset.scalars.get('hdr_modified')
            })

        # the FACS area and relative median intensity
        if self.line.facs_dataset:
            scalars.update({
                'facs_area': self.line.facs_dataset.scalars.get('area'),
                'facs_intensity': self.line.facs_dataset.scalars.get('rel_median_log')
            })
        return scalars


    def construct_fov_payload(self, kind=None):
        '''
        JSON payload describing the FOVs and ROIs
        '''
        payload = []
        for fov in self.line.fovs:
            fov_payload = {}

            # basic metadata
            fov_metadata = {
                'id': fov.id,
                'score': fov.get_score(),
                'pml_id': fov.dataset.pml_id,
                'src_filename': fov.raw_filename,
                'z_step_size': FOVProcessor.z_step_size(fov.dataset.pml_id),
            }

            fov_payload['annotation'] = fov.annotation.as_dict() if fov.annotation else None

            # append the 488 exposure settings
            metadata = fov.get_result('raw-tiff-metadata')
            if metadata:
                fov_metadata['laser_power_488'] = metadata.data.get('laser_power_488_488')
                fov_metadata['exposure_time_488'] = metadata.data.get('exposure_time_488')
                fov_metadata['max_intensity_488'] = metadata.data.get('max_intensity_488')

            # the position of the cell layer center (relative to the bottom of the stack)
            metadata = fov.get_result('clean-tiff-metadata')
            if metadata and metadata.data.get('cell_layer_center') is not None:
                fov_metadata['cell_layer_center'] = (
                    metadata.data.get('cell_layer_center') * fov_metadata['z_step_size']
                )

            if kind in ['all', 'rois']:
                fov_payload['rois'] = [roi.as_dict() for roi in fov.rois]

            if kind in ['all', 'thumbnails']:
                thumbnail = fov.get_thumbnail('rgb')
                fov_payload['thumbnails'] = thumbnail.as_dict() if thumbnail else None

            fov_payload['metadata'] = fov_metadata
            payload.append(fov_payload)

        # sort FOVs by score (unscored FOVs last)
        payload = sorted(payload, key=lambda row: row['metadata'].get('score') or -2)[::-1]
        return payload


class MicroscopyFOVOperations:
    '''
    Methods to insert metadata associated with, or 'children' of, microscopy FOVs

    FOV-associated metadata includes the raw tiff metadata, FOV features, and thumbnails,
    FOV 'children' include the ROIs cropped from each FOV

    NOTE: instances of this class cannot be associated with instances of models.MicroscopyFOV
    (in the way that, for example, PolyclonalLineOperations instances
    are associated with instances of models.CellLine)
    because they may be passed to dask.delayed-wrapped methods

    '''

    def __init__(self, fov_id):
        self.fov_id = fov_id


    def insert_raw_tiff_metadata(self, session, result):
        '''
        Insert the raw tiff metadata and raw TIFF processing events
        generated by FOVProcessor.process_raw_tiff

        Parameters
        ----------
        result : dict with 'metadata' and 'events' keys
            (this should be the output of FOVProcessor.process_raw_tiff)
        '''

        result = to_jsonable(result)
        metadata = result.get('metadata')
        events = result.get('events')

        row = models.MicroscopyFOVResult(
            fov_id=self.fov_id,
            kind='raw-tiff-metadata',
            data=metadata)
        add_and_commit(session, row, errors='raise')

        if len(events):
            row = models.MicroscopyFOVResult(
                fov_id=self.fov_id,
                kind='raw-tiff-processing-events',
                data=events)
            add_and_commit(session, row, errors='raise')


    def insert_fov_features(self, session, result):
        '''
        Insert FOV features
        result : dict returned by FOVProcessor.calculate_fov_features
        '''
        result = to_jsonable(result)
        row = models.MicroscopyFOVResult(
            fov_id=self.fov_id,
            kind='fov-features',
            data=result)
        add_and_commit(session, row, errors='raise')


    def insert_fov_thumbnails(self, session, result):
        '''
        Insert FOV thumbnails
        result : dict returned by FOVProcessor.generate_fov_thumbnails
        '''
        result = to_jsonable(result)

        rows = []
        for channel, encoded_im in result['encoded_ims'].items():
            row = models.MicroscopyThumbnail(
                fov_id=self.fov_id,
                size=result.get('size'),
                channel=channel,
                data=encoded_im)
            rows.append(row)
        add_and_commit(session, rows, errors='raise')


    def insert_z_profiles(self, session, result):
        '''
        Insert z-profiles
        result : dict returned by FOVProcessor.calculate_z_profiles
        '''
        result = to_jsonable(result)
        row = models.MicroscopyFOVResult(
            fov_id=self.fov_id,
            kind='z-profiles',
            data=result)
        add_and_commit(session, row, errors='raise')


    def insert_clean_tiff_metadata(self, session, result):
        '''
        Insert result from the generate_clean_tiff method
        '''
        result = to_jsonable(result)
        row = models.MicroscopyFOVResult(
            fov_id=self.fov_id,
            kind='clean-tiff-metadata',
            data=result)
        add_and_commit(session, row, errors='raise')


    def _insert_rois(self, session, result, roi_kind):
        '''
        result : tuple of (error_info, roi_props) returned by FOVProcessor.crop_rois
        roi_kind : 'corner' or 'annotated'
        '''

        # FOVProcessor.crop_annotated_roi returns None if no manual annotation existed
        if result is None:
            return

        result, all_roi_props = result
        result = to_jsonable(result)
        result_kind = '%s-roi-cropping' % roi_kind

        row = models.MicroscopyFOVResult(
            fov_id=self.fov_id,
            kind=result_kind,
            data=result)
        add_and_commit(session, row, errors='raise')

        rois = []
        for roi_props in all_roi_props:
            roi_props = to_jsonable(roi_props)
            roi = models.MicroscopyFOVROI(
                fov_id=self.fov_id,
                kind=roi_kind,
                props=roi_props
            )
            rois.append(roi)
        add_and_commit(session, rois, errors='raise')


    def insert_corner_rois(self, session, result):
        '''
        Insert the four ROIs cropped from each corner of an FOV
        '''
        self._insert_rois(session, result, roi_kind='corner')


    def insert_annotated_roi(self, session, result):
        '''
        Insert the single manually-annotated ROI (if any)
        '''
        self._insert_rois(session, result, roi_kind='annotated')
