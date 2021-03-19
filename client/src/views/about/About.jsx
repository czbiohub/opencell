
import React, { Component, useState } from 'react';
import classNames from 'classnames';
import { Button } from "@blueprintjs/core";

import 'tachyons';
import 'react-table/react-table.css';
import "@blueprintjs/core/lib/css/blueprint.css";

import CellGraphic from './CellGraphic.jsx';
import './About.scss';

const Link = props => <a className='about-page-link' target='_blank' href={props.href}>{props.children}</a>

const Lightbox = props => {

    const [visible, setVisible] = useState(false);
    const lightboxContainer = (
        <div className='lightbox-container' onClick={() => setVisible(false)}>
            <div className='pa3 bg-white br4'>
                <div className='w-100 f2 b tc'>{props.title}</div>
                {props.children}
            </div>
        </div>
    );
    const childContainer = (
        <div className={props.className} onClick={() => setVisible(true)}>{props.children}</div>
    );
    return visible ? lightboxContainer : childContainer;
};


export default function About (props) {
    return (
        <div className='w-100 pt4 pl5 pr5 f5' style={{minWidth: '1200px'}}>


            {/* first row - logo and welcome blurb */}
            <div className='w-100 flex items-center'>

                {/* large opencell logo - hard-coded width to match the SVG width */}
                <div className='pr5' style={{width: '300px'}}>
                    <CellGraphic/>
                    {/* <img src='/assets/images/opencell_logo_v2.png'/> */}
                </div>

                {/* welcome blurb */}
                <div className='w-60 pl3'>
                    <div className='w-100 f2'>About OpenCell</div>
                    <div className='w-100 pt2'>
                        <p>
                        OpenCell is a proteome-scale collection of localization and interactome measurements
                        for human proteins. It is a collaboration between
                        the <Link href='https://www.czbiohub.org/manuel-leonetti-intracellular-architecture/'>
                            Leonetti group
                        </Link> at
                        the Chan Zuckerberg Biohub and
                        the <Link href='https://www.biochem.mpg.de/mann'>Mann Lab</Link> at
                        the Max Plank Institute for Biochemistry, along with many other colleagues.
                        </p>

                        <ul className='about-page-bullets'>
                            <li>
                            At the moment, this website is best viewed using either Firefox or Chrome
                            in a wide browser window on a laptop or desktop computer screen.
                            </li>
                            <li>
                            We need your feedback! Write to us
                            at <Link href='mailto:opencell@czbiohub.org'>opencell@czbiohub.org</Link> to
                            tell us what you like or dislike.
                            </li>
                        </ul>
                        <p>
                        To get started, use the search box at the top right of the page to search
                        for a protein by name, or check out
                        the <a href='./target/701'>gallery page</a> to
                        see collections of tagged proteins filtered by subcellular localization categories.
                        </p>
                    </div>
                </div>
            </div>


            {/* second row - things to know about the data */}
            <div className='w-100 pt3'>
                <div className='w-100 f3 bb b--black-30'>About the data</div>

                <div className='w-100 f6 pt2 flex items-center'>

                    <div className='about-item-container' style={{flex: '1 1 20%'}}>
                        <div className='about-item-icon-container'>
                            <img src='/assets/images/icon_cells.png'/>
                        </div>
                        <div className='about-item-caption'>
                            All of our endogenous tags are in the <b>HEK293T</b> human cell line
                        </div>
                    </div>

                    <div className='about-item-container' style={{flex: '1 1 35%'}}>
                        <div className='about-item-icon-container'>
                            <img src='/assets/images/icon_crispr.png'/>
                            <img src='/assets/images/icon_sfp_tagging.png'/>
                        </div>
                        <div className='about-item-caption'>
                            <p>
                                Using CRISPR,
                                we <Link href='https://www.pnas.org/content/113/25/E3501'>endogenously tag</Link> our
                                target proteins
                                with <Link href='https://www.nature.com/articles/s41467-017-00494-8'>split-mNeonGreen<sub>2</sub></Link>.
                            </p>
                            <p>
                                Whenever possible, we use existing literature or 3D protein structures
                                to determine the tag insertion site (N- or C-terminus).
                            </p>
                        </div>
                    </div>

                    <div className='about-item-container' style={{flex: '1 1 22%'}}>
                        <div className='about-item-icon-container'>
                            <img src='/assets/images/icon_microscope.png'/>
                        </div>
                        <div className='about-item-caption'>
                            All images are of <b>living cells</b> and were acquired
                            using a spinning-disk confocal microscope with a 63x 1.45NA objective.
                        </div>
                    </div>

                    <div className='about-item-container' style={{flex: '1 1 22%'}}>
                        <div className='about-item-icon-container'>
                            <img src='/assets/images/icon_mass_spec.png'/>
                        </div>
                        <div className='about-item-caption'>
                            We use an anti-mNeonGreen nanobody for immunoprecipitation and mass spectrometry.
                        </div>
                    </div>
                </div>
            </div>


            {/* third row - explanation of website pages */}
            <div className='w-100 pt4'>
                <div className='w-100 f3 bb b--black-30'>About this website</div>

                <div className='w-100 f6 pt3 flex items-center'>

                    <div className='about-item-container' style={{flex: '1 1 30%'}}>
                        <Lightbox className='about-item-screenshot-container' title='Target page'>
                            <img src='/assets/images/2020-11-13-opencell-guide-target-page.jpeg'/>
                        </Lightbox>
                        <div className='about-item-caption'>
                            <b>The target page</b> shows all of the imaging and interactome data
                            for a selected OpenCell target.
                        </div>
                    </div>

                    <div className='about-item-container' style={{flex: '1 1 30%'}}>
                        <Lightbox className='about-item-screenshot-container' title='Interactor page'>
                            <img src='/assets/images/2020-11-13-opencell-guide-interactor-page.jpeg'/>
                        </Lightbox>
                        <div className='about-item-caption'>
                            <b>The interactor page</b> shows the interactome data for more than 4,000
                            additional proteins that we have not tagged but that are present in our mass spec datasets.
                        </div>
                    </div>

                    <div className='about-item-container' style={{flex: '1 1 30%'}}>
                        <Lightbox className='about-item-screenshot-container' title='Gallery page'>
                            <img src='/assets/images/2020-11-13-opencell-guide-gallery-page.jpeg'/>
                        </Lightbox>
                        <div className='about-item-caption'>
                            <b>The gallery page</b> displays a tiled array of image thumbnails
                            representing all of the tagged proteins in OpenCell,
                            filtered by a user-selected set of localization annotations.
                        </div>
                    </div>

                </div>
            </div>

        </div>
    );
};
