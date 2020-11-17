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
        <p>
        This scatterplot compares two different measurements of protein expression 
        for all OpenCell targets. 
        On the x-axis, the fluorescence intensity of the tagged protein (measured by FACS)
        is plotted in arbitrary fluorescence units.
        On the y-axis, the RNA abundance in transcripts per million is plotted. 
        </p><p>
        The currently selected OpenCell target is highlighted in blue. 
        </p>
    </div>
);

export const microscopyHeader = (
    <div className='popover-container-wide'>
        <p>
            Opencell targets are imaged in live cells using a spinning-disk 
            confocal microscope with a 63x 1.45NA objective to acquire three-dimensional (z-stack) images. 
            Three different ways of visualizing these images are available.
        </p><p>
            <b>Z-projection mode</b>: the maximum-intensity projection through the z-stack 
            (along the z-axis) is displayed.
        </p><p>
            <b>Z-slice mode</b>: a single z-slice from the z-stack is displayed.
            The horizontal slider below the image controls position of the displayed z-slice 
            and can be used to 'scroll' through the z-stack.
        </p><p>
            <b>Volume rendering:</b> this visualizes the entire z-stack at once 
            using a three-dimensional volume rendering.
        </p>
    </div>
);

export const microscopyChannel = (
    <div className='popover-container-narrow'>
    <p>
        The <b>'Nucleus' channel</b> shows the signal from the Hoechst stain used to label the DNA.
    </p><p>
        The <b>'Target' channel</b> shows the signal from the mNeonGreen-tagged protein.
    </p><p>
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
    </p><p>
        In <b>'high-quality' mode</b>, the images are lightly compressed to preserve image quality 
        at the expense of longer loading times.
    </p>
    </div>
);

export const microscopyFovSelection = (
    <div className='popover-container-narrow'>
    <p>
        Select the image to view from among all available images of the selected target. 
        Each image represents a different position, or field of view (FOV), on the microscope. 
    </p><p>
        Please note that the five-digit number identifying each FOV 
        is not human-readable and is intended only for internal use. 
    </p>
    </div>
);

export const interactionNetworkHeader = (
    <div className='popover-container-wide'>
    <p>
        The protein-protein interactions for the selected target, displayed 
        as an <b>interactive</b> graph representation. 
    </p><p>
        Proteins are represented by <b>nodes</b> and significant interactions 
        between them are represented by <b>edges</b> between nodes (the light gray lines). 
        You can navigate to the page for any protein in the network by clicking on its node.  
    </p><p>
        The selected OpenCell target protein is labeled in blue, 
        and all of its direct interactions are shown. 
        Interactors in <b>bold</b> have themselves been tagged in OpenCell; all others have not. 
    </p><p>
        We use <a href='https://mcans.org/mcl/' target='_blank'> a type of unsupervised clustering</a> of 
        the whole interactome to group highly connected proteins 
        into <b>functional modules</b>. These are represented by the lightly shaded gray boxes. 
        Within these modules, <b>core complexes</b> are represented by the slightly darker shaded boxes.
        These core complex clusters are defined using high-stoichiometry interactions 
        (see the stoichiometry plots under the 'Scatterplots' tab for more details). 
    </p><p>
        Please note that large interactomes are hard to compactly arrange in two dimensions. 
        We are working on improving this; in the meantime, using the <b>'Re-run layout'</b> button 
        might improve readability for large networks. 
        Panning and zooming is also available (use <b>'Reset zoom'</b> to return to the default view). 
    </p>
    </div>
);

export const scatterplotsHeader = (
    <div className='popover-container-wide'>
    <p>
    Scatter plots contain quantitative information about each protein-protein interaction (PPI) we measured. 
    Each dot represents a protein (or group of homologs) that interacts with the currently selected OpenCell target. 
    Each plot is interactive (use <b>'Show labels'</b> to toggle dot labels on/off 
    and <b>Reset zoom</b> after panning or zooming).
    </p><p>
    <b>The volcano plot mode</b> represents a statistical definition of PPIs in pull-downs 
    of the selected target. 
    Each dot represents the relative enrichment of the interacting protein (on the x-axis)
    and its associated p-value (on the y-axis). 
    The enrichment value of each interactor is calculated relative to its enrichment 
    in hundreds of other OpenCell pulldowns, 
    and p-values are calculated from a t-test using triplicate observations of each interactor. 
    We defined statistically significant interactions using two thresholds for false discovery rate: 
    a very stringent 'major hit' threshold, and a more relaxed 'minor hit' threshold. 
    </p><p>
    <b>The stoichiometry plot mode</b> represents stoichiometry information of PPIs 
    as defined <a href='https://www.cell.com/cell/fulltext/S0092-8674(15)01270-2' target='_blank'>here</a>. 
    The <b>interaction stoichiometry</b> (on the x-axis) corresponds to the abundance ratio 
    of an interactor to that of the target protein in triplicate pull-downs.
    The <b>abundance stoichiometry</b> (on the y-axis) corresponds to the abundance ratio from expression 
    in the whole cell. The shaded circle in the plot is the 'core-complex zone,' 
    determined empirically to be enriched for stable protein interactions.
    </p><p>
    Please note that, for some targets, <b>no data</b> is displayed in this tab. These targets 
    do not have their own IP-MS (immunoprecipitation-mass spectrometry) experiment yet. 
    Rather, their interaction network is derived from the IP-MS data for all other OpenCell targets. 
    </p>
    </div>
);

export const interactionTableHeader = (
    <div className='popover-container-wide'>
    <p>
    This table summarizes the quantitative properties of each interaction involving the selected target. 
    For each interaction, the <b>bait</b> column corresponds to the name of the tagged protein 
    that was pulled down and the <b>prey</b> column corresponds to the interacting protein 
    that was detected in that pull-down. 
    Note that an OpenCell target can appear either as a bait or as a prey (or both) in the interactors table. 
    </p><p>
    The quantitative columns include the <b>p-value</b> (-log10) and the <b>relative enrichment </b>
    from the volcano plot, as well as the <b>abundance stoichiometry</b>
    and the <b>interaction stoichiometry</b> (both in log10) from the stoichiometry plot. 
    (for more details, refer to the scatterplot tab). 
    </p><p>
    When both interactors belong to the same functional module (the shaded boxes in 'Network' tab), 
    the module ID is specified as the 'Cluster ID'. These IDs are unique but not human-readable; 
    we are working on appending meaningful biological annotations to these clusters. 
    </p><p>
    Below the table, the <b>'Export table as CSV'</b> button allows you to download 
    the whole interactors table for the currently selected target as a CSV file. 
    </p>
    </div>
);

export const _ = (
    <div className='popover-container-narrow'>
    <p>
        
    </p><p>
        
    </p>
    </div>
);
