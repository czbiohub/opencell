import React, { Component } from 'react';
import { H3, H4, H5 } from '@blueprintjs/core';

const microscopyHeader = (
    <div className='pa3 popover-container'>
        <p>
            Opencell targets are imaged in live cells in three dimensions using a spinning-disk confocal microscope. 
            Several options are available to control the way in which the images are displayed:
        </p>
        <H5>Display mode</H5>
        <p>
            In <b>z-projection</b> mode, the maximum-intensity projection through the z-stack (along the z-axis) is displayed.
            In <b>z-slice</b> mode, a single z-slice from the z-stack is displayed; the horizontal slider below the image viewer controls the index of the displayed z-slice and can therefore be used to 'scroll' through the z-stack.
            Finally, the <b>volume rendering</b> visualizes the entire z-stack at once using a three-dimensional volume rendering.
        </p>
        <H5>Channel selection</H5>
        <p>
            The <b>DNA</b> channel corresponds to the Hoechst staining used to label the DNA. 
            It is useful as a fiducial marker for the nucleus (and, within the nucleus, the chromatin itself).
            The <b>protein</b> channel corresponds to the signal from the fluorescently tagged protein.
            Finally, clicking the <b>'both'</b> button overlays the DNA staining (shown in blue) on the fluorescently tagged protein (shown in gray).
        </p>
    </div>
);

const aboutHeader = (
    <div className='pa3 popover-container'>
    <p>
        This textbox displays the functional annotation from UniprotKB for the currently selected opencell target.
    </p>
    </div>
);

const expressionLevelHeader = (
    <div className='pa3 popover-container'>
        <p>
        This scatterplot displays two different measurements of protein expression for all opencell targets. 
        On the x-axis, the fluorescence intensity of the tagged protein (measured by FACS) is displayed (in arbitrary fluorescence units).
        On the y-axis, the RNA abunance, in transcripts per million reads, is displayed. 
        <br></br><br></br>
        The currently selected opencell target is highlighted in blue. 
        </p>
    </div>
);

export default {
    microscopyHeader,
    aboutHeader,
    expressionLevelHeader,
}