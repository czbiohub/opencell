import * as d3 from 'd3';
import React, { Component } from 'react';

import ExpressionPlot from '../common/expressionPlot.jsx';
import FacsPlotContainer from './facsPlotContainer.jsx';
import ViewerContainer from './viewerContainer.jsx';
import MassSpecPlotContainer from './massSpecPlotContainer.jsx';
import TargetAnnotator from './targetAnnotator.jsx';
import { SectionHeader } from './common.jsx';
import settings from '../common/settings.js';
import { loadAnnotatedFovs } from '../common/utils.js';
import CellLineMetadata from './cellLineMetadata.jsx';


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

    componentDidMount () {
        //console.log(`Overview mounted with cellLineId ${this.props.cellLineId}`);
        if (this.props.cellLineId) {
            loadAnnotatedFovs(this.props.cellLineId, fovState => this.setState({...fovState}));
        }
    }


    componentDidUpdate (prevProps) {
        //console.log(`Overview updated with cellLineId ${this.props.cellLineId}`);
        if (prevProps.cellLineId===this.props.cellLineId) return;
        loadAnnotatedFovs(this.props.cellLineId, fovState => this.setState({...fovState}));
    }


    render () {
        return (
            <div>
                <div className="flex" style={{minWidth: '1600px'}}>

                    {/* Left column - about box and expression and facs plots*/}
                    <div className="pl2 pr4 pt0" style={{width: '350px'}}>

                        <CellLineMetadata cellLine={this.props.cellLine}/>

                        {/* 'About' textbox */}
                        <div className='pb4'>
                            <SectionHeader title='About this protein'/>
                            <div className='pt2 about-this-protein-container'>
                                <p>{this.props.cellLine.uniprot_metadata?.annotation}</p>
                            </div>
                        </div>

                        {/* expression scatterplot*/}
                        <SectionHeader title='Expression level'/>
                        <div className="fl w-100 pb3 expression-plot-container">
                            <ExpressionPlot targetName={this.props.cellLine.metadata.target_name}/>
                        </div>

                        {/* FACS plot */}
                        <SectionHeader title='FACS histograms'/>
                        <FacsPlotContainer cellLineId={this.props.cellLineId}/>
                    </div>

                    {/* Center column - sliceViewer and volumeViewer */}
                    {/* note the hard-coded width (because the ROIs are always 600px */}
                    <div className="pt3 pl0 pr3" style={{width: '700px'}}>
                        <SectionHeader title='Fluorescence microscopy'/>
                        <ViewerContainer
                            cellLineId={this.props.cellLineId}
                            fovs={this.state.fovs}
                            rois={this.state.rois}
                            fovId={this.state.fovId}
                            roiId={this.state.roiId}
                            showMetadata={true}
                            isLowGfp={this.props.cellLine.annotation?.categories?.includes('low_gfp')}
                            changeRoi={(roiId, fovId) => this.setState({roiId, fovId})}
                        />
                    </div>
                
                    {/* Right column - annotations or volcano plot */}
                    <div className="pa3" style={{width: '600px'}}>
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
                                <SectionHeader title='Protein interactions'/>
                                <MassSpecPlotContainer
                                    cellLineId={this.props.cellLineId}
                                    changeTarget={this.props.onSearchChange}
                                />
                            </div>
                        )}
                    </div>
                </div>
            </div>
        );
    }
}