import React, { Component } from 'react';
import { H3, H4, H5 } from '@blueprintjs/core';

import {LocalizationAnnotation} from '../profile/cellLineMetadata.jsx';

const VSpace = props => <div style={{'height': '15px', width: '100%'}}/>;

export const aboutThisProteinHeader = (
    <div className='popover-container-narrow'>
    <p>
    This is the functional annotation from UniprotKB for the currently selected protein.
    </p>
    </div>
);

export const localizationHeader = (
    <div className='popover-container-wide'>
    <p>
        These are protein localization categories determined by a human observer 
        from the fluorescence microscopy images. Each category is assigned one of three 'grades,'
        which are represented by the colored rectangles as follows:
    </p>
    <VSpace/>
    <div className="w-100">
        <LocalizationAnnotation name='Prominent signal' grade='3'/>
        <LocalizationAnnotation name='Clearly detectable signal' grade='2'/>
        <LocalizationAnnotation name='Detectable but subtle and/or weak signal' grade='1'/>
    </div>
    </div>
);

export const expressionLevelHeader = (
    <div className='popover-container-wide'>
        <H3>Expression level scatterplot</H3>
        <p>
        This scatterplot compares two different measurements of protein expression 
        for all opencell targets. 
        On the x-axis, the fluorescence intensity of the tagged protein (measured by FACS) 
        is displayed (in arbitrary fluorescence units).
        On the y-axis, the RNA abundance, in transcripts per million, is displayed. 
        <VSpace/>
        The currently selected opencell target is highlighted in blue. 
        </p>
    </div>
);

export const microscopyHeader = (
    <div className='popover-container-wide'>
        <p>
            Opencell targets are imaged in live cells in three dimensions using a spinning-disk 
            confocal microscope. Three different ways of visualizing these images are available.
            <VSpace/>
            <b>Z-projection mode</b>: the maximum-intensity projection through the z-stack 
            (along the z-axis) is displayed.
            <VSpace/>
            <b>Z-slice mode</b>: a single z-slice from the z-stack is displayed.
            The horizontal slider below the image controls position of the displayed z-slice 
            and can be used to 'scroll' through the z-stack.
            <VSpace/>
            <b>Volume rendering:</b> this visualizes the entire z-stack at once 
            using a three-dimensional volume rendering.
        </p>
    </div>
);

export const microscopyChannel = (
    <div className='popover-container-narrow'>
    <p>
        The <b>'DNA' channel</b> shows the signal from the Hoechst stain used to label the DNA.
        <VSpace/>
        The <b>'Protein' channel</b> shows the signal from the mNeonGreen-tagged protein.
        <VSpace/>
        When <b>both channels</b> are selected, the Hoechst staining is overlaid in blue 
        on the mNeonGreen signal, which is shown in gray.
    </p>
    </div>
);

export const microscopyImageQuality = (
    <div className='popover-container-narrow'>
    <p>
        In <b>'auto' mode</b>, the images are heavily compressed to ensure fast loading times.
        Compression artifacts will be visible in some images on this setting. 
        <VSpace/>
        In <b>'high-quality' mode</b>, the images are lightly compressed to preserve image quality 
        at the expense of longer loading times.
    </p>
    </div>
);

export const interactionNetworkHeader = (
    <div className='popover-container-wide'>
    <p>
        The protein-protein interaction network for the currently selected protein. 
        This network consists of all of the direct interactors of the selected protein 
        as well as the interactions between them. 
        <VSpace/>
        The node that represents the selected protein is shown in blue. 
        Bolded protein names indicate that the protein is an OpenCell target. 
        <VSpace/>
        Clicking on a protein navigates to the OpenCell page for that protein 
        (whether or not it has been tagged). 
        <VSpace/>
    </p>
    </div>
);

export const scatterplotsHeader = (
    <div className='popover-container-wide'>
    <p>
        
        <VSpace/>
        
    </p>
    </div>
);

export const interactionTableHeader = (
    <div className='popover-container-wide'>
    <p>
        
        <VSpace/>
        
    </p>
    </div>
);

export const _ = (
    <div className='popover-container-narrow'>
    <p>
        
        <VSpace/>
        
    </p>
    </div>
);
