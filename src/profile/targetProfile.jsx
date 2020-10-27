
import * as d3 from 'd3';
import React, { useState, useEffect, useContext } from 'react';

import { Button, Radio, RadioGroup, MenuItem } from "@blueprintjs/core";
import { Select } from "@blueprintjs/select";

import TargetProfileOverview from './targetProfileOverview.jsx';
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


export default function TargetProfile (props) {
    const modeContext = useContext(settings.ModeContext);
    const [allCellLines, setAllCellLines] = useState([]);

    // load the metadata for all cell lines
    useEffect(() => {
        const url = `${settings.apiUrl}/lines?publication_ready=${modeContext==='public'}`;
        d3.json(url).then(lines => setAllCellLines(lines));
    }, [])

    // update the cellLineId when the user clicks the back or forward buttons
    // (this effect also runs after calls to history.push)
    useEffect(() => {
        const cellLineIdFromUrl = parseInt(props.match.params.cellLineId);
        props.setCellLineId(cellLineIdFromUrl, false);
    }, [props.match]);

    const cellLine = allCellLines.filter(
        line => line.metadata?.cell_line_id === props.cellLineId
    )[0];

    if (allCellLines.length && !cellLine) {
        console.log(`No cell line found for cellLineId ${props.cellLineId}`);
    };

    if (!cellLine) return null;

    const pulldownId = cellLine.best_pulldown?.id;
    return (
        <div>
            {/* main container */}
            <div className="pl3 pr3" style={{width: '2000px'}}>
                {props.showFovAnnotator ? (
                    <FovAnnotator cellLineId={props.cellLineId} cellLine={cellLine}/>
                ) : (
                    <TargetProfileOverview
                        cellLine={cellLine}
                        cellLineId={props.cellLineId}
                        handleGeneNameSearch={props.handleGeneNameSearch}
                        onCellLineSelect={props.setCellLineId}
                        showTargetAnnotator={props.showTargetAnnotator}
                    />
                )}
            </div>

            {/* table of all targets */}
            <div className="w-100 pl2 pt2 pb2">
                <SectionHeader title='All OpenCell targets'/>
                <CellLineTable 
                    cellLines={allCellLines}
                    cellLineId={props.cellLineId}
                    onCellLineSelect={props.setCellLineId}
                />
            </div>

            {allCellLines.length ? (null) : (<div className='loading-overlay'/>)}
        </div>
    );
}



