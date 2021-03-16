
import React, { Component, useState, useContext } from 'react';
import classNames from 'classnames';
import { Button } from "@blueprintjs/core";
import { useHistory } from 'react-router-dom';

import 'tachyons';
import 'react-table/react-table.css';
import "@blueprintjs/core/lib/css/blueprint.css";

import SearchBar from '../../components/searchBar.jsx';
import settings from '../../settings/settings.js';

import './Home.scss';


export default function Home (props) {
    const history = useHistory();
    const modeContext = useContext(settings.ModeContext);

    return (
        <div className='w-100 flex justify-center'>
            
            <div className='w-70 pt5'>

                {/* top row */}
                <div className='flex justify-center'>

                    <div className='logo-container'>
                        <img 
                            src='/assets/images/opencell_simpler_no_ribosome-with-labels.svg'
                            width={300}
                        />

                    </div>

                    <div className='title-search-container pl5'>

                        <div className='title'>
                            <span>Opencell</span>
                        </div>

                        <div className='title-caption'>
                            <span>
                                Proteome-scale measurements<br></br>of human protein localization and interactions
                            </span>
                        </div>

                        <div className='search-container'>
                            <SearchBar 
                                handleGeneNameSearch={props.handleGeneNameSearch}
                                history={history}
                            />
                        </div>

                        <div className='stats-container'>
                        </div>

                    </div>

                </div>

                {/* bottom row - localization categories */}
                <div className='explore-by-localization-container'>
                </div>
            </div>
        </div>
    );
}

