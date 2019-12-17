
import React, {Component} from 'react';

import {metadataDefinitions} from './definitions.js';


class Header extends Component {

    constructor (props) {
        super(props);
    }


    render () {

        const headerDefs = ['protein_name', 'target_family', 'uniprot_id'];
        const metadataItems = metadataDefinitions.filter(def => headerDefs.includes(def.id)).map(def => {
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

                    <div className='fl dib w-25 pt0 pl3'>

                        {/* OpenCell graphic logo */}
                        <div className='fl dib w-30'>
                            <img src='./logos/opencell_logo.png' width={120} height={120}/>
                        </div>

                        {/* 'OpenCell' text header on top of the CZB logo */}
                        <div className='fl pl3 dib w-70' style={{marginTop: -15}}>
                            <div className="blue pt3 pb2 opencell-logo">{'OpenCell'}</div>
                            <img src='./logos/logo_text_smaller.png' width={'40%'}
                                    style={{verticalAlign: 'top', paddingLeft: 0}}
                                />
                        </div>
                    
                    </div>

                    <div className='fl dib w-75 pt3 pl3'>

                        {/* target name */}
                        <div className='fl dib'>
                            <div className="blue pt3" style={{fontSize: 66}}>{this.props.targetName}</div>
                        </div>

                        {/* stats */}
                        <div className='fl dib pt3 header-metadata'>
                            <ul>{metadataItems}</ul>
                        </div>

                        {/* target search text input */}
                        <div className='fr dib pt4 pr4'>
                            <input 
                                type='text' 
                                className='header-search-textbox' 
                                defaultValue={''}
                                onKeyPress={(event) => {
                                    if (event.charCode===13) {
                                        this.props.onSearchChange(event.currentTarget.value);
                                    }
                                }}/>
                            <div className='f5 header-search-label'>Search by target name</div>
                        </div>
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
            <div className='f5 header-metadata-label'>{props.label}</div>
        </li>
    );
}



export default Header;