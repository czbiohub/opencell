
import React, {Component} from 'react';

import FACSPlot from '../common/facsPlot.jsx';
import {metadataDefinitions} from './definitions.js';
import pipelineMetadata from './data/20190816_pipeline-metadata.json';


class Header extends Component {

    constructor (props) {
        super(props);
    }


    render () {

        const metadata = pipelineMetadata[this.props.targetName];

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
                        <img src='./logos/opencell_logo.png' width={120} height={100}/>
                    </div>

                    {/* target name */}
                    <div className='fl dib'>
                        <div className="blue pt3" style={{fontSize: 66}}>{this.props.targetName}</div>
                    </div>

                      {/* stats */}
                    <div className='fl dib w-70 pt3 header-metadata'>
                        <ul>{metadataItems}</ul>
                    </div>

                    {/* FACS plot */}
                    {/* <div className='fl dib pl3' style={{marginTop: 0}}>
                        <div className='f6 black-70 w-100 tc'>FACS plot</div>
                        <FACSPlot 
                            width={100}
                            data={metadata.facs_histograms}/>
                    </div> */}
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