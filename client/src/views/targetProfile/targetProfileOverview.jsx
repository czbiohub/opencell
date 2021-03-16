import React, { Component } from 'react';

import FacsPlotContainer from './facsPlotContainer.jsx';
import TargetAnnotator from './targetAnnotator.jsx';
import ExpressionPlot from '../../components/expressionPlot.jsx';
import ViewerContainer from '../../components/imageViewer/viewerContainer.jsx';
import MassSpecContainer from '../../components/massSpecContainer.jsx';
import SectionHeader from '../../components/sectionHeader.jsx';
import { LocalizationAnnotations } from '../../components/localizationAnnotations.jsx';
import SequencingPlot from '../../components/sequencingPlot.jsx';
import CellLineMetadataTable from '../../components/cellLineMetadataTable.jsx';
import ExternalLinks from '../../components/externalLinks.jsx';
import FunctionalAnnotation from '../../components/functionalAnnotation.jsx';

import * as popoverContents from '../../components/popoverContents.jsx';
import * as utils from '../../utils/utils.js';
import settings from '../../settings/settings.js';


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
            <>
                <div className="flex" style={{minWidth: '1600px'}}>

                    {/* Left column - about box and expression and facs plots*/}
                    <div className="pl3 pr4" style={{width: '350px'}}>

                        <CellLineMetadataTable data={this.props.cellLine}/>

                        <SectionHeader 
                            title='Allele frequency' 
                            popoverContent={popoverContents.sequencingHeader}
                        />
                        <SequencingPlot data={this.props.cellLine.sequencing}/>

                        <SectionHeader 
                            title='About this protein' 
                            popoverContent={popoverContents.aboutThisProteinHeader}
                        />
                        <FunctionalAnnotation 
                            content={this.props.cellLine.uniprot_metadata?.annotation}
                        />
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
                            <>
                                <SectionHeader title='FACS histograms'/>
                                <FacsPlotContainer cellLineId={this.props.cellLineId}/>
                            </>
                        ) : null}

                    </div>

                    {/* Center column - sliceViewer and volumeViewer */}
                    {/* note the hard-coded width (because the ROIs are always 600px */}
                    <div className="pt3" style={{width: '600px'}}>
                        <SectionHeader 
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
                    <div className="pt3 pl4 pr4" style={{width: '700px'}}>
                        {this.props.showTargetAnnotator ? (
                            <>
                                <SectionHeader title='Annotations'/>    
                                <TargetAnnotator 
                                    cellLineId={this.props.cellLineId} 
                                    fovIds={this.state.fovs.map(fov => fov.metadata.id)}
                                />
                            </>
                        ) : (
                            <>
                                <SectionHeader title='Mass spectrometry'/>
                                <MassSpecContainer 
                                    layout='tabs'
                                    ensgId={this.props.cellLine.metadata.ensg_id}
                                    pulldownId={this.props.cellLine.best_pulldown?.id}
                                    geneName={this.props.cellLine.metadata?.target_name}
                                    handleGeneNameSearch={this.props.handleGeneNameSearch}
                                />
                            </>
                        )}
                    </div>
                </div>
            </>
        );
    }
}