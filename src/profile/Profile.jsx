
import * as d3 from 'd3';
import React, { Component } from 'react';

import { Button, Radio, RadioGroup, MenuItem } from "@blueprintjs/core";
import { Select } from "@blueprintjs/select";

import Navbar from '../common/navbar.jsx';
import Header from './header.jsx';
import Overview from './overview.jsx';
import FovAnnotator from '../microscopy/fovAnnotator.jsx';

import 'tachyons';
import 'react-table/react-table.css';
import "@blueprintjs/core/lib/css/blueprint.css";

import settings from '../common/settings.js';
import * as utils from '../common/utils.js';

import '../common/common.css';
import './Profile.css';

const initialTarget = 'POLR2F';

class App extends Component {

    constructor (props) {
        super(props);

        this.urlParams = new URLSearchParams(window.location.search);

        this.cellLine = {};
        this.allCellLines = [];

        this.state = {
            cellLineId: null,
            targetName: null,
            linesLoaded: false,
            showTargetAnnotator: this.urlParams.get('mode')==='target_annotation',
            showFovAnnotator: this.urlParams.get('mode')==='fov_annotation',
        };

        this.changeTarget = this.changeTarget.bind(this);
        this.onSearchChange = this.onSearchChange.bind(this);
        this.onCellLineSelect = this.onCellLineSelect.bind(this);

    }


    changeTarget (cellLine) {
        // cellLine is the JSON object returned by the lines/ endpoint

        // check that the target has changed
        if (cellLine.metadata.cell_line_id===this.state.cellLineId) return;

        this.cellLine = cellLine;
        this.setState({
            cellLineId: cellLine.metadata.cell_line_id,
            targetName: cellLine.metadata.target_name,
        });
    }


    onSearchChange (value) {
        // fired when the user hits enter in the header's target search text input
        // (`value` is the string in the textbox)
        const url = `${settings.apiUrl}/lines?target=${value}`;
        d3.json(url).then(lines => {
            for (const line of lines) {
                if (line) {
                    this.changeTarget(line);
                    break;
                }
            }
        });
    }


    onCellLineSelect (cellLineId) {
        // fired when the user clicks on a row of the datatable
        const url = `${settings.apiUrl}/lines/${cellLineId}`;
        d3.json(url).then(line => {
            if (line) this.changeTarget(line);
        });
    }
    

    componentDidMount () {
        let url = `${settings.apiUrl}/lines`;
        d3.json(url).then(lines => {
            this.allCellLines = lines;     
            this.setState({linesLoaded: true});
        });
        // initial target to display
        this.onSearchChange(this.urlParams.get('target') || initialTarget);
    }


    render () {

        return (
            <div>
                <Navbar/>

                {/* main container */}
                <div className="pl4 pr4" style={{width: '2000px'}}>

                    {/* page header and metadata */}
                    <Header cellLine={this.cellLine} onSearchChange={this.onSearchChange}/>

                    {this.state.showFovAnnotator ? (
                        <FovAnnotator 
                            cellLines={this.allCellLines}
                            cellLineId={this.state.cellLineId}
                            onSearchChange={this.onSearchChange}
                            onCellLineSelect={this.onCellLineSelect}
                        />
                    ) : (
                        <Overview
                            cellLine={this.cellLine}
                            cellLines={this.allCellLines}
                            cellLineId={this.state.cellLineId}
                            targetName={this.state.targetName}
                            onSearchChange={this.onSearchChange}
                            onCellLineSelect={this.onCellLineSelect}
                            showTargetAnnotator={this.state.showTargetAnnotator}
                        />
                    )}
                </div>

                {this.state.linesLoaded ? (null) : (<div className='loading-overlay'/>)}
            </div>

        );
    }
}


export default App;



