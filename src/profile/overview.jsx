import React, { Component } from 'react';

import CellLineTable from './cellLineTable.jsx';
import ExpressionPlot from '../common/expressionPlot.jsx';
import FacsPlotContainer from './facsPlotContainer.jsx';
import ViewerContainer from './viewerContainer.jsx';
import VolcanoPlotContainer from './volcanoPlotContainer.jsx';
import AnnotationsForm from './annotations.jsx';
import { SectionHeader } from './common.jsx';

// this is where the content for the 'About this protein' comes from
import uniprotMetadata from '../demo/data/uniprot_metadata.json';


export default class Overview extends Component {

    constructor (props) {
        super(props);
        this.state = {};
    }

    render () {
        return (
            <div>
                <div className="flex" style={{minWidth: '1600px'}}>

                    {/* Left column - about box and expression and facs plots*/}
                    <div className="w-25 pl3 pr4 pt0">

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
                    <div className="pl3 pr3" style={{flexBasis: '650px'}}>
                        <SectionHeader title='Localization'/>
                        <ViewerContainer
                            fovs={this.props.fovs}
                            fovId={this.props.fovId}
                            roiId={this.props.roiId}
                            changeRoi={(roiId, fovId) => this.setState({roiId, fovId})}
                        />
                    </div>


                    {/* Right column - annotations or volcano plot */}
                    <div className="w-33 pl3 pb3">
                        {this.props.showAnnotations ? (
                            <div>
                                <SectionHeader title='Annotations'/>    
                                <AnnotationsForm 
                                    cellLineId={this.props.cellLineId} 
                                    fovIds={this.props.fovs.map(fov => fov.id)}
                                />
                            </div>
                        ) : (
                            <div>
                                <SectionHeader title='Interactions'/>
                                <VolcanoPlotContainer
                                    targetName={this.props.targetName}
                                    changeTarget={this.props.onSearchChange}
                                />
                            </div>
                        )}
                    </div>
                </div>


                {/* table of all targets */}
                <div className="w-90 pt0 pl4 pb5">
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