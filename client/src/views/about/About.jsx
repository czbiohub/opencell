
import React, { Component, useState } from 'react';
import classNames from 'classnames';
import { Button } from "@blueprintjs/core";

import 'tachyons';
import 'react-table/react-table.css';
import "@blueprintjs/core/lib/css/blueprint.css";

import CellGraphic from './CellGraphic.jsx';
import './About.scss';


const Link = props => (
    <a className='about-page-link' target={props.new ? '_blank' : undefined} href={props.href}>{props.children}</a>
);


const Lightbox = props => {
    const [visible, setVisible] = useState(false);
    const lightboxContainer = (
        <div className='howto-lightbox-container' onClick={() => setVisible(false)}>
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


export function About (props) {
    return (
        <div className='w-100 pt4 pl5 pr5 pb3 f5 about-page-container' style={{minWidth: '1200px'}}>

            {/* first row - logo and welcome blurb */}
            <div className='w-100 flex items-center'>

                {/* large opencell logo - hard-coded width to match the SVG width */}
                <div className='pr5' style={{width: '300px'}}>
                    <CellGraphic/>
                </div>

                {/* welcome blurb */}
                <div className='w-60 pl3'>
                    <div className='w-100 f3'>About OpenCell</div>
                    <div className='w-100 pt2'>
                        <p>
                            OpenCell is a proteome-scale collection of protein localization and interaction measurements
                            for human proteins. It is a collaboration between
                            the <Link new href='https://www.czbiohub.org/manuel-leonetti-intracellular-architecture/'>
                                Leonetti group
                            </Link> at
                            the Chan Zuckerberg Biohub and
                            the <Link new href='https://www.biochem.mpg.de/mann'>Mann Lab</Link> at
                            the Max Plank Institute for Biochemistry.
                        </p>
                        <p>
                            The OpenCell dataset consists of confocal fluorescence microscopy images
                            and protein interactions detected by IP/MS experiments
                            for a library of 1,311 human proteins tagged endogenously using a CRISPR-based split-FP system.
                            This website provides an interactive way to visualize and access this dataset.
                            Please note that the site is best viewed using a modern web browser (e.g., Chrome or Firefox)
                            on a laptop or desktop computer.
                        </p>

                        <p>
                            There are a few ways to start using the site:
                        </p>
                        <ul className='about-page-bullets'>
                        <li>
                            Use the search box at the top right of the page
                            to search for a protein by name or keyword (e.g., 'ACTB' or 'actin')
                        </li>
                        <li>
                            Check out the <Link href='./gallery'>gallery page</Link> to
                            explore all of the tagged proteins in the dataset,
                            filtered by subcellular localization
                        </li>
                        <li>
                            Browser the complete list of tagged proteins <Link href='./target'>here</Link>
                        </li>
                        <li>
                            Read the <Link href='./howto'>how-to guide</Link> for
                            details about how to use the site and interpret the data
                        </li>
                        </ul>

                        <p className='b'>
                            We welcome feedback!
                            Please <Link href='./contact'>contact us</Link> to
                            tell us what you like or dislike.
                        </p>

                        <div className='pt3 w-100 flex justify-center see-more-link'>
                            <a target='_blank' href='https://www.biorxiv.org/'>
                                Check out our preprint for more information
                            </a>
                        </div>

                    </div>
                </div>
            </div>

            {/* second row - things to know about the data */}
            <div className='w-100 pt4'>
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
                                we <Link new href='https://www.pnas.org/content/113/25/E3501'>endogenously tag</Link> our
                                target proteins
                                with <Link new href='https://www.nature.com/articles/s41467-017-00494-8'>split-mNeonGreen<sub>2</sub></Link>.
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
                            using a spinning-disk confocal microscope with a 63x 1.47NA objective.
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

        </div>
    );
};


export function HowTo (props) {
    return (
        <div className='w-100 pt4 pl5 pr5 pb3 f5' style={{minWidth: '1200px'}}>
            <div className='w-100 f3 bb b--black-30'>How to use this website</div>

            <div className='w-100 f6 pt3 flex items-center'>
                <div className='howto-item-container' style={{flex: '1 1 30%'}}>
                    <Lightbox className='howto-item-screenshot-container' title='Target page'>
                        <img src='/assets/images/2020-11-13-opencell-guide-target-page.jpeg'/>
                    </Lightbox>
                    <div className='howto-item-caption'>
                        <b>The target page</b> shows all of the imaging and interactome data
                        for a selected OpenCell target.
                    </div>
                </div>

                <div className='howto-item-container' style={{flex: '1 1 30%'}}>
                    <Lightbox className='howto-item-screenshot-container' title='Interactor page'>
                        <img src='/assets/images/2020-11-13-opencell-guide-interactor-page.jpeg'/>
                    </Lightbox>
                    <div className='howto-item-caption'>
                        <b>The interactor page</b> shows the interactome data for more than 4,000
                        additional proteins that we have not tagged but that are present in our mass spec datasets.
                    </div>
                </div>

                <div className='howto-item-container' style={{flex: '1 1 30%'}}>
                    <Lightbox className='howto-item-screenshot-container' title='Gallery page'>
                        <img src='/assets/images/2020-11-13-opencell-guide-gallery-page.jpeg'/>
                    </Lightbox>
                    <div className='howto-item-caption'>
                        <b>The gallery page</b> displays a tiled array of image thumbnails
                        representing all of the tagged proteins in OpenCell,
                        filtered by a user-selected set of localization annotations.
                    </div>
                </div>

            </div>
        </div>
    );
};


export function Privacy (props) {
    return (
        <div className='w-100 pt4 flex justify-center about-page-container'>
            <div className='w-70'>
                <div className='w-100 f3 bb b--black-30'>OpenCell privacy policy</div>
                <div className='w-100 pt2'>
                    <p>

                    </p>
                </div>
            </div>
        </div>
    );
};



export function Contact (props) {
    return (
        <div className='w-100 pt4 flex justify-center about-page-container'>
            <div className='w-70'>
                <div className='w-100 f3 bb b--black-30'>Contact us</div>
                <div className='w-100 f5 pt2'>
                    <p>
                        OpenCell is a work in progress! We welcome comments, feedback, and bug reports.
                        We would also love to hear about how you are using our data,
                        and <b>especially if our data helped you to generate new biological hypotheses or insights. </b>
                    </p>

                    <p>There are a few ways to get in touch:</p>
                    <ul className='about-page-bullets'>
                        <li>Email us at <Link href='mailto:opencell@czbiohub.org'>opencell@czbiohub.org</Link></li>
                        <li>Follow us on <Link new href='https://twitter.com/OpenCellCZB'>Twitter</Link></li>
                        <li>Report bugs or suggest new features on <Link new href='https://github.com/czbiohub/opencell'>GitHub</Link></li>
                    </ul>

                </div>
            </div>
        </div>
    );
};
