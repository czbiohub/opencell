
import React, { Component } from 'react';


export default class Navbar extends Component {

    constructor (props) {
        super(props);
    }
    
    render () {

        return (
            // main container
            <div>

            {/* full-bleed navbar */}
            <div className="w-100 pa2 bg-black-10 f3">
                <div className='dib f3 pr4'>OpenCell v0.0.1</div>

                {/* mock navbar links */}
                <div className='fr pt2 dib f5'>
                    <div className='dib pl3 pr3' style={{borderRight: '1px solid #aaa'}}>
                        <a href="./">Home</a>
                    </div>
                    <div className='dib pl3 pr3' style={{borderRight: '1px solid #aaa'}}>
                        <a href="./dashboard">Dashboard</a>
                    </div>
                    <div className='dib pl3 pr3'>
                        <a href="./profile">Profile</a>
                    </div>

                </div>
            </div>
            </div>
        );
    }
}

