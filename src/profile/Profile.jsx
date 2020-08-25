
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

import Overview from './overview.jsx';
import FovAnnotator from './fovAnnotator.jsx';
import CellLineTable from './cellLineTable.jsx';
import { SectionHeader } from './common.jsx';

import 'tachyons';
import 'react-table/react-table.css';
import "@blueprintjs/core/lib/css/blueprint.css";

import settings from '../common/settings.js';
import * as utils from '../common/utils.js';

import '../common/common.css';
import './Profile.css';


export default function Profile (props) {

    const [allCellLines, setAllCellLines] = useState([]);

    // load the metadata for all cell lines
    useEffect(() => {
        d3.json(`${settings.apiUrl}/lines`).then(lines => {
            setAllCellLines(lines);  
        });
    }, [])

    // this is hackish: we end up here only if the user clicked the back or forward buttons,
    // which means we do not want to push the new cellLineId to the history
    useEffect(() => {
        const cellLineIdFromUrl = parseInt(props.match.params.cellLineId);
        console.log(`Profile changing id from ${props.cellLineId} to ${cellLineIdFromUrl}`)
        props.setCellLineId(cellLineIdFromUrl, false);
    }, [props.match]);


    // debugging
    useEffect(() => {
        console.log(`Profile cellLineId is ${props.cellLineId} and cellLines.length is ${allCellLines.length}`)
    });


    const cellLine = allCellLines.filter(
        line => line.metadata?.cell_line_id === props.cellLineId
    )[0];

    if (allCellLines.length && !cellLine) {
        console.log(`No cell line found for cellLineId ${props.cellLineId}`);
    };

    if (!cellLine) return null;
        
    return (
        <div>
            {/* main container */}
            <div className="pl3 pr3" style={{width: '2000px'}}>

                {props.showFovAnnotator ? (
                    <FovAnnotator cellLineId={props.cellLineId} cellLine={cellLine}/>
                ) : (
                    <Overview
                        cellLine={cellLine}
                        cellLineId={props.cellLineId}
                        onSearchChange={() => {}}
                        onCellLineSelect={props.setCellLineId}
                        showTargetAnnotator={props.showTargetAnnotator}
                    />
                )}

                {/* table of all targets */}
                <div className="w-100 pl2 pt2 pb2">
                    <SectionHeader title='All cell lines'/>
                    <CellLineTable 
                        cellLines={allCellLines}
                        cellLineId={props.cellLineId}
                        onCellLineSelect={props.setCellLineId}
                    />
                </div>
            </div>

            {allCellLines.length ? (null) : (<div className='loading-overlay'/>)}
        </div>

    );
}



