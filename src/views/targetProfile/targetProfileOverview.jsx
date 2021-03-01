import * as d3 from 'd3';
import React, { Component } from 'react';

import ExpressionPlot from './expressionPlot.jsx';
import FacsPlotContainer from '../../components/facsPlot/facsPlotContainer.jsx';
import ViewerContainer from '../../components/imageViewer/viewerContainer.jsx';

import MassSpecContainer from '../../components/massSpecContainer.jsx';
import TargetAnnotator from './targetAnnotator.jsx';
import { SectionHeader } from '../../components/common.jsx';
import settings from '../../settings/settings.js';
import * as popoverContents from '../../components/popoverContents.jsx';
import * as utils from '../../utils/utils.js';
import { 
    CellLineMetadataTable, 
    ExternalLinks, 
    LocalizationAnnotations,
    SequencingPlot,
} from '../../components/cellLineMetadata.jsx';


export default class TargetProfileOverview extends Component {
    static contextType = settings.ModeContext;
    constructor (props) {
        super(props);
        this.state = {
            fovs: [],
            rois: [],
            roiId: undefined,
            fovId: undefined,
            massSpecView: 'network',
        };

    }

    componentDidMount () {
        //console.log(`Overview mounted with cellLineId ${this.props.cellLineId}`);
        if (!this.props.cellLineId) return;
        utils.getAnnotatedFovMetadata(
            this.props.cellLineId, 
            fovState => this.setState({...fovState}),
            error => this.setState({fovs: [], rois: []})
        );
    }

    componentDidUpdate (prevProps) {
        //console.log(`Overview updated with cellLineId ${this.props.cellLineId}`);
        if (prevProps.cellLineId===this.props.cellLineId) return;
        utils.getAnnotatedFovMetadata(
            this.props.cellLineId, 
            fovState => this.setState({...fovState}),
            error => this.setState({fovs: [], rois: []})
        );
    }

    render () {
        return (
            <div>
                <div className="flex" style={{minWidth: '1600px'}}>

                    {/* Left column - about box and expression and facs plots*/}
                    <div className="pl3 pr4" style={{width: '350px'}}>

                        <CellLineMetadataTable data={this.props.cellLine}/>

                        <SectionHeader 
                            title='Allele frequency' 
                            popoverContent={popoverContents.aboutSequencing}
                        />
                        <SequencingPlot data={this.props.cellLine.sequencing}/>

                        {/* 'About' textbox */}
                        <div>
                            <SectionHeader 
                                title='About this protein' 
                                popoverContent={popoverContents.aboutThisProteinHeader}
                            />
                            <div className='pt2 about-this-protein-container'>
                                <p>{this.props.cellLine.uniprot_metadata?.annotation}</p>
                            </div>
                        </div>
                        <ExternalLinks data={this.props.cellLine}/>

                        <SectionHeader 
                            title='Localization' 
                            popoverContent={popoverContents.localizationHeader}
                        />
                        <LocalizationAnnotations data={this.props.cellLine}/>

                        {/* expression scatterplot*/}
                        <SectionHeader 
                            title='Expression level' 
                            popoverContent={popoverContents.expressionLevelHeader}
                        />
                        <div className="w-100 pb3 expression-plot-container">
                            <ExpressionPlot 
                                cellLines={this.props.allCellLines}
                                cellLineId={this.props.cellLineId}
                            />
                        </div>

                        {/* FACS plot */}
                        {this.context==='private' ? (
                            <div>
                                <SectionHeader title='FACS histograms'/>
                                <FacsPlotContainer cellLineId={this.props.cellLineId}/>
                            </div>
                        ) : null}

                    </div>

                    {/* Center column - sliceViewer and volumeViewer */}
                    {/* note the hard-coded width (because the ROIs are always 600px */}
                    
                    <div className="pt4" style={{width: '620px'}}>
                        <SectionHeader 
                            border={true}
                            title='Fluorescence microscopy' 
                            popoverContent={popoverContents.microscopyHeader}
                        />
                        <ViewerContainer
                            cellLineId={this.props.cellLineId}
                            fovs={this.state.fovs}
                            rois={this.state.rois}
                            fovId={this.state.fovId}
                            roiId={this.state.roiId}
                            showMetadata={this.context==='private'}
                            isLowGfp={this.props.cellLine.annotation?.categories?.includes('low_gfp')}
                            changeRoi={(roiId, fovId) => this.setState({roiId, fovId})}
                        />
                    </div>

                    {/* Right column - cell line annotations or mass spec container */}
                    <div className="pt4 pl4 pr4" style={{width: '750px'}}>
                        {this.props.showTargetAnnotator ? (
                            <div>
                                <SectionHeader title='Annotations'/>    
                                <TargetAnnotator 
                                    cellLineId={this.props.cellLineId} 
                                    fovIds={this.state.fovs.map(fov => fov.metadata.id)}
                                />
                            </div>
                        ) : (
                            <MassSpecContainer 
                                layout='tabs'
                                ensgId={this.props.cellLine.metadata.ensg_id}
                                pulldownId={this.props.cellLine.best_pulldown?.id}
                                geneName={this.props.cellLine.metadata?.target_name}
                                handleGeneNameSearch={this.props.handleGeneNameSearch}
                            />
                        )}
                    </div>
                </div>
            </div>
        );
    }
}