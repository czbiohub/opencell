
import React, { useState, useEffect, useContext } from 'react';
import {Link} from 'react-router-dom';
import settings from '../common/settings.js';

export default function Navbar (props) {
    const modeContext = useContext(settings.ModeContext);

    const publicNavbarLinks = [
        <div key='home' className='pl3 pr3' style={{borderRight: '1px solid #aaa'}}>
            <Link to='/'>Home</Link>
        </div>,
        <div key='target' className='pl3 pr3' style={{borderRight: '1px solid #aaa'}}>
            <Link to="/target/701">Targets</Link>
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
        <div>
        {/* 'space-between' left- and right-justifies the two children divs */}
        <div 
            className="flex items-center w-100 pr3 pl3" 
            style={{
                justifyContent: 'space-between', 
                backgroundColor: "#eee",
                minWidth: 1400,
            }}
        >
            {/* left-side content */}
            <div className="flex items-center">
                <div style={{flex: '1 1 100%', marginBottom: '-4px'}}>
                    <img 
                        width={785} 
                        height={50} 
                        style={{mixBlendMode: 'darken'}}
                        src='/assets/logos/oc_banner_transparent.png' 
                    />
                </div>
                <div className="pl3 blue navbar-opencell-title">OpenCell</div>
            </div>

            {/* right-justified content */}
            <div className='flex items-center'>
                {publicNavbarLinks}
                {modeContext==='private' ? privateNavbarLinks : null}
                <div className='pl3'>
                    <input 
                        type='text' 
                        className='navbar-search-textbox' 
                        defaultValue={''}
                        onKeyPress={(event) => {
                            if (event.charCode===13) {
                                props.handleGeneNameSearch(event.currentTarget.value);
                            }
                        }}
                        placeholder="Search for a protein"
                    />
                </div>
            </div>
        </div>
        </div>
    );
}

