
import React, { Component } from 'react';
import {Link} from 'react-router-dom';

export default function Navbar (props) {
    
    return (
        // main container
        <div>

        {/* 'space-between' left- and right-justifies the two children divs */}
        <div 
            className="flex items-center w-100 pr3 pl3 pt1 pb1" 
            style={{justifyContent: 'space-between', backgroundColor: "#eee"}}
        >

            {/* left-side content */}
            <div className="flex items-center">
                <div>
                    <img src='./logos/opencell_logo.png' width={70} height={70} style={{mixBlendMode: 'darken'}}/>
                </div>
                <div className="pl3 blue navbar-opencell-title">OpenCell</div>
            </div>

            {/* right-justified content */}
            <div className='flex items-center' style={{}}>

                <div className='pl3 pr3' style={{borderRight: '1px solid #aaa'}}>
                    <Link to='/'>Home</Link>
                </div>
                <div className='pl3 pr3' style={{borderRight: '1px solid #aaa'}}>
                    <Link to="/profile/401">Targets</Link>
                </div>
                <div className='pl3 pr3' style={{borderRight: '1px solid #aaa'}}>
                    <Link to="/fovs/401">FOVs</Link>
                </div>
                <div className='pl3 pr3' style={{borderRight: '1px solid #aaa'}}>
                    <Link to="/annotations/401">Annotations</Link>
                </div>
                <div className='pl3 pr3'>
                    <Link to="/gallery">Gallery</Link>
                </div>

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

