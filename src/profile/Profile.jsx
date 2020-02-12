
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


class App extends Component {

    constructor (props) {
        super(props);

        this.state = {
            rois: [],
            fovId: null,
            roiId: null,
            cellLineId: null,
            targetName: null,
            linesLoaded: false,
        };

        this.changeTarget = this.changeTarget.bind(this);
        this.onSearchChange = this.onSearchChange.bind(this);

        this.cellLine = {};
        this.allCellLines = [];
        this.urlParams = new URLSearchParams(window.location.search);
    }


    changeTarget (cellLine) {
        
        const targetName = cellLine.target_name;

        // check that the target has changed
        if (targetName===this.state.targetName) return;

        // concatenate all ROIs
        const rois = [...cellLine.fovs[0].rois, ...cellLine.fovs[1].rois];

        this.cellLine = cellLine;

        this.setState({
            cellLineId: cellLine.cell_line_id,
            fovId: rois[0].fov_id,
            roiId: rois[0].id,
            targetName,
            rois,
        });
    }


    onSearchChange (value) {
        // fired when the user hits enter in the header's target search text input
        // `value` is the value of the input

        let url = `${settings.apiUrl}/lines?target_name=${value}&kind=all`;
        d3.json(url).then(lines => {
            for (const line of lines) {
                if (line && line.fovs.length) {
                    this.changeTarget(line);
                    break;
                }
            }
        });
    }


    componentDidMount() {
        let url = `${settings.apiUrl}/lines`;
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
                accessor: row => row.target_name,
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

                {/* Left column */}
                <div className="fl w-25 dib pl3 pr4 pt0">

                    {/* 'About' textbox */}
                    <div className="bb b--black-10">
                        <div className="f3 container-header">About this protein</div>
                    </div>
                    <div
                        className='pt0 pb3 w-100 protein-function-container'
                        style={{height: 100, overflow: 'auto', lineHeight: 1.33}}
                    >
                        <div>
                            <p>{uniprotMetadata[this.state.targetName]?.uniprot_function}</p>
                        </div>
                    </div>

                    {/* expression scatterplot*/}
                    <div className="pt4 bb b--black-10">
                        <div className="f3 container-header">Expression level</div>
                    </div>
                    <div 
                        className="fl pt3 pb3 w-100 expression-plot-container" 
                        style={{marginLeft: -20, marginTop: 0}}
                    >
                        <ExpressionPlot targetName={this.state.targetName}/>
                    </div>

                    {/* FACS plot */}
                    <div className="bb b--black-10">
                        <div className="f3 container-header">FACS histograms</div>
                    </div>  
                    <FacsPlotContainer cellLineId={this.state.cellLineId}/>
                   
                </div>


                {/* Center column - sliceViewer and volumeViewer */}
                {/* note that the 'fl' is required here for 'dib' to work*/}
                <div className="fl dib pl3 pr3" style={{width: '650px'}}>
                    <div className="bb b--black-10">
                        <div className="f3 container-header">Localization</div>
                    </div>
                    <ViewerContainer
                        rois={this.state.rois}
                        fovId={this.state.fovId}
                        roiId={this.state.roiId}
                        changeRoi={(roiId, fovId) => this.setState({roiId, fovId})}
                    />
                </div>


                {/* Right column - annotations or volcano plot */}
                <div className="fl dib pl3 pb3" style={{width: '400px'}}>
                    {this.urlParams.get('annotations')!=='yes' ? (
                        <div>
                            <div className="bb b--black-10">
                                <div className="f3 container-header">Interactions</div>
                            </div>
                            <VolcanoPlotContainer
                                targetName={this.state.targetName}
                                changeTarget={name => this.onSearchChange(name)}
                            />
                        </div>
                    ) : (
                        <div>
                            <div className="bb b--black-10">
                                <div className="f3 container-header">Annotations</div>
                            </div>       
                            {/* note that fovIds should include only the *displayed* FOVs */}
                            <AnnotationsForm 
                                cellLineId={this.state.cellLineId} 
                                fovIds={this.state.rois.map(roi => roi.fov_id)}
                            />
                        </div>
                    )}
                </div>


                {/* table of all targets */}
                <div className="fl w-90 pt0 pl4 pb5">
                    <div className="">
                        <div className="f3 container-header">All cell lines</div>
                    </div>
                    <ReactTable 
                        pageSize={50}
                        showPageSizeOptions={false}
                        filterable={true}
                        columns={tableDefs}
                        data={this.allCellLines.map(line => {
                            return {...line, isActive: this.state.targetName===line.target_name};
                        })}
                        getTrProps={(state, rowInfo, column) => {
                            const isActive = rowInfo ? rowInfo.original.isActive : false;
                            return {
                                onClick: () => this.onSearchChange(rowInfo.original.target_name),
                                style: {
                                    background: isActive ? '#ddd' : null,
                                    fontWeight: isActive ? 'bold' : 'normal'
                                }
                            }
                        }}
                        getPaginationProps={(state, rowInfo, column) => {
                            return {style: {fontSize: 16}}
                        }}
                    />
                </div>
            </div>

            {this.state.linesLoaded ? (null) : (<div className='loading-overlay'/>)}

            </div>

        );
    }
}


export default App;



