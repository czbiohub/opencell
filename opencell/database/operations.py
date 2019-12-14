import os
import re
import enum
import pandas as pd
import sqlalchemy as db

from contextlib import contextmanager
from opencell.database import models
from opencell.imaging import processors
from opencell import constants


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

    if not isinstance(instances, list):
        instances = [instances]

    for instance in instances:
        try:
            session.add(instance)
            session.commit()
        except Exception as exception:
            session.rollback()
            if errors=='raise':
                raise
            if errors=='warn':
                print('Error in add_and_commit: %s' % exception)

    # except db.exc.IntegrityError:
    # except db.orm.exc.FlushError:


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
    cell_line = session.query(models.CellLine)\
        .filter(models.CellLine.name==name)\
        .first()

    if cell_line is not None:
        print("Warning: a cell line with the name '%s' already exists" % name)

    elif create:
        print("Creating progenitor cell line with name '%s'" % name)
        cell_line = models.CellLine(name=name, notes=notes, line_type='PROGENITOR')
        add_and_commit(session, cell_line, errors='raise')

    else:
        cell_line = None
        print("No progenitor cell line with name '%s' found; use create=True to force its creation" \
            % name)

    return cell_line


def get_plate_instance(session, plate_design_id, plate_instance_id):
    '''
    Convenience method to retrieve an instance of a plate design 
    by specifying a design_id and/or an instance_id

    If a design_id is provided without an instance_id, then there must be only one instance
    of the design. If there is more than one instance, an error is raised.

    If an instance_id is provided without a design_id, then we assume the user has looked up
    the correct instance_id.
    
    If both a design_id and an instance_id are provided, we check that the instance_id is indeed
    an instance of the specified design. 
    '''
    pass


class PlateOperations(object):
    '''
    Operations that create or modify a particular plate *design*

    Methods
    -------
    from_id
    create_plate_design
    create_plate_instance
    create_crispr_design

    '''

    def __init__(self, plate):
        self.plate = plate


    @classmethod
    def from_id(cls, session, design_id):
        '''
        Initialize from a design_id
        '''

        plate = session.query(models.PlateDesign)\
            .filter(models.PlateDesign.design_id==design_id).first()

        if plate is None:
            raise ValueError('Plate design %s does not exist' % design_id)

        # sanity check that there's at least one instance of the design
        if not plate.plate_instances:
            print('Warning: no plate instances exist for plate design %s' % design_id)

        return cls(plate)


    @classmethod
    def get_or_create_plate_design(cls, session, design_id, date=None, notes=None):
        '''
        Get or create a new plate design and the first instance of it

        **This is intended to be the only way in which new plate designs are created**

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
        plate = models.PlateDesign(design_id=design_id, design_date=date, design_notes=notes)

        # automatically create the first instance of the new design
        plate.plate_instances.append(
            models.PlateInstance(
                instance_date=None, 
                instance_notes='auto-generated first instance')
        )

        try:
            add_and_commit(session, plate)
        except:
            print('Error creating design %s' % plate.design_id)
            raise 
        
        return cls(plate)


    def create_plate_instance(self, date=None, notes=None):
        '''
        Manually create a new instance of the plate

        Note that this is not implemented (as of 2019-06-28), 
        because there is currently only one instance of each plate
        (and it is created automatically in create_plate_design)
        '''
        raise NotImplementedError


    def create_crispr_designs(
        self, 
        session, 
        library_snapshot, 
        drop_existing=False,
        errors='warn'):
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
        designs = library_snapshot.loc[library_snapshot.plate_id==self.plate.design_id].copy()

        # discard the plate_id
        designs.drop(labels=['plate_id'], axis=1, inplace=True)

        # coerce nan to None (sqlalchemy doesn't coerce np.nan to NULL)
        designs.replace({pd.np.nan: None}, inplace=True)

        # check that we have the expected number of designs/wells
        if designs.shape[0]!=len(constants.DATABASE_WELL_IDS):
            raise ValueError('%s designs found; expected 96' % designs.shape[0])

        # drop the negative (empty) controls
        designs = designs.loc[designs.target_name!='empty_control']
    
        # delete all existing crispr designs
        if drop_existing:
            delete_and_commit(session, self.plate.crispr_designs)

        # create all designs and maybe warn about errors
        for ind, design in designs.iterrows(): # pylint: disable=unused-variable
            self.plate.crispr_designs.append(models.CrisprDesign(**design))
            add_and_commit(session, self.plate, errors=errors)


class ElectroporationOperations(object):
    '''
    Operations that create or modify an electroporation event
    '''

    def __init__(self, electroporation):
        self.electroporation = electroporation


    @classmethod
    def create_electroporation(cls, session, cell_line, plate_instance, date, errors='warn'):
        '''
        Create a new electroporation

        Note that this *automatically* generates 96 new polyclonal cell lines. 

        Parameters
        ----------
        cell_line : an instance of CellLine corresponding to the cell line used
        plate_instance : the PlateInstance corresponding to the plate electroporated
        date : the date, as a string, of the electroporation 
               (required to disambiguate electroporations of the same plate)

        Returns
        -------
        The Electroporation instance corresponding to the new electroporation
        
        '''

        electroporation = models.Electroporation(
            cell_line=cell_line,
            plate_instance=plate_instance,
            electroporation_date=date)

        add_and_commit(session, electroporation, errors=errors) 

        # create a polyclonal line for each crispr design
        for design in electroporation.plate_instance.plate_design.crispr_designs:
            
            cell_line = models.CellLine(
                parent_id=electroporation.cell_line.id,
                line_type='POLYCLONAL')

            ep_line = models.ElectroporationLine(
                well_id=design.well_id,
                cell_line=cell_line)

            electroporation.electroporation_lines.append(ep_line)
            add_and_commit(session, electroporation, errors=errors)

        return cls(electroporation)

    
    @classmethod
    def from_plate_design_id(cls, plate_design_id):
        '''
        Convenience method to get the electroporation from a plate_design_id,
        assuming that there is only one electroporation, and one instance, of the design

        '''
        raise NotImplementedError


class PolyclonalLineOperations(object):
    '''
    '''

    def __init__(self, line):
        self.line = line


    @classmethod
    def from_line_id(cls, session, line_id):
        '''
        '''
        line = session.query(models.CellLine).filter(models.CellLine.id==line_id).first()
        return cls(line)


    @classmethod
    def from_plate_well(cls, session, design_id, well_id):
        '''
        Convenience method to retrieve the cell line corresponding to a plate design and a well id,
        *assuming* that there is only one electroporation of one instance of the plate design. 
        '''

        pi = models.PlateInstance
        ep = models.Electroporation

        this_ep = session.query(ep).filter(
            ep.plate_instance==session.query(pi).filter(pi.plate_design_id==design_id).first()
        ).first()

        for line in this_ep.electroporation_lines:
            if line.well_id==well_id:
                return cls(line.cell_line)
        
        raise ValueError('No polyclonal line found for well %s of plate %s' % (well_id, design_id))
    
    
    @classmethod
    def from_target_name(cls, session, target_name):
        '''
        Convenience method to retrieve the cell line for the given target_name

        If there is more than one cell_line for the target_name, 
        then the PolyClonalLineOperations class is instantiated using the first such cell_line
        '''
        cds = session.query(models.CrisprDesign)\
                .filter(db.func.lower(models.CrisprDesign.target_name) == db.func.lower(target_name)).all()

        if len(cds) > 1:
            print('Warning: %s cell lines found for target %s' % (len(cds), target_name))

        if len(cds) == 0:
            print('Warning: no cells lines found for target %s' % target_name)
            return

        cd = cds[0]
        ep_lines = cd.plate_design.plate_instances[0].electroporations[0].electroporation_lines
        ep_line = [line for line in ep_lines if line.well_id==cd.well_id][0]
        return cls(ep_line.cell_line)


    def insert_facs_result(self, session, histograms, scalars, errors='warn'):
        '''
        Insert the processed FACS data for a single polyclonal cell line

        This processed data is generated by the scripts in `pipeline-process/facs`. 
        '''

        # drop any existing data
        if self.line.facs_result:
            delete_and_commit(session, self.line.facs_result)

        facs_result = models.FACSResult(
            cell_line=self.line,
            histograms=histograms,
            **scalars)

        add_and_commit(session, facs_result, errors=errors)

    
    def insert_sequencing_result(self, session, scalars, errors='warn'):
        '''
        Insert a limited set of the sequencing results - just the HDR/all and HDR/modified ratios
        '''

        # drop any existing data
        if self.line.sequencing_result:
            delete_and_commit(session, self.line.sequencing_result)

        sequencing_result = models.SequencingResult(
            cell_line=self.line,
            **scalars)

        add_and_commit(session, sequencing_result, errors=errors)


    def insert_microscopy_fovs(self, session, metadata, errors='warn'):
        '''
        Insert a set of microscopy FOVs for the cell line

        metadata : dataframe of raw FOV metadata with the following columns:
        pml_id, imaging_round_id, site_num, raw_filepath
        '''

        fovs = []
        for _, row in metadata.iterrows():
            columns = {
                'pml_id': row.pml_id, 
                'imaging_round_id': row.imaging_round_id, 
                'site_num': row.site_num, 
                'raw_filename': row.raw_filepath,
            }
            fovs.append(models.MicroscopyFOV(cell_line=self.line, **columns))

        add_and_commit(session, fovs, errors=errors)


    @staticmethod
    def simplify_scalars(d):
        '''
        Simplify a dict of scalar values
        '''
        for key, value in d.items():
            if value is not None and not isinstance(value, str):
                d[key] = '%0.2f' % value
        return d


    @staticmethod
    def simplify_facs_histograms(histograms):
        '''
        Downsample and discretize the FACS histograms for a cell line
        This is intended to reduce the payload size when the histograms 
        will only be used to generate thumbnail/sparkline-like plots

        Note that the scaling, rounding, and 2x-subsampling were empirically determined
        as the most extreme downsampling that still yields satisfactory thumbnail-sized plots
        ('thumbnail-sized' means plots on the order of 100px wide)
        '''

        if histograms is None:
            return None

        # x-axis values can be safely rounded to ints
        histograms['x'] = [int(val) for val in histograms['x']]

        # y-axis values (densities) must be scaled 
        scale_factor = 1e6
        for key in 'y_sample', 'y_ref_fitted':
            histograms[key] = [int(val*scale_factor) for val in histograms[key]]

        # finally, downsample by 2x
        for key in histograms.keys():
            histograms[key] = histograms[key][::2]

        return histograms


    def construct_json(self):
        '''
        Build the JSON object returned by the lines/ endpoint of the API
        '''

        ep = self.line.electroporation_line.electroporation

        plate_id = ep.plate_instance.plate_design_id
        well_id = self.line.electroporation_line.well_id

        # the crispr design for this line
        for design in ep.plate_instance.plate_design.crispr_designs:
            if design.well_id == well_id:
                break

        # the crispr design
        # (includes plate_design_id and well_id)
        d = design.as_dict()

        # append cell-line- and electroporation-specific fields 
        d['cell_line_id'] = self.line.id
        d['electroporation_date'] = ep.electroporation_date

        # the facs results (scalars and histograms)
        # TODO: enforce one-to-one and drop the [0]
        d['facs_results'] = {}
        d['facs_histograms'] = {}
        if self.line.facs_result:
            facs_result = self.line.facs_result[0].as_dict()
            d['facs_histograms'] = self.simplify_facs_histograms(facs_result.pop('histograms'))    
            d['facs_results'] = self.simplify_scalars(facs_result)

        # the sequencing ratios
        d['sequencing_results'] = {}
        if self.line.sequencing_result:
            d['sequencing_results'] = self.simplify_scalars(self.line.sequencing_result[0].as_dict())

        # microscopy FOVs
        d['fovs'] = []
        for fov in self.line.microscopy_fovs:

            p = processors.RawZStackProcessor(
                fov_id=fov.id,
                pml_id=fov.dataset.pml_id,
                parental_line=fov.cell_line.parent.name,
                imaging_round_id=fov.imaging_round_id,
                plate_id=plate_id,
                well_id=well_id,
                site_num=fov.site_num,
                raw_filepath=fov.raw_filename,
                target_name=design.target_name)

            d['fovs'].append({
                'fov_id': fov.id,
                'pml_id': fov.dataset.pml_id,
                'src_filename': fov.raw_filename,
                'dst_filename': p.dst_filepath(dst_root='root', kind='projection', channel='dapi', axis='z'),
            })

        return d

    