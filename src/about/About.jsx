
import React, { Component } from 'react';
import classNames from 'classnames';
import { Button } from "@blueprintjs/core";

import 'tachyons';
import 'react-table/react-table.css';
import "@blueprintjs/core/lib/css/blueprint.css";

import settings from '../common/settings.js';
import * as utils from '../common/utils.js';

import '../common/common.css';
import '../profile/Profile.css';
import '../about/About.css';


export default function About (props) {
    return (
        <div className='w-90 pa4 f5' style={{minWidth: '1200px'}}>


            {/* first row - logo and welcome blurb */}
            <div className='w-100 flex items-center'>

                {/* large opencell logo */}
                <div className='' style={{width: '220px'}}>
                    <img src='/assets/images/opencell_logo_v2.png'/>
                </div>

                {/* welcome blurb */}
                <div className='w-70 pl5'>
                    <div className='w-100 f2'>Welcome to OpenCell!</div>
                    <div className='w-100 pt2'>
                        <p>
                        OpenCell is a collection of localization and interactome measurements
                        for human proteins. It is a collaboration between the Leonetti group
                        at the Chan Zuckerberg Biohub and the Mann lab at the Max Plank Institute
                        for Biochemistry, along with many other colleagues. 
                        </p>
                        <p>
                        This project is still under development. Thanks for being an alpha tester!
                        We ask that you keep in mind a few important points:
                        </p>
                        <ul>
                            <li>
                            Please keep our data confidential and do not share login credentials.
                            </li>
                            <li>
                            At the moment, the website is best viewed in a wide browser window on a laptop or desktop.
                            </li>
                            <li>
                            We need your feedback! Write to us at opencell at czbiohub.org 
                            to tell us what you like or dislike.
                            </li>
                        </ul>
                    </div>
                </div>
            </div>


            {/* second row - things to know about the data */}
            <div className='w-100 pt3'>
                <div className='w-100 f3 bb b--black-30'>About the data</div>

                <div className='w-100 f6 pt2 flex items-center'>

                    <div className='about-item-container' style={{flex: '1 1 20%'}}>
                        <div className='about-item-icon-container'>
                            <img src='/assets/images/cells_icon.png'/>
                        </div>
                        <div className='about-item-caption'>
                            All of our endogenous tags are in the <b>HEK293T</b> human cell line
                        </div>
                    </div>

                    <div className='about-item-container' style={{flex: '1 1 35%'}}>
                        <div className='about-item-icon-container'>
                            <img src='/assets/images/crispr_icon.png'/>
                            <img src='/assets/images/sfp_tagging_icon.png'/>
                        </div>
                        <div className='about-item-caption'>
                            <p>
                                Using CRISPR, we endogenously tag our target proteins 
                                with split-mNeonGreen2 (PMID 28851864).
                            </p>
                            <p>
                                Whenever possible, we use existing literature or 3D protein structures 
                                to determine the tag insertion site (N- or C-terminus). 
                            </p>
                        </div>
                    </div>

                    <div className='about-item-container' style={{flex: '1 1 22%'}}>
                        <div className='about-item-icon-container'>
                            <img src='/assets/images/microscope_icon.png'/>
                        </div>
                        <div className='about-item-caption'>
                            All imaging is live-cell from a spinning-disk confocal microscope.
                        </div>
                    </div>

                    <div className='about-item-container' style={{flex: '1 1 22%'}}>
                        <div className='about-item-icon-container'>
                            <img src='/assets/images/mass_spec_icon.png'/>
                        </div>
                        <div className='about-item-caption'>
                            We use anti-mNeonGreen nanobody for immunoprecipitation and mass spectrometry.
                        </div>
                    </div>
                </div>
            </div>


            {/* third row - explanation of website pages */}
            <div className='w-100 pt4'>
                <div className='w-100 f3 bb b--black-30'>About this website</div>

                <div className='w-100 f6 pt3 flex items-center'>

                    <div className='about-item-container' style={{flex: '1 1 30%'}}>
                        <div className='about-item-screenshot-container'>
                            <img src='/assets/images/target_page.png'/>
                        </div>
                        <div className='about-item-caption'>
                            <b>The target page</b> shows the imaging and interactome data
                            for the 1,217 proteins that we have successfully tagged so far.
                        </div>
                    </div>

                    <div className='about-item-container' style={{flex: '1 1 30%'}}>
                        <div className='about-item-screenshot-container'>
                            <img src='/assets/images/interactor_page.png'/>
                        </div>
                        <div className='about-item-caption'>
                            <b>The interactor page</b> shows the interactome data for more than 4,000
                            additional proteins that we have not tagged but that are present in our mass spec datasets.
                        </div>
                    </div>

                    <div className='about-item-container' style={{flex: '1 1 30%'}}>
                        <div className='about-item-screenshot-container'>
                            <img src='/assets/images/gallery_page_small.jpg'/>
                        </div>
                        <div className='about-item-caption'>
                            <b>The gallery page</b> displays a tiled array of image thumbnails
                            representing all of the tagged proteins with a particular set of localization annotations.
                        </div>
                    </div>

                </div>
            </div>

        </div>
    );
};