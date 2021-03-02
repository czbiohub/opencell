
import * as d3 from 'd3';
import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom';
import {Callout} from '@blueprintjs/core';

import 'tachyons';
import 'react-table/react-table.css';
import "@blueprintjs/core/lib/css/blueprint.css";

import MassSpecContainer from '../../components/massSpecContainer.jsx';
import CellLineMetadataTable from '../../components/cellLineMetadataTable.jsx';
import ExternalLinks from '../../components/externalLinks.jsx';
import SectionHeader from '../../components/sectionHeader.jsx';
import settings from '../../settings/settings.js';


export default function InteractorProfile (props) {

    const [data, setData] = useState({});
    const [loaded, setLoaded] = useState(false);

    // load the metadata for the interactor
    // TODO: this request is only needed for the interactor's uniprot metadata, 
    // not for the interactors themselves (which are loaded in the MassSpecContainer)
    useEffect(() => {
        if (!props.match.params.ensgId) return;
        d3.json(`${settings.apiUrl}/interactors/${props.match.params.ensgId}`).then(data => {
            setData(data); 
            setLoaded(true); 
        }, error => setLoaded(true));
    }, [props.match]);

    return (
        <div>
            <div className='pl5 pr5 pt3 pb1 flex justify-center'>
                <div className='w-80'>
                    <Callout 
                        title='This is an OpenCell interactor page' 
                        intent='warning' 
                        showHeader={true}
                    >
                        This page represents a protein that has not yet been tagged as part of OpenCell.
                        The interaction network and list of interactors shown below 
                        consist <b>only</b> of the OpenCell targets that we have observed to interact 
                        with this protein; they are therefore necessarily incomplete. 
                    </Callout>
                </div>
            </div>

            {/* main container */}
            <div className="pl3 pr3 flex">

                {/* Left column */}
                <div className="w-25 pl2 pr2">
                    <CellLineMetadataTable data={data} isInteractor/>
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
                        geneName={data.metadata?.target_name}
                        handleGeneNameSearch={props.handleGeneNameSearch}
                    />
                </div>
            </div>
        {loaded ? (null) : (<div className='loading-overlay'/>)}
        </div>
    );
}



