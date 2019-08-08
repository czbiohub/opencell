
import * as d3 from 'd3';
import React, { Component } from 'react';
import ReactTable from 'react-table';

import ButtonGroup from './buttonGroup.jsx';
import Slider from './slider.jsx';

import Navbar from '../common/navbar.jsx';

import Header from './header.jsx';
import SliceViz from './sliceViz.jsx';
import VolumeViz from './volumeViz.jsx';
import ScatterPlot from './scatterPlot.jsx';
import FACSPlot from '../common/facsPlot.jsx';

import 'tachyons';
import 'react-table/react-table.css';

import { NRRDLoader } from 'three/examples/jsm/loaders/NRRDLoader';
import { metadataDefinitions } from './definitions.js';

import msData from './data/ms_data.json';
import nrrdFilepaths from './data/nrrd_filepaths.json';
import manualMetadata from './data/manual_metadata.json';
import pipelineMetadata from './data/pipeline_metadata.json';

import '../common/common.css';
import './Demo.css';


class App extends Component {

    constructor (props) {
        super(props);

        this.state = {

            appHasLoaded: false,

            // default initial target
            targetName: 'ATL2',

            // 'Volume' or 'Slice'
            localizationMode: 'Slice',

            // 'GFP' or 'DAPI' or 'Both'
            localizationChannel: 'DAPI',

            // 'Volcano' or 'Table'
            msDisplayMode: 'Volcano',

            // 'None', 'Family', 'Status'
            msColorMode: 'Status',

            // HACK: these values must match the initial values hard-coded in the sliders below
            gfpMin: 0,
            gfpMax: 50,
            dapiMin: 5,
            dapiMax: 50,
            zIndex: 30,
        };

        this.changeTarget = this.changeTarget.bind(this);

        // the list of all targets for which we have data;
        // these target names should also all appear in manualMetadata
        this.allTargetNames = Object.keys(nrrdFilepaths);
    
    }


    changeTarget (targetName) {
        
        // check that the target has changed
        if (targetName===this.state.targetName) return;

        // check that we have both MS data and stacks for the target
        if (!msData.filter(d => d.target_name===targetName).length || !nrrdFilepaths[targetName]) return;

        // reset appHasLoaded to false, since we now need to load new NRRD files
        this.setState({appHasLoaded: false, targetName});

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
        const fileroot = nrrdFilepaths[this.state.targetName];
        const filepaths = [
            `./demo-data/stacks/${fileroot}_C0.nrrd`,  // DAPI
            `./demo-data/stacks/${fileroot}_C1.nrrd`,  // GFP
        ];

        Promise.all(filepaths.map(loadStack)).then(volumes => {
            this.volumes = volumes;
            this.setState({appHasLoaded: true});
        });
    }

    
    componentDidMount() {
        // load the NRRD files
        this.loadStacks();
    }

    
    componentDidUpdate(prevProps, prevState, snapshot) {

        // reload the NRRD files
        if (prevState.targetName!==this.state.targetName) {
            this.loadStacks();
        }
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

        return (
            // main container
            <div>
            
            <Navbar/>

            {/* full-bleed navbar
            <div className="w-100 pa2 bg-black-10 f3">
                <div className='dib f3 pr4'>OpenCell v0.0.1</div>

                <div className='fr pt2 dib f5'>
                    <div className='dib pl3 pr3' style={{borderRight: '1px solid #aaa'}}>Home</div>
                    <div className='dib pl3 pr3' style={{borderRight: '1px solid #aaa'}}><strong>Database</strong></div>
                    <div className='dib pl3 pr3'>About</div>
                </div>
            </div> */}


            <div className="w-100 pl4 pr4">

                {/* page header and metadata */}
                <Header targetName={this.state.targetName}/>

                {/* microscopy - slice-viz and volume-viz modes */}
                {/* note that the 'fl' is required here for 'dib' to work*/}
                <div className="fl w-40 dib pr3">
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
                                min={0} max={100} initialValue={5}
                                onChange={value => this.setState({dapiMin: value})}/>
                            <Slider 
                                label='Max'
                                min={0} max={100} initialValue={50}
                                onChange={value => this.setState({dapiMax: value})}/>
                        </div>

                        <div className='w-50 dib'>
                            <div className=''>GFP range</div>
                            <Slider 
                                label='Min'
                                min={0} max={100} initialValue={0}
                                onChange={value => this.setState({gfpMin: value})}/>
                            <Slider 
                                label='Max'
                                min={0} max={100} initialValue={50}
                                onChange={value => this.setState({gfpMax: value})}/>
                        </div>
                        <div className='w-100 pt2'>
                            <div className=''>Z-slice</div>
                            <Slider 
                                label='z-index'
                                min={0} max={100} initialValue={30}
                                onChange={value => this.setState({zIndex: value})}/>
                        </div>
                    </div>
                </div>

                {/* mass spec data (scatter plot and list of interactors) */}
                <div className="fl w-30 dib pl3">
    
                    <div className="bb b--black-10">
                        <div className="f3 container-header">Interactions</div>
                    </div>

                    {/* display controls */}
                    <div className="pt3 pb2">

                        {/* Top row - scatterplot controls */}
                        <div className='fl w-100 pb3'>
                            <div className='dib pr4'>
                                <ButtonGroup 
                                    label='Mode' 
                                    values={['Volcano', 'Network']}
                                    activeValue={this.state.msDisplayMode}
                                    onClick={value => this.setState({msDisplayMode: value})}/>
                            </div>
                            <div className='dib pr4'>
                                <ButtonGroup 
                                    label='Color by' 
                                    values={['None', 'Family', 'Status']}
                                    activeValue={this.state.msColorMode}
                                    onClick={value => this.setState({msColorMode: value})}/>
                            </div>
                        </div>
                    </div>

                    {/* volcano plot
                    the hack-ish absolute margins here are to better align the svg itself*/}
                    <div className="fl w-100 scatterplot-container" style={{marginLeft: -40, marginTop: -10}}>
                        <ScatterPlot
                            xAccessor={row => row.enrichment}
                            yAccessor={row => row.pvalue}
                            xDomain={[-15, 15]}
                            yDomain={[0, 20]}
                            targetName={this.state.targetName}
                            changeTarget={this.changeTarget}
                        />
                    </div>
                    {/* table of top MS hits */}
                    <div className='fl w-100'>
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
                                    accessor: row => row.enrichment.toFixed(2),
                                },{
                                    id: 'pvalue',
                                    Header: 'p-value (-log)',
                                    accessor: row => row.pvalue.toFixed(2),
                                }
                            ]}
                            data={msData.filter(d => d.target_name==this.state.targetName)[0].hits}
                        />
                    </div>
                </div>


                {/* FACS plot */}
                <div className="fl w-30 dib pl3">
    
                    <div className="bb b--black-10">
                        <div className="f3 container-header">FACS</div>
                    </div>

                    {/* FACS plot itself*/}
                    <div className="fl pt3 w-100">
                        <FACSPlot 
                            width={400}
                            data={pipelineMetadata[this.state.targetName].facs_histograms}/>
                    </div>
                </div>


                {/* table of all targets */}
                <div className="fl w-100 pt4 pr3">

                    <div className="">
                        <div className="f3 container-header">All tagged genes</div>
                    </div>
        
                    <ReactTable 
                        pageSize={10}
                        filterable={false}
                        columns={metadataDefinitions}
                        data={this.allTargetNames.map(name => ({targetName: name, isActive: this.state.targetName===name}))}
                        getTrProps={(state, rowInfo, column) => {
                            return {
                                onClick: () => this.changeTarget(rowInfo.original.targetName)
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



