
import * as d3 from 'd3';
import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom';

import 'tachyons';
import 'react-table/react-table.css';
import "@blueprintjs/core/lib/css/blueprint.css";

import { CellLineMetadata, ExternalLinks } from './cellLineMetadata.jsx';
import { SectionHeader } from './common.jsx';
import MassSpecContainer from './massSpecContainer.jsx';
import settings from '../common/settings.js';
import * as utils from '../common/utils.js';

import '../common/common.css';
import './Profile.css';


export default function InteractorProfile (props) {

    const [data, setData] = useState({});

    // load the metadata for the interactor
    // TODO: this request is only needed for the interactor's uniprot metadata, 
    // not for the interactors themselves (which are loaded in the MassSpecContainer)
    useEffect(() => {
        if (!props.match.params.ensgId) return;
        d3.json(`${settings.apiUrl}/interactors/${props.match.params.ensgId}`).then(data => {
            setData(data);  
        });
    }, [props.match]);

    return (
        <div>
            {/* main container */}
            <div className="pl3 pr3 flex">

                {/* Left column */}
                <div className="w-25 pl2 pr2">
                    <CellLineMetadata data={data} isInteractor/>
                    <div className='pb4'>
                        <SectionHeader title='About this protein'/>
                        <div className='pt2 about-this-protein-container'>
                            <p>{data.uniprot_metadata?.annotation}</p>
                        </div>
                    </div>
                    <ExternalLinks data={data}/>
                </div>

                {/* right column - mass spec network/table */}
                <div className="w-75 pt4 pl3">
                    <MassSpecContainer
                        layout='columns'
                        ensgId={props.match.params.ensgId}
                        handleGeneNameSearch={props.handleGeneNameSearch}
                    />
                </div>
            </div>
        {data.interacting_cell_lines ? (null) : (<div className='loading-overlay'/>)}
        </div>
    );
}



