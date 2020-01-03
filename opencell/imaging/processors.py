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
        raw_filepath):
        
        self.fov_id = fov_id
        self.pml_id = pml_id
        self.parental_line = parental_line
        self.imaging_round_id = imaging_round_id
        self.plate_id = plate_id
        self.well_id = well_id
        self.site_num = site_num
        self.raw_filepath = raw_filepath

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

        processor = cls(
            fov_id=fov.id,
            pml_id=fov.dataset.pml_id,
            parental_line=fov.cell_line.parent.name,
            imaging_round_id=fov.imaging_round_id,
            plate_id=plate_design.design_id,
            well_id=well_id,
            site_num=fov.site_num,
            raw_filepath=fov.raw_filename,
            target_name=crispr_design.target_name)

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
        ext=None, 
        makedirs=True):
        '''
        Construct the relative directory path and filename for a 'kind' of output file

        The path is of the form {kind}/{dst_plate_dir}
        dst_plate_dir is of the form 'czML0383-P0001-R01'
        dst_filename is of the form '{dst_plate_dir}-ML0123-A01-S01-CLTA_{kind}-{channel}'

        Returns dst_dirpath and the dst_filename as a tuple
        (so that dst_dirpath can be created if it doesn't exist)

        TODO: extend this method so that it can generate unique filenames
        for each ROI from the same FOV

        '''

        if dst_root is None:
            dst_root = ''

        kinds = ['metadata', 'proj', 'cropz', 'cropxy', 'nrrd']
        if kind not in kinds:
            raise ValueError('%s is not a valid destination kind' % kind)
        appendix = kind.upper()

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



    def crop_cell_layer(self, src_root, dst_root):
        '''
        Crop the raw z-stack around the cell layer
        '''
        
        src_filepath = self.src_filepath(src_root=src_root)
        result = {'src_filepath': src_filepath}
        if not os.path.isfile(src_filepath):
            result['error'] = 'src_filepath does not exist'
            return result

        # the depth (that is, width in z) of the cropped stack in um
        crop_width = 13

        # half the depth in number of z-slices
        crop_width = np.ceil(crop_width/self.z_step_size()/2)

        src_tiff = images.RawPipelineTIFF(src_filepath, verbose=False)
        src_tiff.parse_micromanager_metadata()
        src_tiff.validate_micromanager_metadata()

        # attempt to split the channels and project
        src_tiff.split_channels()
        if not src_tiff.did_split_channels:
            src_tiff.tiff.close()
            result['error'] = 'Raw TIFF could not be split'
            return result
    
        # mean intensity in z of the Hoechst staining
        profile = np.array([zslice.mean() for zslice in src_tiff.stacks['dapi']]).astype(float)
        profile -= profile.mean()
        profile[profile < 0] = 0
        profile /= profile.sum()

        # the index of the center of the cell layer
        # (defined as the median of the mean-subtracted mean intensity profile)
        center_ind = np.argwhere(np.cumsum(profile) > .5).min()
        min_ind = int(max(0, center_ind - crop_width))
        max_ind = int(min(len(profile) - 1, center_ind + crop_width))

        # log the crop parameters
        result.update({
            'profile': profile,
            'min_ind': min_ind,
            'max_ind': max_ind,
            'center_ind': center_ind,
        })

        # do the crop
        for channel in ['dapi', 'gfp']:
            stack = src_tiff.stacks[channel]
            dst_filepath = self.dst_filepath(
                dst_root=dst_root, kind='cropz', channel=channel, ext='tif')
            dst_tiff_file = tifffile.TiffWriter(dst_filepath)
            for ind in np.arange(min_ind, max_ind + 1):
                dst_tiff_file.save(stack[ind, :, :])
            dst_tiff_file.close()

        src_tiff.tiff.close()
        return result


    def generate_nrrd(self, dst_root):
        '''
        Generate NRRD files for the website by cropping a 600x600 ROI
        from the cell-layer-cropped raw z-stacks

        NOTE: for now, we crop the center of each FOV
        '''

        result = {}
    
        # pixel size in microns
        # (for 1024x1024 images from the Dragonfly's EMCCD with 63x objective)
        pixel_size = 0.2

        roi_size = 600
        image_size = 1024
        min_xy_ind = int(image_size/2 - roi_size/2)
        max_xy_ind = int(image_size/2 + roi_size/2)
        
        # the number of z-slices that must be in each NRRD file
        num_nrrd_slices = 60

        for channel in ['dapi', 'gfp']:
        
            # the path to the cropped raw z-stack
            src_filepath = self.dst_filepath(
                dst_root=dst_root, kind='cropz', channel=channel, ext='tif')
            if not os.path.isfile(src_filepath):
                result['%s_error' % channel] = 'File does not exist'
                continue

            # the path to the nrrd file
            # TODO: include the coordinates of the crop like this: '-CROPXY-R000-C424'
            dst_filepath = self.dst_filepath(
                dst_root=dst_root, kind='nrrd', channel=channel, ext='nrrd')
            if os.path.isfile(dst_filepath):
                result['%s_error' % channel] = 'NRRD file already exists'
                continue

            stack = tifffile.imread(src_filepath)

            # crop the 600x600 ROI from the center of the FOV
            stack = stack[:, min_xy_ind:max_xy_ind, min_xy_ind:max_xy_ind]
            
            # move the z dimension from the first to the last axis
            stack = np.moveaxis(stack, 0, -1)

            # resample z to generate isotropic voxels
            if self.z_step_size() != pixel_size:
                z_scale = self.z_step_size()/pixel_size
                stack = skimage.transform.rescale(
                    stack, (1, 1, z_scale), multichannel=False, preserve_range=True)

            # pad or crop the stack in z so that there are the required number of slices
            num_slices = stack.shape[-1]
            if num_slices < num_nrrd_slices:
                pad = np.zeros((roi_size, roi_size, num_nrrd_slices - num_slices)).astype(stack.dtype)
                stack = np.concatenate((stack, pad), axis=2)

            elif num_slices > num_nrrd_slices:
                num_extra = num_slices - num_nrrd_slices
                crop_ind = int(np.floor(num_extra/2))
                if np.mod(num_extra, 2) == 0:
                    stack = stack[:, :, crop_ind:-crop_ind]
                else:
                    stack = stack[:, :, crop_ind:-(crop_ind + 1)]

            # autogain
            # TODO: log the min/max used here
            stack = utils.autoscale(stack, percentile=0.01, dtype='uint8')

            # log the final stack shape
            result['%s_stack_shape' % channel] = list(stack.shape)

            # save the stack
            nrrd.write(dst_filepath, stack)

        return result


