
import * as d3 from 'd3';
import React, { Component } from 'react';

import { Button, Radio, RadioGroup, MenuItem } from "@blueprintjs/core";
import { Select } from "@blueprintjs/select";

import Navbar from '../common/navbar.jsx';
import Header from './header.jsx';
import Overview from './overview.jsx';
import FOVCurator from '../microscopy/FOVCurator.jsx';

import 'tachyons';
import 'react-table/react-table.css';
import "@blueprintjs/core/lib/css/blueprint.css";

import settings from '../common/settings.js';
import * as utils from '../common/utils.js';

import '../common/common.css';
import './Profile.css';


class App extends Component {

    constructor (props) {
        super(props);

        this.urlParams = new URLSearchParams(window.location.search);

        this.cellLine = {};
        this.allCellLines = [];

        this.state = {
            fovs: [],
            cellLineId: null,
            targetName: null,
            linesLoaded: false,
            showAnnotations: this.urlParams.get('mode')==='target_annotation',
            showFOVCurator: this.urlParams.get('mode')==='fov_annotation',
        };

        this.changeTarget = this.changeTarget.bind(this);
        this.onSearchChange = this.onSearchChange.bind(this);
        this.onCellLineSelect = this.onCellLineSelect.bind(this);

    }


    changeTarget (cellLine) {
        // cellLine is the JSON object returned by the lines/ endpoint

        // check that the target has changed
        if (cellLine.metadata.cell_line_id===this.state.cellLineId) return;

        // only FOVs with manual annotations are displayed in the volume/slice viewer
        const viewableFovs = cellLine.fovs.filter(fov => fov.annotation);

        this.cellLine = cellLine;
        this.setState({
            cellLineId: cellLine.metadata.cell_line_id,
            targetName: cellLine.metadata.target_name,
            allFovs: cellLine.fovs,
            fovs: viewableFovs,
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

        return (
            <div>
                <Navbar/>

                {/* main container */}
                <div className="w-100 pl4 pr4">

                    {/* page header and metadata */}
                    <Header cellLine={this.cellLine} onSearchChange={this.onSearchChange}/>

                    {this.state.showFOVCurator ? (
                        <FOVCurator 
                            cellLines={this.allCellLines}
                            onSearchChange={this.onSearchChange}
                            onCellLineSelect={this.onCellLineSelect}
                            {...this.state}
                        />
                    ) : (
                        <Overview
                            cellLines={this.allCellLines}
                            onSearchChange={this.onSearchChange}
                            onCellLineSelect={this.onCellLineSelect}
                            showAnnotations={this.state.showAnnotations}
                            {...this.state}/>
                    )}
                </div>

                {this.state.linesLoaded ? (null) : (<div className='loading-overlay'/>)}
            </div>

        );
    }
}


export default App;



