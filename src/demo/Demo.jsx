
import * as d3 from 'd3';
import React, { Component } from 'react';
import ReactTable from 'react-table';

import ButtonGroup from './buttonGroup.jsx';
import Slider from './slider.jsx';

import Navbar from '../common/navbar.jsx';

import Header from './header.jsx';
import SliceViz from './sliceViz.jsx';
import VolumeViz from './volumeViz.jsx';
import VolcanoPlot from './volcanoPlot.jsx';


import FACSPlot from '../common/facsPlot.jsx';
import ExpressionPlot from '../common/expressionPlot.jsx';


import 'tachyons';
import 'react-table/react-table.css';

import { NRRDLoader } from 'three/examples/jsm/loaders/NRRDLoader';
import { metadataDefinitions } from './definitions.js';

import msData from './data/20190816_ms-data.json';
import nrrdFilepaths from './data/20190816_nrrd-filepaths.json';
import manualMetadata from './data/manual_metadata.json';
import uniprotMetadata from './data/uniprot_metadata.json';
import pipelineMetadata from './data/20191217_all-pipeline-metadata.json';

import '../common/common.css';
import './Demo.css';

const localApi = `http://localhost:5000`;
const capApi = `http://cap.czbiohub.org:5001`;

class App extends Component {

    constructor (props) {
        super(props);

        this.apiUrl = capApi;

        this.state = {

            appHasLoaded: false,
            
            fovId: null,
            cellLineId: null,
            targetName: null,

            // 'Volume' or 'Slice'
            localizationMode: 'Slice',

            // 'GFP' or 'DAPI' or 'Both'
            localizationChannel: 'Both',

            // 'Volcano' or 'Table'
            msDisplayMode: 'Volcano',

            // 'Significance' or 'Function'
            volcanoLabelColor: 'Significance',

            // 'None', 'Family', 'Status'
            msColorMode: 'Status',

            // whether to plot the GFP-positive population
            facsShowGFP: 'On',

            // whether to show the annotations (median/max intensity etc)
            facsShowAnnotations: 'On',

            // label mode for volcano plot
            volcanoShowLabels: 'When zoomed',

            // whether to reset the zoom 
            // this is a hack: volcanoPlot just listens for changes to this value
            volcanoResetZoom: false,

            // HACK: these values must match the initial values hard-coded in the sliders below
            gfpMin: 0,
            gfpMax: 50,
            dapiMin: 5,
            dapiMax: 50,
            zIndex: 30,
        };

        this.changeTarget = this.changeTarget.bind(this);
        this.onSearchChange = this.onSearchChange.bind(this);

        // the list of all targets for which we have data;
        // these target names should also all appear in manualMetadata
        this.allTargetNames = Object.keys(pipelineMetadata);
    
    }



    changeTarget (targetName, cellLineId, fovId) {
        
        // check that the target has changed
        if (targetName===this.state.targetName) return;

        // reset appHasLoaded to false, since we now need to load new NRRD files
        this.setState({
            targetName,
            cellLineId,
            fovId,
            appHasLoaded: false, 
            gfpMax: manualMetadata[targetName]?.gfp_max || 50,
        });

    }

    onSearchChange (value) {
        // fired when the user hits enter in the header's target search text input
        // `value` is the value of the input

        let url = `${this.apiUrl}/lines?target_name=${value}`;
        d3.json(url).then(data => {
            const line = data[0];
            if (!line) return;
            this.changeTarget(line.target_name, line.cell_line_id, line.fovs[0].fov_id);
        });
    }


    loadStacks() {

        const loadStack = (filepath) => {
            return new Promise((resolve, reject) => {
                const loader = new NRRDLoader();
                loader.load(filepath, volume => resolve(volume));
            });
        }

        // ***WARNING***
        // the order of the channels in the `filepaths` array below matters,
        // because it is *independently* hard-coded in SliceViz and VolumeViz
        // const fileroot = nrrdFilepaths[this.state.targetName];
        // const filepaths = [
        //     `./demo-data/stacks/${fileroot}_C0.nrrd`,  // DAPI
        //     `./demo-data/stacks/${fileroot}_C1.nrrd`,  // GFP
        // ];

        if (!this.state.fovId) {
            this.setState({appHasLoaded: true});
            return;
        }

        const filepaths = [
            `${this.apiUrl}/fovs/dapi/nrrd/${this.state.fovId}`,
            `${this.apiUrl}/fovs/gfp/nrrd/${this.state.fovId}`,
        ];

        console.log('before promise');
        Promise.all(filepaths.map(loadStack)).then(volumes => {
            this.volumes = volumes;
            this.setState({appHasLoaded: true});
            console.log('volumes loaded');
        });
    }

    
    componentDidMount() {
        
        // initial target to display
        this.onSearchChange('LMNB1');

        // load the NRRD files
        this.loadStacks();
    }

    
    componentDidUpdate(prevProps, prevState, snapshot) {

        // reload the NRRD files
        if (prevState.targetName!==this.state.targetName) {
            this.loadStacks();
        }

        //console.log(this.state.gfpMax);
    }


    render() {

        let localizationContent;
        if (this.state.localizationMode==='Volume') {
            localizationContent = <VolumeViz
                volumes={this.volumes}
                {...this.state}
            />
        }
    
        if (this.state.localizationMode==='Slice') {
            localizationContent = <SliceViz
                volumes={this.volumes}
                {...this.state}
            />
        }

        // append gene_name to metadataDefinitions 
        // (used only for the table of all targets at the bottom)
        let tableDefs = [
            {   
                id: 'gene_name',
                Header: 'Gene name',
                accessor: row => row.targetName,
            },
            ...metadataDefinitions,
        ];

        return (

            <div>
            <Navbar/>

            {/* main container */}
            <div className="w-100 pl4 pr4">


                {/* page header and metadata */}
                <Header 
                    targetName={this.state.targetName}
                    onSearchChange={this.onSearchChange}/>


                {/* Expression scatterplot and FACS histograms */}
                <div className="fl w-25 dib pl3 pr4 pt0">

                    <div className="bb b--black-10">
                        <div className="f3 container-header">About this protein</div>
                    </div>

                    <div
                        className='pt0 pb3 w-100 protein-function-container'
                        style={{height: 175, overflow: 'auto', lineHeight: 1.33}}>
                        <div>
                            <p>{uniprotMetadata[this.state.targetName]?.uniprot_function}</p>
                        </div>
                    </div>


                    <div className="pt4 bb b--black-10">
                        <div className="f3 container-header">Expression level</div>
                    </div>

                    {/* tpm-GFP scatterplot*/}
                    <div 
                        className="fl pt3 pb3 w-100 expression-plot-container" 
                        style={{marginLeft: -20, marginTop: 0}}>
                        <ExpressionPlot targetName={this.state.targetName}/>
                    </div>


                    {/* 
                    <div className="bb b--black-10">
                        <div className="f3 container-header">FACS histograms</div>
                    </div> 
                    */}

                    {/* FACS plot controls */}
                    {/* <div className="pt3 pb2">

                        <div className='fl w-100 pb3'>
                            <div className='dib pr4'>
                                <ButtonGroup 
                                    label='GFP-positive population' 
                                    values={['On', 'Off']}
                                    activeValue={this.state.facsShowGFP}
                                    onClick={value => this.setState({facsShowGFP: value})}/>
                            </div>
                            <div className='dib pr4'>
                                <ButtonGroup 
                                    label='Annotations' 
                                    values={['On', 'Off']}
                                    activeValue={this.state.facsShowAnnotations}
                                    onClick={value => this.setState({facsShowAnnotations: value})}/>
                            </div>
                        </div>
                    </div> */}


                    {/* FACS plot itself*/}
                    {/*
                    <div 
                        className="fl pt3 w-100 facs-container" 
                        style={{marginLeft: -20, marginTop: 0}}>
                        <FACSPlot 
                            width={400}
                            height={300}
                            isSparkline={false}
                            showGFP={this.state.facsShowGFP=='On'}
                            targetName={this.state.targetName}
                            data={pipelineMetadata[this.state.targetName].facs_histograms}/>
                    </div>
                    */}
                </div>



                {/* microscopy - slice-viz and volume-viz modes */}
                {/* note that the 'fl' is required here for 'dib' to work*/}
                <div className="fl w-40 dib pl3 pr4">
                    <div className="bb b--black-10">
                        <div className="f3 container-header">Localization</div>
                    </div>

                    {/* display controls */}
                    <div className="pt3 pb2">

                        {/* Top row - display mode and channel */}
                        <div className='fl w-100 pb3'>
                            <div className='dib pr4'>
                                <ButtonGroup 
                                    label='Mode' 
                                    values={['Slice', 'Volume']}
                                    activeValue={this.state.localizationMode}
                                    onClick={value => this.setState({localizationMode: value})}/>
                            </div>
                            <div className='dib pr4'>
                                <ButtonGroup 
                                    label='Channel' 
                                    values={['DAPI', 'GFP', 'Both']}
                                    activeValue={this.state.localizationChannel}
                                    onClick={value => this.setState({localizationChannel: value})}/>
                            </div>
                        </div>
                    </div>

                    {/* slice viewer or volume rendering */}
                    <div className="fl">
                        {localizationContent}
                    </div>

                    {/* Localization controls - min/max/z-index sliders */}
                    <div className='fl w-90 pt3'>
                        <div className='w-50 dib'>
                            <div className=''>DAPI range</div>
                            <Slider 
                                label='Min'
                                min={0} max={100} value={this.state.dapiMin}
                                onChange={value => this.setState({dapiMin: value})}/>
                            <Slider 
                                label='Max'
                                min={0} max={100} value={this.state.dapiMax}
                                onChange={value => this.setState({dapiMax: value})}/>
                        </div>

                        <div className='w-50 dib'>
                            <div className=''>GFP range</div>
                            <Slider 
                                label='Min'
                                min={0} max={100} value={this.state.gfpMin}
                                onChange={value => this.setState({gfpMin: value})}/>
                            <Slider 
                                label='Max'
                                min={0} max={100} value={this.state.gfpMax}
                                onChange={value => this.setState({gfpMax: value})}/>
                        </div>
                        <div className='w-100 pt2'>
                            <div className=''>Z-slice</div>
                            <Slider 
                                label='z-index'
                                min={0} max={100} value={this.state.zIndex}
                                onChange={value => this.setState({zIndex: value})}/>
                        </div>
                    </div>
                </div>



                {/* mass spec data (scatter plot and list of interactors) */}
                <div className="fl w-33 dib pl3">
    
                    <div className="bb b--black-10">
                        <div className="f3 container-header">Interactions</div>
                    </div>

                    {/* display controls */}
                    <div className="pt3 pb2">

                        {/* Top row - scatterplot controls */}
                        <div className='fl w-100 pb3'>
                            <div className='dib pr4'>
                                <ButtonGroup 
                                    label='Label color' 
                                    values={['Significance', 'Function']}
                                    activeValue={this.state.volcanoLabelColor}
                                    onClick={value => this.setState({volcanoLabelColor: value})}/>
                            </div>
                            <div className='dib pr4'>
                                <ButtonGroup 
                                    label='Show labels' 
                                    values={['Always', 'Never', 'On zoom']}
                                    activeValue={this.state.volcanoShowLabels}
                                    onClick={value => this.setState({volcanoShowLabels: value})}/>
                            </div>
                            <div className='fr dib'>
                                <div 
                                    className='f6 simple-button' 
                                    onClick={() => this.setState({volcanoResetZoom: !this.state.volcanoResetZoom})}>
                                    {'Reset zoom'}
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* volcano plot
                    the hack-ish absolute margins here are to better align the svg itself*/}
                    <div className="fl w-100 scatterplot-container" style={{marginLeft: -20, marginTop: 10}}>
                        <VolcanoPlot
                            enrichmentAccessor={row => parseFloat(row.enrichment)}
                            pvalueAccessor={row => parseFloat(row.pvalue)}
                            targetName={this.state.targetName}
                            changeTarget={this.onSearchChange}
                            showLabels={this.state.volcanoShowLabels}
                            resetZoom={this.state.volcanoResetZoom}
                            labelColor={this.state.volcanoLabelColor}
                        />
                    </div>
                    {/* table of top MS hits */}
                    <div className='fl w-100' style={{visibility: 'hidden'}}>
                        <div className='f3 container-header'>Top hits</div>
                        <ReactTable
                            pageSize={5}
                            filterable={false}
                            showPagination={false}
                            columns={[
                                {
                                    Header: 'Gene ID',
                                    accessor: 'gene_id',
                                },{
                                    id: 'enrichment',
                                    Header: 'Enrichment',
                                    accessor: row => parseFloat(row.enrichment).toFixed(2),
                                },{
                                    id: 'pvalue',
                                    Header: '-log p-value',
                                    accessor: row => parseFloat(row.pvalue).toFixed(2),
                                }
                            ]}
                            data={msData.filter(d => d.target_name==this.state.targetName)[0]?.hits}
                        />
                    </div>
                </div>



                {/* table of all targets */}
                <div className="fl w-90 pt0 pl4 pb5">

                    <div className="">
                        <div className="f3 container-header">All cell lines</div>
                    </div>
        
                    <ReactTable 
                        pageSize={10}
                        showPageSizeOptions={false}
                        filterable={true}
                        columns={tableDefs}
                        data={this.allTargetNames.map(name => {
                            return {
                                targetName: name, 
                                isActive: this.state.targetName===name
                            };
                        })}
                        getTrProps={(state, rowInfo, column) => {
                            const isActive = rowInfo ? rowInfo.original.isActive : false;
                            return {
                                onClick: () => this.onSearchChange(rowInfo.original.targetName),
                                style: {
                                    background: isActive ? '#ddd' : null,
                                    fontWeight: isActive ? 'bold' : 'normal'
                                }
                            }
                        }}
                        getPaginationProps={(state, rowInfo, column) => {
                            return {
                              style: {fontSize: 16}
                            }
                          }}
                    />
                </div>

            </div>

            {this.state.appHasLoaded ? (null) : (<div className='loading-overlay'/>)}

            </div>

        );
    }
}


export default App;



