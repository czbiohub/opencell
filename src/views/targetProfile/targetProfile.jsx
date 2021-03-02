
import * as d3 from 'd3';
import React, { useState, useEffect, useContext } from 'react';

import TargetProfileOverview from './targetProfileOverview.jsx';
import FovAnnotator from './fovAnnotator.jsx';
import CellLineTable from '../../components/cellLineTable.jsx';
import SectionHeader from '../../components/sectionHeader.jsx';
import * as popoverContents from '../../components/popoverContents.jsx';
import settings from '../../settings/settings.js';

import 'tachyons';
import 'react-table/react-table.css';
import "@blueprintjs/core/lib/css/blueprint.css";
import './targetProfile.scss';


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

    let content;
    if (props.showFovAnnotator) {
        content = <FovAnnotator cellLineId={props.cellLineId} cellLine={cellLine}/>
    } else {
        content = (
            <TargetProfileOverview
                cellLine={cellLine}
                cellLineId={props.cellLineId}
                allCellLines={allCellLines}
                handleGeneNameSearch={props.handleGeneNameSearch}
                onCellLineSelect={props.setCellLineId}
                showTargetAnnotator={props.showTargetAnnotator}
            />
        );
    }

    const tableWidthClass = 'w-90'; //modeContext==='public'? 'w-70' : 'w-100';
    return (
        <div>
            {/* main container */}
            <div className="pl3 pr3" style={{width: '2000px'}}>
                {cellLine ? content : null}
            </div>

            {/* table of all targets */}
            <div className={'pl5 pr5 pt3 pb2 ' + tableWidthClass}>
                <SectionHeader 
                    title='All OpenCell targets' 
                    popoverContent={popoverContents.cellLineTableHeader}
                />
                <CellLineTable 
                    cellLines={allCellLines}
                    cellLineId={props.cellLineId}
                    onCellLineSelect={props.setCellLineId}
                    defaultPageSize={25}
                />
            </div>

            {allCellLines.length ? (null) : (<div className='f2 tc loading-overlay'>Loading...</div>)}
        </div>
    );
}



