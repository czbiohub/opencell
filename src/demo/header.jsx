
import React, {Component} from 'react';

import {metadataDefinitions} from './definitions.js';


class Header extends Component {

    constructor (props) {
        super(props);
    }


    render () {

        const metadataItems = metadataDefinitions.map(def => {
            return (
                <MetadataItem
                    key={def.Header}
                    value={def.accessor({targetName: this.props.targetName})}
                    label={def.Header}
                    units={def.units}
                />
            );
        });

        return (
            <div className="fl w-100 pt3 pb3">

                {/* main container with bottom border */}
                <div className="bb b--white" style={{overflow: 'hidden'}}>

                    {/* OpenCell logo */}
                    <div className='fl dib w-10'>
                        <img src='./logos/opencell_logo.png' width={100} height={100}/>
                    </div>

                    {/* target name */}
                    <div className='fl dib'>
                        <div className="blue pt3" style={{fontSize: 66}}>{this.props.targetName}</div>
                    </div>

                      {/* stats */}
                    <div className='fl dib w-70 pt3 header-metadata'>
                        <ul>{metadataItems}</ul>
                    </div>

                </div>
            </div>
        );
    }
}

function MetadataItem(props) {
    
    return (
        <li>
            <strong className='f3'>{props.value}</strong>
            <abbr className='f4' title='units description'>{props.units}</abbr>
            <div className='f5 label'>{props.label}</div>
        </li>
    );
}



export default Header;