
import * as d3 from 'd3';
import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom';

import CellLineTable from './cellLineTable.jsx';
import { SectionHeader } from './common.jsx';

import 'tachyons';
import 'react-table/react-table.css';
import "@blueprintjs/core/lib/css/blueprint.css";

import { CellLineMetadata, ExternalLinks } from './cellLineMetadata.jsx';
import MassSpecNetworkContainer from './massSpecNetworkContainer.jsx';
import settings from '../common/settings.js';
import * as utils from '../common/utils.js';

import '../common/common.css';
import './Profile.css';


export default function InteractorProfile (props) {

    const [data, setData] = useState({});

    // load the metadata for the interactor
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
                <div className="w-20 pl2 pr2">

                    <CellLineMetadata data={data} isInteractor/>

                    {/* 'About' textbox */}
                    <div className='pb4'>
                        <SectionHeader title='About this protein'/>
                        <div className='pt2 about-this-protein-container'>
                            <p>{data.uniprot_metadata?.annotation}</p>
                        </div>
                    </div>

                    <ExternalLinks data={data}/>
                </div>

                {/* table of all interacting targets */}
                <div className="w-40 pt4 pl2">
                    <SectionHeader title='Interaction network'/>
                    <MassSpecNetworkContainer
                        width={500}
                        height={500}
                        idType='ensg'
                        id={props.match.params.ensgId}
                        handleGeneNameSearch={props.handleGeneNameSearch}
                    />
                </div>
                <div className="w-40 pt4 pl2">
                    <SectionHeader title='Interacting targets'/>
                    <CellLineTable 
                        defaultPageSize={20}
                        cellLines={data.interacting_cell_lines}
                        onCellLineSelect={props.setCellLineId}
                    />
                </div>
            </div>
        {data.interacting_cell_lines ? (null) : (<div className='loading-overlay'/>)}
        </div>
    );
}



