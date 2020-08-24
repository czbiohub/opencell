
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


export default class Profile extends Component {

    constructor (props) {
        super(props);

        this.urlParams = new URLSearchParams(window.location.search);

        this.cellLine = {};
        this.allCellLines = [];

        this.state = {
            // cellLineId: null,
            targetName: null,
            linesLoaded: false,
        };
    }


    componentDidUpdate(prevProps) {
        
        if (prevProps.cellLineId===this.props.cellLineId) return;
        if (!this.state.linesLoaded) return;

        //if (!cellLineId || this.state.cellLineId===cellLineId) return;

        const cellLine = this.allCellLines.filter(
            line => line.metadata?.cell_line_id === parseInt(this.props.cellLineId)
        )[0];

        if (!cellLine) {
            console.log(`No cell line found for cellLineId ${this.props.cellLineId}`);
            return;
        };
    
        this.cellLine = cellLine;
        this.setState({
            // cellLineId,
            targetName: this.cellLine.metadata.target_name,
        });
    }


    componentDidMount () {
        d3.json(`${settings.apiUrl}/lines`).then(lines => {
            this.allCellLines = lines;     
            this.setState({linesLoaded: true});
        });
    }

    componentWillReceiveProps (nextProps) {
        // this is hackish: we end up here only if the user clicked the back or forward buttons,
        // which means we do not want to push the new cellLineId to the history,
        // so we pass false to this.changeCellLineId
        this.props.onCellLineSelect(nextProps.match.params.cellLineId, false);
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
                            cellLineId={this.props.cellLineId}
                            onSearchChange={this.onSearchChange}
                            onCellLineSelect={this.props.onCellLineSelect}
                        />
                    ) : (
                        <Overview
                            cellLine={this.cellLine}
                            cellLines={this.allCellLines}
                            cellLineId={this.props.cellLineId}
                            targetName={this.state.targetName}
                            onSearchChange={this.onSearchChange}
                            onCellLineSelect={this.props.onCellLineSelect}
                            showTargetAnnotator={this.props.showTargetAnnotator}
                        />
                    )}
                </div>

                {this.state.linesLoaded ? (null) : (<div className='loading-overlay'/>)}
            </div>

        );
    }
}



