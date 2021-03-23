import React, { Component } from 'react';
import { H3, H4, H5 } from '@blueprintjs/core';
import { LocalizationAnnotation } from './localizationAnnotations.jsx';

import './popoverContents.css';


const VSpace = props => <div style={{'height': '15px', width: '100%'}}/>;

const aboutThisProteinHeader = (
    <div className='popover-container-narrow'>
    <p>
    This is the functional annotation from UniprotKB for the currently selected protein.
    </p>
    </div>
);

const localizationHeader = (
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

const expressionLevelHeader = (
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

const cellLineTableHeader = (
    <div className='popover-container-wide'>
        <p>
        This table lists all of the ~1200 genes that have been successfully tagged as part of OpenCell.
        </p><p>
        Click on a column header to sort the table by the values in that column,
        and use the textbox below each column header to search within that column.
        </p><p>
        The 'Expression' column corresponds to the expression level in HEK293T cells,
        measured using RNAseq.
        </p>
    </div>
);

const microscopyHeader = (
    <div className='popover-container-wide'>
        <p>
            Opencell targets are imaged in live cells using a spinning-disk
            confocal microscope and a 63x high-NA objective.
            Cells are imaged in 3D by acquiring a stack of 2D confocal slices
            to compose a three-dimensional image of the cell layer.
            There are three different ways of visualizing these 3D images:
        </p><p>
            <b>2D projection mode</b>: this mode displays the maximum-intensity projection
            through the stack of confocal slices (along the z-axis).
            It provides a quick overview of the full 3D image.
        </p><p>
            <b>2D slice mode</b>: this mode displays a single confocal slice from the stack.
            Use the horizontal slider below the image viewer to scroll through the slices in the stack.
        </p><p>
            <b>3D rendering:</b> this mode displays the full 3D image using a volume rendering.
            This kind of rendering reveals the 3D structure in the image by displaying bright regions in the image
            as partially opaque 3D shapes. The degree of transparency is proportional to the intensity;
            black (bakground) regions are completely transparent.
        </p>
    </div>
);

const microscopyChannel = (
    <div className='popover-container-narrow'>
    <p>
        Select the imaging channel to display.
    </p>
    <p>
        The <b>nucleus</b> channel shows the signal from the Hoechst stain used to label the DNA.
    </p><p>
        The <b>target</b> channel shows the signal from the split-mNeonGreen-tagged protein.
    </p><p>
        When the <b>'both channels'</b> option is selected,
        the nucleus channel (Hoechst staining) is overlaid in blue
        on top of the target channel (split-mNeonGreen signal), which is shown in gray.
    </p>
    </div>
);

const microscopyImageQuality = (
    <div className='popover-container-narrow'>
    <p>
        Select the quality of the 3D images.
    </p><p>
        When the quality is set to <b>auto</b>,
        the images are substantially compressed to ensure fast loading times.
        Compression artifacts will be visible in some images on this setting.
    </p><p>
        When the quality is set to <b>high</b>, the images are lightly compressed
        to preserve image quality, but at the expense of longer loading times.
    </p>
    </div>
);

const microscopyFovSelection = (
    <div className='popover-container-narrow'>
    <p>
        Select the image to view from among all available images of the selected target.
        Each image represents a different position, or field of view (FOV), on the microscope.
    </p>
    </div>
);

const interactionNetworkHeader = (
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

const scatterplotsHeader = (
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
    The <b>cellular abundance stoichiometry</b> (on the y-axis) corresponds to the abundance ratio from expression
    in the whole cell. The shaded circle in the plot is the 'core-complex zone,'
    determined empirically to be enriched for stable protein interactions.
    </p><p>
    Please note that, for some targets, <b>no data</b> is displayed in this tab. This occurs for targets
    that do not have their own IP-MS (immunoprecipitation-mass spectrometry) dataset yet.
    For these targets, the interaction network is derived from the IP-MS data for all other OpenCell targets.
    </p><p>
    Additionally, because the interaction stoichiometry values are normalized to the target,
    if the target was not detected in its own pull-down,
    the stoichiometry calculations are impossible and no data can be displayed in the stoichiometry scatterplot.
    </p>
    </div>
);

const interactionTableHeader = (
    <div className='popover-container-wide'>
    <p>
    This table summarizes the quantitative properties of each interaction involving the selected target.
    For each interaction, the <b>bait</b> column corresponds to the name of the tagged protein
    that was pulled down and the <b>prey</b> column corresponds to the interacting protein
    that was detected in that pull-down.
    Note that an OpenCell target can appear either as a bait or as a prey (or both) in the interactors table.
    </p><p>
    The quantitative columns include the <b>p-value</b> (-log10) and the <b>relative enrichment </b>
    from the volcano plot, as well as the <b>cellular abundance stoichiometry</b>
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

// unwritten popovers
const sequencingHeader = null;
const galleryHeader = null;
const gallerySelectionMode = null;

const umapGridSize = null;
const umapMarkerType = null;
const umapSnapToGrid = null;


// template
const _ = (
    <div className='popover-container-narrow'>
    <p>
    </p>
    </div>
);


export {
    aboutThisProteinHeader,
    sequencingHeader,
    localizationHeader,
    expressionLevelHeader,
    cellLineTableHeader,

    microscopyHeader,
    microscopyChannel,
    microscopyFovSelection,
    microscopyImageQuality,

    interactionNetworkHeader,
    scatterplotsHeader,
    interactionTableHeader,

    galleryHeader,
    gallerySelectionMode,

    umapGridSize,
    umapSnapToGrid,
    umapMarkerType,
}
