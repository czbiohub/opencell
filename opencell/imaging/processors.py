import os
import re
import sys
import glob
import json
import nrrd
import pickle
import skimage
import hashlib
import datetime
import tifffile

import numpy as np
import pandas as pd

from opencell import constants
from opencell.imaging import images, utils


class FOVProcessor:

    def __init__(
        self, 
        fov_id,
        pml_id,
        parental_line, 
        imaging_round_id, 
        plate_id, 
        well_id, 
        site_num, 
        target_name,
        raw_filepath,
        all_roi_rows):
        
        self.fov_id = fov_id
        self.pml_id = pml_id
        self.parental_line = parental_line
        self.imaging_round_id = imaging_round_id
        self.plate_id = plate_id
        self.well_id = well_id
        self.site_num = site_num
        self.raw_filepath = raw_filepath

        # array of dicts for all ROIs cropped from the FOV
        self.all_roi_rows = all_roi_rows

        # clean up the target_name (remove slashes and dashes)
        self.target_name = self.clean_target_name(target_name)

        # create site_id from site_num
        self.site_id = 'S%02d' % int(self.site_num)


    @staticmethod
    def clean_target_name(target_name):
        '''
        Create a filename-safe target_name by removing slashes and dashes
        '''
        forbidden_chars = ['-', '_', '/']
        for char in forbidden_chars:
            target_name = target_name.replace(char, '')
        return target_name


    @classmethod
    def from_database(cls, fov):
        '''
        Initialize a processor given a microscopy_fov instance from opencelldb
        '''

        well_id = fov.cell_line.electroporation_line.well_id
        plate_design = fov.cell_line.electroporation_line.electroporation.plate_instance.plate_design
        crispr_design = [d for d in plate_design.crispr_designs if d.well_id == well_id].pop()

        # roi_props for all ROIs cropped from this FOV (will often be empty)
        all_roi_rows = [roi.as_dict() for roi in fov.rois]

        processor = cls(
            fov_id=fov.id,
            pml_id=fov.dataset.pml_id,
            parental_line=fov.cell_line.parent.name,
            imaging_round_id=fov.imaging_round_id,
            plate_id=plate_design.design_id,
            well_id=well_id,
            site_num=fov.site_num,
            raw_filepath=fov.raw_filename,
            target_name=crispr_design.target_name,
            all_roi_rows=all_roi_rows)

        return processor


    def z_step_size(self):
        '''
        Unpleasant method to determine the z-step size from the PML ID

        This method encodes the facts that, prior to ML0123 (aka PML0123),
        the step size was always 0.5um, and that starting at ML0123, 
        the step size has always been 0.2um.

        NOTE: this method is necessary because the z-step size is *not* encoded
        in the MicroManager metadata or anywhere else
        '''
        z_step_size = 0.2
        critical_pml_num = 123
        pml_num = int(self.pml_id[3:])
        if pml_num < critical_pml_num:
            z_step_size = 0.5
        return z_step_size


    def src_filepath(self, src_root=None):
        '''
        Construct the absolute filepath to a TIFF stack in the 'PlateMicroscopy' directory 
        from a row of metadata (works for raw and processed TIFFs)

        Returns a path of the form (relative to src_root):
        'mNG96wp15/ML0125_20190424/mNG96wp15_sortday2/C11_4_SLC35F2.ome.tif'

        src_root is the absolute path to the 'PlateMicroscopy' directory
        (e.g., on `cap`, '/gpfsML/ML_group/PlateMicroscopy/')
        '''

        src_root = '' if src_root is None else src_root
        src_filepath = os.path.join(src_root, self.raw_filepath)
        return src_filepath

    
    def dst_plate_dir(self):
        '''
        Construct a dst plate_dir from an src plate_dir

        Destination plate directory names are of the form 'czML0383-P0001-R01'
        '''
        dst_plate_dir = f'{self.parental_line}-{self.plate_id}-{self.imaging_round_id}'
        return dst_plate_dir


    def dst_filepath(
        self, 
        dst_root=None, 
        kind=None, 
        channel=None, 
        roi_id=None,
        roi_props=None,
        ext=None, 
        makedirs=True):
        '''
        Construct the relative directory path and filename for a given 'kind' of output file

        The full path is of the form '{kind}/{dst_plate_dir}/{dst_filename}'
        dst_plate_dir is of the form 'czML0383-P0001-R01'
        dst_filename is of the form '{dst_plate_dir}-ML0123-A01-S01-CLTA_{kind}-{channel}'
        
        If `kind` is an 'ROI kind' (e.g., 'nrrd' or 'tile'), and if roi_coords are provided,
        then the roi_coords are included in the filename:
        'czML00383-P0001-R01-ML0123-A01-S01-CLTA_ROI-0424-0000-0600-0600-DAPI'

        '''

        if dst_root is None:
            dst_root = ''

        kinds = ['metadata', 'proj', 'nrrd', 'tile', 'ijclean']
        if kind not in kinds:
            raise ValueError('%s is not a valid destination kind' % kind)
        appendix = kind.upper()

        # retrieve the roi_props if an roi_id was provided
        if roi_id is not None:
            row = [row for row in self.all_roi_rows if row['id'] == roi_id]
            if not row:
                raise ValueError('ROI %s is not an ROI of FOV %s' % (roi_id, self.fov_id))
            roi_props = row.pop()['props']

        # append the ROI coords if roi_props exists
        # (we don't validate these, but we assume they correspond to 
        # (top_left_row, top_left_col, num_rows, num_cols))
        if kind in ['nrrd', 'tile'] and roi_props is not None:
            for coord in roi_props['xy_coords']:
                appendix = '%s-%04d' % (appendix, coord)

        # append the channel last, so that when sorting files,
        # the two channels of each FOV OR ROI remain adjacent to one another
        if channel is not None:
            if channel not in ['dapi', 'gfp', 'rgb']:
                raise ValueError("'%s' is not a valid channel" % channel)
            appendix = '%s-%s' % (appendix, channel.upper())

        # destination plate_dir name
        dst_plate_dir = self.dst_plate_dir()

        # construct the destination dirpath
        dst_dirpath = os.path.join(dst_root, kind, dst_plate_dir)
        if makedirs:
            os.makedirs(dst_dirpath, exist_ok=True)
        
        # construct the destination filename
        dst_filename = f'{dst_plate_dir}-{self.pml_id}-{self.well_id}-{self.site_id}-{self.target_name}_{appendix}.{ext}'
        return os.path.join(dst_dirpath, dst_filename)


    def load_raw_tiff(self, src_root):
        '''
        Convenience method to open and parse a raw TIFF and attempt to split it by channel
        Returns None if the file does not exist or cannot be split by channel
        '''
        src_filepath = self.src_filepath(src_root=src_root)
        if os.path.isfile(src_filepath):
            tiff = images.RawPipelineTIFF(src_filepath, verbose=False)
            tiff.parse_micromanager_metadata()
            tiff.validate_micromanager_metadata()
            tiff.split_channels()
            if tiff.did_split_channels:
                return tiff
            else:
                tiff.tiff.close()
    

    def process_raw_tiff(self, src_root, dst_root):
        '''
        Process a single raw TIFF
            1) parse the micromanager and other metadata
            2) split the tiff pages into DAPI and GFP channels
            3) generate z-projections

        src_root : the root of the 'PlateMicroscopy' directory
        dst_root : the destination 'oc-plate-microscopy' directory 

        NOTE: the `tiff.global_metadata` object returned by this method
        is modified by all of the `RawPipelineTIFF methods called below
        (including by `project_stack`, which appends the min/max intensities)
        '''

        src_filepath = self.src_filepath(src_root=src_root)
        metadata = {'src_filepath': src_filepath}
        if not os.path.isfile(src_filepath):
            metadata['error'] = 'File does not exist'

        tiff = images.RawPipelineTIFF(src_filepath, verbose=False)
        tiff.parse_micromanager_metadata()
        tiff.validate_micromanager_metadata()

        # attempt to split the channels and project
        tiff.split_channels()
        if tiff.did_split_channels:
            for channel in ['dapi', 'gfp']:
                dst_filepath = self.dst_filepath(
                    dst_root=dst_root, kind='proj', channel=channel, ext='tif')
                tiff.project_stack(channel_name=channel, axis='z', dst_filepath=dst_filepath)

        # the tiff file must be manually closed
        tiff.tiff.close()

        metadata.update(tiff.global_metadata)

        # return the parsed raw TIFF metadata and the parsing events (if any)
        result = {'metadata': metadata, 'events': tiff.events}
        return result


    def calculate_fov_features(self, dst_root, fov_scorer):
        '''
        Calculate the features and score for the FOV
        using the PipelineFOVScorer module from the dragonfly-automation project

        dst_root : the root directory in which z-projections were saved in process_raw_tiff
        fov_scorer : an instance of PipelineFOVScorer in 'training' mode
        '''

        # construct the filepath to the DAPI z-projection
        filepath = self.dst_filepath(dst_root, kind='proj', channel='dapi', ext='tif')
        result = fov_scorer.process_existing_fov(filepath)
        return result


    def crop_corner_rois(self, src_root, dst_root):
        '''
        Crop a 600x600 ROI at each corner of the raw FOV

        At the same time, crop around the cell layer in z,
        downsample the intensities from uint16 to uint8,
        and save each ROI as a tiled PNG
        '''

        fov_size = 1024
        roi_size = 600
        left_ind = 0
        right_ind = fov_size - roi_size

        # the top and bottom of the cell layer, relative to its center, in microns
        # (these are empirical estimates/guesses)
        cell_layer_bottom = -7
        cell_layer_top = 7

        # the step size of the final stack
        # (this is set to correspond to the xy pixel size,
        # so that the voxels of the resampled stack will be isotropic)    
        target_step_size = 0.2

        # the number of slices the final stack must have
        required_num_slices = (cell_layer_top - cell_layer_bottom)/target_step_size

        all_roi_props = []

        # attempt to load and split the TIFF
        tiff = self.load_raw_tiff(src_root)
        if tiff is None:
            raise ValueError('Raw TIFF file for fov %s does not exist' % self.fov_id)
    
        # the z coords of the cell layer (calculated using the entire FOV)
        abs_bottom_ind, abs_top_ind, center_ind = self.find_cell_layer(
            tiff.stacks['dapi'], 
            rel_bottom=cell_layer_bottom, 
            rel_top=cell_layer_top,
            step_size=self.z_step_size())

        # the shape of each ROI
        roi_shape = (roi_size, roi_size, abs_top_ind - abs_bottom_ind)

        # the position of the top left corner of each of the ROIs
        roi_top_left_positions = [
            (left_ind, left_ind, abs_bottom_ind),
            (left_ind, right_ind, abs_bottom_ind),
            (right_ind, left_ind, abs_bottom_ind),
            (right_ind, right_ind, abs_bottom_ind)
        ]

        for roi_position in roi_top_left_positions:

            num_rows, num_cols, num_z = roi_shape
            row_ind, col_ind, z_ind = roi_position
        
            # construct the ROI props
            roi_props = {
                'position': roi_position, 
                'shape': roi_shape,
                'center': center_ind,
                'xy_coords': (row_ind, col_ind, num_rows, num_cols),
            }

            for channel in ['dapi', 'gfp']:
                dst_filepath = self.dst_filepath(
                    dst_root, 
                    kind='nrrd', 
                    channel=channel, 
                    roi_props=roi_props, 
                    ext='nrrd')

                # crop the raw stack
                cropped_stack = tiff.stacks[channel][
                    z_ind:(z_ind + num_z), row_ind:(row_ind + num_rows), col_ind:(col_ind + num_cols)]

                cropped_stack = cropped_stack.copy()

                # resample the stack so that it has the required step size and number of slices         
                cropped_stack, did_resample_stack = self.resample_stack(
                    cropped_stack, 
                    actual_step_size=self.z_step_size(),
                    target_step_size=target_step_size, 
                    required_num_slices=required_num_slices)

                # the did_resample_stack flag will always be the same for both channels
                roi_props['stacks_resampled'] = did_resample_stack

                # downsample the pixel intensities from uint16 to uint8
                cropped_stack, min_intensity, max_intensity = self.stack_to_uint8(
                    cropped_stack, percentile=0.01)
                
                # log the black and white points used to downsample the intensities
                roi_props['min_intensity_%s' % channel] = min_intensity
                roi_props['max_intensity_%s' % channel] = max_intensity

                # save the stack itself
                # TODO: what to do when the file already exists?
                if not os.path.isfile(dst_filepath):
                    nrrd.write(dst_filepath, cropped_stack)

            all_roi_props.append(roi_props)
    
        return all_roi_props


    def crop_best_roi(self, src_root, dst_root):
        '''
        Find and crop the ROI with the highest ROI score
        '''
        pass


    def generate_ijclean(self, src_root, dst_root):
        '''
        Append the IJMetadata tags to the raw tiff so that it can be opened in ImageJ
        with the correct psuedocolors and black/white points
        '''
        # attempt to load and split the TIFF
        tiff = self.load_raw_tiff(src_root)
        if not tiff:
            return


    @staticmethod
    def find_cell_layer(stack, rel_bottom, rel_top, step_size):
        '''
        Find the top and bottom of the cell layer

        stack : a 3D numpy array with dimensions (z, x, y)
            (assumed to correspond to the DAPI channel)
        rel_bottom, rel_top : the position of the bottom and top of the cell layer,
            relative to the center of the cell layer, in microns

        '''

        # z-profile of the mean intensity in the Hoechst channel
        raw_profile = np.array([zslice.mean() for zslice in stack]).astype(float)
        profile = raw_profile - raw_profile.mean()
        profile[profile < 0] = 0
        profile /= profile.sum()

        # the index of the center of the cell layer
        # (defined as the median of the mean-subtracted mean intensity profile)
        center_ind = np.argwhere(np.cumsum(profile) > .5).min()

        # absolute position, in number of z-slices, of the top and bottom of the cell layer 
        # (rel_bottom_ind is assumed to be negative)
        abs_bottom_ind = int(max(0, center_ind + np.floor(rel_bottom/step_size)))
        abs_top_ind = int(min(len(profile) - 1, center_ind + np.ceil(rel_top/step_size)))

        return abs_bottom_ind, abs_top_ind, center_ind


    @staticmethod
    def resample_stack(stack, actual_step_size, target_step_size, required_num_slices):
        '''
        Resample and possibly crop or pad a z-stack so that it has the specified step size
        and number of z-slices

        stack : 3D numpy array with dimensions (x, y, z)
        actual_step_size : the z-step size of the original stack (in microns)
        target_step_size : the z-step size after resampling (in microns)
        required_num_slices : the number of z-slices the resampled stack must have
        '''
    
        did_resample_stack = False

        # move the z dimension from the first to the last axis
        stack = np.moveaxis(stack, 0, -1)

        # resample z to generate isotropic voxels
        if actual_step_size != target_step_size:
            did_resample_stack = True
            z_scale = actual_step_size/target_step_size
            stack = skimage.transform.rescale(
                stack, (1, 1, z_scale), multichannel=False, preserve_range=True)

        # pad or crop the stack in z so that there are the required number of slices
        num_rows, num_cols, num_slices = stack.shape
        if num_slices < required_num_slices:
            pad = np.zeros((num_rows, num_cols, required_num_slices - num_slices)).astype(stack.dtype)
            stack = np.concatenate((stack, pad), axis=2)

        elif num_slices > required_num_slices:
            num_extra = num_slices - required_num_slices
            crop_ind = int(np.floor(num_extra/2))
            if np.mod(num_extra, 2) == 0:
                stack = stack[:, :, crop_ind:-crop_ind]
            else:
                stack = stack[:, :, crop_ind:-(crop_ind + 1)]

        return stack, did_resample_stack


    @staticmethod
    def stack_to_uint8(stack, percentile):
        '''
        Downsample the raw uint16 pixel intensities to uint8
        and return the black and white points used to do so
        '''
            
        stack = stack.astype(float)
        minn, maxx = np.percentile(stack, (percentile, 100 - percentile))
        if minn == maxx:
            maxx = minn + 1
            
        stack -= minn
        stack[stack < minn] = 0
        stack /= (maxx - minn)
        stack[stack > 1] = 1
        
        stack = (255*stack).astype('uint8')
        return stack, int(minn), int(maxx)


