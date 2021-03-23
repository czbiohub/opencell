import * as d3 from 'd3';
import React, { Component, useState, useEffect, useContext } from 'react';
import classNames from 'classnames';
import { Button } from "@blueprintjs/core";
import { useHistory, Link } from 'react-router-dom';

import 'tachyons';
import 'react-table/react-table.css';
import "@blueprintjs/core/lib/css/blueprint.css";

import SearchBar from '../../components/searchBar.jsx';
import settings from '../../settings/settings.js';
import { SimpleButton } from '../../components/buttonGroup.jsx';

import './Home.scss';

const Stat = props => {
    return (
        <div className='pr3'>
            <div className='f3 b black-80'>{props.value}</div>
            <div className='pt0 f6 black-30'>{props.label}</div>
        </div>
    );
}

const Thumbnail = props => {
    return (
        <div className='pr3 home-thumbnail-container'>
            <Link to={`/gallery?localization=${props.localizationCategory || props.label.toLowerCase()}`}>
                <img src={props.src}/>
                <div className='f5 b black-80'>{props.label}</div>
                <div className='pt0 f6 black-30'>{props.minorLabel}</div>
            </Link>
        </div>
    );
}


export default function Home (props) {
    const history = useHistory();
    const modeContext = useContext(settings.ModeContext);

    // remove blueprint-defined placeholder text in the suggest input elements
    useEffect(() => {d3.selectAll('input').attr('placeholder', '')}, []);

    return (
        <div className='pb3'>
        <div className='w-100 home-banner-container'>
            <img src='/assets/images/home_banner_color.png'/>
        </div>

        <div className='flex justify-center'>

        {/* main fix-width container */}
        <div className='home-container'>

        {/* top row - logo, title, search bar */}
        <div className='w-100 pt4 flex justify-center'>
            <div className='w-70'>

            <div className=''>
                <div className='home-title'>
                        <span>OpenCell</span>
                </div>

                <div className='pt0 pb3 home-title-caption'>
                    <span>
                        Proteome-scale measurements
                        of human protein localization and interactions
                    </span>
                </div>

                <div className='flex flex-row justify-around home-menu-container'>
                    <a href='./target'>Targets</a>
                    <a href='./gallery'>Gallery</a>
                    <a href='./'>How to</a>
                    <a href='./about'>About</a>
                </div>
            </div>

                {/* top row */}
                <div className='pt4 flex justify-center'>

                    <div className='w-30 flex justify-center home-logo-container'>
                        <img src='/assets/images/opencell_simpler_no_ribosome-with-labels.svg'/>
                    </div>

                    <div className='w-70 pl5'>

                        <div className='pt4 search-bar-container'>
                            <div className='search-bar-caption pb2'>Search for a protein</div>
                            <SearchBar
                                handleGeneNameSearch={props.handleGeneNameSearch}
                                history={history}
                            />
                            <div className='pt1 search-bar-hint'>
                                {'For example: '}
                                <a href='./target/828'>MAP4</a>{', '}
                                <a href='./target/701'>POLR2F</a>{', '}
                                <a href='./search/golgi'>Golgi</a>{', '}
                                <a href='./search/mediator%20complex'>mediator complex</a>{''}
                            </div>
                        </div>

                        <div className='pt4 flex justify-around'>
                            <Stat label='Tagged proteins' value={'1,311'}/>
                            <Stat label='Protein interactions' value={'25,212'}/>
                            <Stat label='3D images' value={'5,176'}/>
                        </div>

                    </div>

                </div>
            </div>
        </div>

        {/* bottom row - explore by localization */}
        <div className='w-100 pl6 pr6 pt4'>
            <div className='search-bar-caption'>
                Explore by protein localization
            </div>
            <div className='pt3 flex justify-between'>
                <Thumbnail
                    label='Nucleolus'
                    minorLabel='137 proteins'
                    localizationCategory='nucleolus_gc,nucleolus_fc_dfc'
                    src='/assets/images/home-thumbnails/NPM1.png'
                />
                <Thumbnail
                    label='Chromatin'
                    minorLabel='145 proteins'
                    src='/assets/images/home-thumbnails/H2BC21.png'
                />
                <Thumbnail
                    label='ER'
                    minorLabel='162 proteins'
                    src='/assets/images/home-thumbnails/BCAP31.png'
                />
                <Thumbnail
                    label='Golgi'
                    minorLabel='112 proteins'
                    src='/assets/images/home-thumbnails/GOLGA2.png'
                />
                <Thumbnail
                    label='Cytoskeleton'
                    minorLabel='60 proteins'
                    src='/assets/images/home-thumbnails/MAP4.png'
                />
                <Thumbnail
                    label='Membrane'
                    minorLabel='191 proteins'
                    src='/assets/images/home-thumbnails/RAC1.png'
                />
            </div>
            <div className='pt3 flex flex-row justify-center'>
                <div className='see-more-link'>
                    <a href='./gallery'>See all 18 localization categories on the gallery page</a>
                </div>
            </div>
        </div>

        </div>
    </div>
    </div>
    );
}
