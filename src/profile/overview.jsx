import * as d3 from 'd3';
import React, { Component } from 'react';

import CellLineTable from './cellLineTable.jsx';
import ExpressionPlot from '../common/expressionPlot.jsx';
import FacsPlotContainer from './facsPlotContainer.jsx';
import ViewerContainer from './viewerContainer.jsx';
import MassSpecPlotContainer from './massSpecPlotContainer.jsx';
import TargetAnnotator from './targetAnnotator.jsx';
import { SectionHeader } from './common.jsx';
import settings from '../common/settings.js';
import { loadFovs } from '../common/utils.js';

// this is where the content for the 'About this protein' comes from
import uniprotMetadata from '../demo/data/uniprot_metadata.json';



export default class Overview extends Component {

    constructor (props) {
        super(props);
        this.state = {
            fovs: [],
            rois: [],
            roiId: undefined,
            fovId: undefined,
        };
    }


    componentDidUpdate (prevProps) {
        if (prevProps.cellLineId===this.props.cellLineId) return;
        loadFovs(this.props.cellLineId, fovState => this.setState({...fovState}));
    }


    render () {
        return (
            <div>
                <div className="flex" style={{minWidth: '1600px'}}>

                    {/* Left column - about box and expression and facs plots*/}
                    <div className="pl3 pr4 pt0" style={{width: '400px'}}>

                        {/* 'About' textbox */}
                        <div className='pb4'>
                            <SectionHeader title='About this protein'/>
                            <div className='pt2 protein-function-container'>
                                <p>{uniprotMetadata[this.props.targetName]?.uniprot_function}</p>
                            </div>
                        </div>

                        {/* expression scatterplot*/}
                        <SectionHeader title='Expression level'/>
                        <div className="fl w-100 pb3 expression-plot-container">
                            <ExpressionPlot targetName={this.props.targetName}/>
                        </div>

                        {/* FACS plot */}
                        <SectionHeader title='FACS histograms'/>
                        <FacsPlotContainer cellLineId={this.props.cellLineId}/>
                    </div>

                    {/* Center column - sliceViewer and volumeViewer */}
                    {/* note the hard-coded width (because the ROIs are always 600px */}
                    <div className="pl3 pr3" style={{width: '650px'}}>
                        <SectionHeader title='Localization'/>
                        <ViewerContainer
                            cellLineId={this.props.cellLineId}
                            fovs={this.state.fovs}
                            rois={this.state.rois}
                            fovId={this.state.fovId}
                            roiId={this.state.roiId}
                            isLowGfp={this.props.cellLine.annotation?.categories?.includes('low_gfp')}
                            changeRoi={(roiId, fovId) => this.setState({roiId, fovId})}
                        />
                    </div>
                
                    {/* Right column - annotations or volcano plot */}
                    <div className="pl3 pb3" style={{width: '600px'}}>
                        {this.props.showTargetAnnotator ? (
                            <div>
                                <SectionHeader title='Annotations'/>    
                                <TargetAnnotator 
                                    cellLineId={this.props.cellLineId} 
                                    fovIds={this.state.fovs.map(fov => fov.metadata.id)}
                                />
                            </div>
                        ) : (
                            <div>
                                <SectionHeader title='Interactions'/>
                                <MassSpecPlotContainer
                                    cellLineId={this.props.cellLineId}
                                    changeTarget={this.props.onSearchChange}
                                />
                            </div>
                        )}
                    </div>
                </div>


                {/* table of all targets */}
                <div className="w-100 pt0 pl4 pb5">
                    <SectionHeader title='All cell lines'/>
                    <CellLineTable 
                        cellLineId={this.props.cellLineId}
                        cellLines={this.props.cellLines}
                        onCellLineSelect={this.props.onCellLineSelect}
                    />
                </div>

            </div>
        );
    }
}