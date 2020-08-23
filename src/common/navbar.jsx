
import React, { Component } from 'react';


export default class Navbar extends Component {

    constructor (props) {
        super(props);
    }
    
    render () {

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
                    <div className="pl3 blue header-opencell-title">OpenCell</div>
                </div>

                {/* right-justified content */}
                <div className='flex items-center' style={{}}>

                    <div className='pl3 pr3' style={{borderRight: '1px solid #aaa'}}>
                        <a href="./">Home</a>
                    </div>
                    <div className='pl3 pr3' style={{borderRight: '1px solid #aaa'}}>
                        <a href="./dashboard">Dashboard</a>
                    </div>
                    <div className='pl3 pr3'>
                        <a href="./profile">Profile</a>
                    </div>

                    <div className='pl3'>
                        <input 
                            type='text' 
                            className='header-search-textbox' 
                            defaultValue={''}
                            onKeyPress={(event) => {
                                if (event.charCode===13) {
                                    this.props.onSearchChange(event.currentTarget.value);
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
}

