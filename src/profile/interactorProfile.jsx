
import * as d3 from 'd3';
import React, { useState, useEffect, useLayoutEffect } from 'react';
import ReactDOM from 'react-dom';

import {
    BrowserRouter,
    Switch,
    Route,
    Redirect,
    useHistory, 
    useLocation, 
    useParams, 
    useRouteMatch
 } from "react-router-dom";

import { Button, Radio, RadioGroup, MenuItem } from "@blueprintjs/core";
import { Select } from "@blueprintjs/select";

import CellLineTable from './cellLineTable.jsx';
import { SectionHeader } from './common.jsx';

import 'tachyons';
import 'react-table/react-table.css';
import "@blueprintjs/core/lib/css/blueprint.css";

import CellLineMetadata from './cellLineMetadata.jsx';
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
            <div className="pl3 pr3">
                <div className="flex">
                    {/* Left column - about box and expression and facs plots*/}
                    <div className="pl2 pr4 pt0" style={{width: '450px'}}>

                        <CellLineMetadata data={data} isInteractor/>

                        {/* 'About' textbox */}
                        <div className='pb4'>
                            <SectionHeader title='About this protein'/>
                            <div className='pt2 about-this-protein-container'>
                                <p>{data.uniprot_metadata?.annotation}</p>
                            </div>
                        </div>
                    </div>

                    {/* table of all interacting targets */}
                    <div className="w-100 pl2 pt2 pb2">
                        <SectionHeader title='Interacting targets'/>
                        <CellLineTable 
                            cellLines={data.interacting_cell_lines}
                            onCellLineSelect={props.setCellLineId}
                        />
                    </div>
                </div>
            </div>

            {data.interacting_cell_lines ? (null) : (<div className='loading-overlay'/>)}
        </div>
    );
}



