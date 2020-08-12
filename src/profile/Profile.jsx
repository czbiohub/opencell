
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




export default class Profile extends Component {

    constructor (props) {
        super(props);

        this.urlParams = new URLSearchParams(window.location.search);

        this.cellLine = {};
        this.allCellLines = [];

        this.state = {
            cellLineId: null,
            targetName: null,
            linesLoaded: false,
        };

        this.onSearchChange = this.onSearchChange.bind(this);
        this.changeCellLineId = this.changeCellLineId.bind(this);

    }


    changeCellLineId (cellLineId, push = true) {
        
        if (!this.state.linesLoaded) return;

        cellLineId = parseInt(cellLineId);
        const cellLine = this.allCellLines.filter(
            line => line.metadata?.cell_line_id === cellLineId
        )[0];

        if (!cellLine) {
            console.log(`No cell line found for cellLineId ${cellLineId}`);
            return;
        };

        if (push) this.props.history.push(`${this.props.path}/${cellLineId}`);

        this.cellLine = cellLine;
        this.setState({
            cellLineId,
            targetName: this.cellLine.metadata.target_name,
        });
    }


    onSearchChange (value) {
        // fired when the user hits enter in the header's target search text input
        // (`value` is the string in the textbox)
        const url = `${settings.apiUrl}/lines?target=${value}`;
        d3.json(url).then(lines => {
            for (const line of lines) {
                if (line) {
                    const newCellLineId = line.metadata.cell_line_id;
                    this.changeCellLineId(newCellLineId);
                    break;
                }
            }
        });
    }


    componentDidMount () {
        let url = `${settings.apiUrl}/lines`;
        
        d3.json(url).then(lines => {
            this.allCellLines = lines;     
            this.setState({linesLoaded: true});

            // initial target to display
            this.props.match.params.cellLineId ? (
                this.changeCellLineId(this.props.match.params.cellLineId, false)
            ) : (
                this.onSearchChange(this.urlParams.get('target') || initialTarget)
            );
        });
    }


    componentWillReceiveProps (nextProps) {
        // this is hackish: we end up here only if the user clicked the back or forward buttons;
        // so we know that we do not want to push the new cellLineId to the history,
        // so we pass false to this.changeCellLineId
        
        const nextCellLineId = nextProps.match.params.cellLineId;
        if (nextCellLineId && this.state.cellLineId!==nextCellLineId) {
            this.changeCellLineId(nextCellLineId, false);
        }
    }


    render () {
        return (
            <div>
                {/* main container */}
                <div className="pl4 pr4" style={{width: '2000px'}}>

                    {/* page header and metadata */}
                    <Header cellLine={this.cellLine} onSearchChange={this.onSearchChange}/>

                    {this.props.showFovAnnotator ? (
                        <FovAnnotator 
                            cellLines={this.allCellLines}
                            cellLineId={this.state.cellLineId}
                            onSearchChange={this.onSearchChange}
                            onCellLineSelect={this.changeCellLineId}
                        />
                    ) : (
                        <Overview
                            cellLine={this.cellLine}
                            cellLines={this.allCellLines}
                            cellLineId={this.state.cellLineId}
                            targetName={this.state.targetName}
                            onSearchChange={this.onSearchChange}
                            onCellLineSelect={this.changeCellLineId}
                            showTargetAnnotator={this.props.showTargetAnnotator}
                        />
                    )}
                </div>

                {this.state.linesLoaded ? (null) : (<div className='loading-overlay'/>)}
            </div>

        );
    }
}



