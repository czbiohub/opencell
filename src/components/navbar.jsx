
import { Suggest } from '@blueprintjs/select';
import React, { useState, useEffect, useContext } from 'react';
import { useHistory } from 'react-router-dom';

import {Link} from 'react-router-dom';

import SearchBar from './searchBar.jsx';
import settings from '../settings/settings.js';
import './navbar.scss';


export default function Navbar (props) {

    const history = useHistory();
    const modeContext = useContext(settings.ModeContext);

    const publicNavbarLinks = [
        <div key='home' className='pl3 pr3' style={{borderRight: '1px solid #aaa'}}>
            <Link to='/'>Home</Link>
        </div>,
        <div key='target' className='pl3 pr3' style={{borderRight: '1px solid #aaa'}}>
            <Link to="/target">Targets</Link>
        </div>,
        <div key='gallery' className='pl3 pr3'>
            <Link to="/gallery">Gallery</Link>
        </div>
    ];

    const privateNavbarLinks = [
        <div key='fovs' className='pl3 pr3' style={{borderRight: '1px solid #aaa'}}>
            <Link to="/fovs/401">FOVs</Link>
        </div>,
        <div key='ants' className='pl3 pr3' style={{borderRight: '1px solid #aaa'}}>
            <Link to="/annotations/401">Annotations</Link>
        </div>
    ];

    return (
        // the 'justify-between' class here left- and right-justifies the two children divs
        <div className="flex items-center justify-between w-100 pr3 pl3 navbar-container">

            {/* left-side content */}
            <div className="flex items-center">
                <div style={{flex: '1 1 100%', marginBottom: '-4px'}}>
                    <img 
                        width={785} 
                        height={50} 
                        style={{mixBlendMode: 'darken'}}
                        src='/assets/images/oc_banner_transparent.png' 
                    />
                </div>
                <div className="pl3 blue navbar-opencell-title">OpenCell</div>
            </div>

            {/* right-side content */}
            <div className='flex items-center'>
                {publicNavbarLinks}
                {modeContext==='private' ? privateNavbarLinks : null}
                <div className='pl3'>
                    <SearchBar 
                        handleGeneNameSearch={props.handleGeneNameSearch}
                        history={history}
                    />
                </div>
            </div>

        </div>
    );
}

