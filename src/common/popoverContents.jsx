import React, { Component } from 'react';
import { H3, H4, H5 } from '@blueprintjs/core';

const VSpace = props => <div style={{'height': '15px', width: '100%'}}/>;

export const aboutThisProteinHeader = (
    <div className='popover-container-small'>
    <p>
    This is the functional annotation from UniprotKB for the currently selected protein.
    </p>
    </div>
);

export const expressionLevelHeader = (
    <div className='popover-container-large'>
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
    <div className='popover-container-large'>
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
    <div className='popover-container-small'>
    <p>
        The <b>'DNA' channel</b> shows the DNA stain (Hoechst) used to label the DNA and visualize the nuclei.
        <VSpace/>
        The <b>'Protein' channel</b> shows the signal from the mNeonGreen-tagged protein.
        <VSpace/>
        When <b>both channels</b> are selected, the Hoechst staining is overlaid in blue 
        on the mNeonGreen signal (which is shown in gray). 
    </p>
    </div>
);

export const microscopyImageQuality = (
    <div className='popover-container-small'>
    <p>
        In <b>'auto' mode</b>, the images are heavily compressed to ensure fast loading times.
        Compression artifacts may be visible in some images on this setting. 
        <VSpace/>
        In <b>'high' mode</b>, the images are lightly compressed to preserve image quality 
        at the expense of longer loading times.
    </p>
    </div>
);

export const _ = (
    <div className='popover-container-small'>
    <p>
        
        <VSpace/>
        
    </p>
    </div>
);


export const interactionNetworkHeader = (
    <div className='popover-container-small'>
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
        <VSpace/>
        
    </p>
    </div>
);
