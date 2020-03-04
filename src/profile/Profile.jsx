
import * as d3 from 'd3';
import React, { Component } from 'react';
import ReactTable from 'react-table';

import { Button, Radio, RadioGroup, MenuItem } from "@blueprintjs/core";
import { Select } from "@blueprintjs/select";

import Slider from './slider.jsx';
import ButtonGroup from './buttonGroup.jsx';

import Navbar from '../common/navbar.jsx';
import Header from './header.jsx';

import ExpressionPlot from '../common/expressionPlot.jsx';
import FacsPlotContainer from './facsPlotContainer.jsx';
import ViewerContainer from './viewerContainer.jsx';
import VolcanoPlotContainer from './volcanoPlotContainer.jsx';
import AnnotationsForm from './annotations.jsx';

import 'tachyons';
import 'react-table/react-table.css';
import "@blueprintjs/core/lib/css/blueprint.css";

import metadataDefinitions from './metadataDefinitions.js';
import manualMetadata from '../demo/data/manual_metadata.json';
import uniprotMetadata from '../demo/data/uniprot_metadata.json';

import settings from '../common/settings.js';
import * as utils from '../common/utils.js';

import '../common/common.css';
import './Profile.css';


function SectionHeader (props) {
    return (
        <div className="bb b--black-10">
            <div className="f3 section-header">{props.title}</div>
        </div>
    );
}


class App extends Component {

    constructor (props) {
        super(props);

        this.state = {
            fovs: [],
            fovId: null,
            roiId: null,
            cellLineId: null,
            targetName: null,
            linesLoaded: false,
        };

        this.changeTarget = this.changeTarget.bind(this);
        this.onSearchChange = this.onSearchChange.bind(this);
        this.onCellLineSelect = this.onCellLineSelect.bind(this);

        this.cellLine = {};
        this.allCellLines = [];
        this.urlParams = new URLSearchParams(window.location.search);
    }


    changeTarget (cellLine) {
        // cellLine is the JSON object returned by the lines/ endpoint

        // check that the target has changed
        if (cellLine.metadata.cell_line_id===this.state.cellLineId) return;

        // the available FOVs are the top two 
        // (we assume the FOVs are sorted by score)
        const fovs = [cellLine.fovs[0], cellLine.fovs[1]];

        this.cellLine = cellLine;

        this.setState({
            cellLineId: cellLine.metadata.cell_line_id,
            targetName: cellLine.metadata.target_name,
            fovId: fovs[0].id,
            roiId: fovs[0].rois[0].id,
            fovs,
        });
    }


    onSearchChange (value) {
        // fired when the user hits enter in the header's target search text input
        // `value` is the value of the input

        const url = `${settings.apiUrl}/lines?target_name=${value}&kind=all`;
        d3.json(url).then(lines => {
            for (const line of lines) {
                if (line && line.fovs.length) {
                    this.changeTarget(line);
                    break;
                }
            }
        });
    }


    onCellLineSelect (cellLineId) {
        // fired when the user clicks on a row of the datatable
        // or otherwise selects a new cell line by its ID
        const url = `${settings.apiUrl}/lines/${cellLineId}?kind=all`;
        d3.json(url).then(line => {
            if (line) this.changeTarget(line);
        });
    }
    

    componentDidMount() {
        let url = `${settings.apiUrl}/lines?kind=scalars`;
        d3.json(url).then(lines => {
            this.allCellLines = lines;     
            this.setState({linesLoaded: true});
        });
        // initial target to display
        this.onSearchChange(this.urlParams.get('target') || 'LMNB1');
        
    }


    render() {

        // append gene_name to metadataDefinitions 
        // (used only for the table of all targets at the bottom)
        let tableDefs = [
            {   
                id: 'gene_name',
                Header: 'Gene name',
                accessor: row => row.metadata?.target_name,
            },
            ...metadataDefinitions,
        ];


        return (
            <div>

            <Navbar/>

            {/* main container */}
            <div className="w-100 pl4 pr4">

                {/* page header and metadata */}
                <Header cellLine={this.cellLine} onSearchChange={this.onSearchChange}/>

                {/* container for the three primary panels */}
                <div className="flex" style={{minWidth: '1600px'}}>

                    {/* Left column - about box and expression and facs plots*/}
                    <div className="w-25 pl3 pr4 pt0">

                        {/* 'About' textbox */}
                        <div className='pb4'>
                            <SectionHeader title='About this protein'/>
                            <div className='pt2 protein-function-container'>
                                <p>{uniprotMetadata[this.state.targetName]?.uniprot_function}</p>
                            </div>
                        </div>

                        {/* expression scatterplot*/}
                        <SectionHeader title='Expression level'/>
                        <div className="fl w-100 pb3 expression-plot-container">
                            <ExpressionPlot targetName={this.state.targetName}/>
                        </div>

                        {/* FACS plot */}
                        <SectionHeader title='FACS histograms'/>
                        <FacsPlotContainer cellLineId={this.state.cellLineId}/>
                    </div>


                    {/* Center column - sliceViewer and volumeViewer */}
                    {/* note the hard-coded width (because the ROIs are always 600px */}
                    <div className="pl3 pr3" style={{flexBasis: '650px'}}>
                        <SectionHeader title='Localization'/>
                        <ViewerContainer
                            fovs={this.state.fovs}
                            fovId={this.state.fovId}
                            roiId={this.state.roiId}
                            changeRoi={(roiId, fovId) => this.setState({roiId, fovId})}
                        />
                    </div>


                    {/* Right column - annotations or volcano plot */}
                    <div className="w-33 pl3 pb3">
                        {this.urlParams.get('annotations')!=='yes' ? (
                            <div>
                                <SectionHeader title='Interactions'/>
                                <VolcanoPlotContainer
                                    targetName={this.state.targetName}
                                    changeTarget={name => this.onSearchChange(name)}
                                />
                            </div>
                        ) : (
                            <div>
                                <SectionHeader title='Annotations'/>    
                                <AnnotationsForm 
                                    cellLineId={this.state.cellLineId} 
                                    fovIds={this.state.fovs.map(fov => fov.id)}
                                />
                            </div>
                        )}
                    </div>
                </div>


                {/* table of all targets */}
                <div className="w-90 pt0 pl4 pb5">
                    <SectionHeader title='All cell lines'/>
                    <div className='pt3 table-container'>
                    <ReactTable 
                        defaultPageSize={10}
                        showPageSizeOptions={true}
                        filterable={true}
                        columns={tableDefs}
                        data={this.allCellLines.map(line => {
                            return {...line, isActive: this.state.cellLineId===line.metadata.cell_line_id};
                        })}
                        getTrProps={(state, rowInfo, column) => {
                            const isActive = rowInfo ? rowInfo.original.isActive : false;
                            return {
                                onClick: () => this.onCellLineSelect(rowInfo.original.metadata.cell_line_id),
                                style: {
                                    background: isActive ? '#ddd' : null,
                                    fontWeight: isActive ? 'bold' : 'normal'
                                }
                            }
                        }}
                        getPaginationProps={(state, rowInfo, column) => {
                            return {style: {fontSize: 16}}
                        }}
                        defaultFilterMethod={(filter, row, column) => {
                            // force default filtering to be case-insensitive
                            const id = filter.pivotId || filter.id;
                            const value = filter.value.toLowerCase();
                            return row[id] !== undefined ? String(row[id]).toLowerCase().startsWith(value) : true
                        }}
                    />
                    </div>
                </div>
            </div>

            {this.state.linesLoaded ? (null) : (<div className='loading-overlay'/>)}

            </div>

        );
    }
}


export default App;



