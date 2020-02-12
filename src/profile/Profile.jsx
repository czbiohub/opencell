
import * as d3 from 'd3';
import React, { Component } from 'react';
import ReactTable from 'react-table';

import { Button, Radio, RadioGroup, MenuItem } from "@blueprintjs/core";
import { Select } from "@blueprintjs/select";

import Slider from './slider.jsx';
import ButtonGroup from './buttonGroup.jsx';

import Navbar from '../common/navbar.jsx';
import Header from './header.jsx';

import SliceViz from './sliceViz.jsx';
import VolumeViz from './volumeViz.jsx';
import FACSPlot from '../common/facsPlot.jsx';
import ExpressionPlot from '../common/expressionPlot.jsx';
import AnnotationsForm from './annotations.jsx';
import VolcanoPlotContainer from './volcanoPlotContainer.jsx';

import 'tachyons';
import 'react-table/react-table.css';
import "@blueprintjs/core/lib/css/blueprint.css";

import { metadataDefinitions } from './definitions.js';
import manualMetadata from '../demo/data/manual_metadata.json';
import uniprotMetadata from '../demo/data/uniprot_metadata.json';

import settings from '../common/settings.js';

import '../common/common.css';
import './Profile.css';


class App extends Component {

    constructor (props) {
        super(props);

        this.apiUrl = settings.apiRoot;
        this.urlParams = new URLSearchParams(window.location.search);

        this.state = {

            linesLoaded: false,
            stacksLoaded: false,
            
            roiId: null,
            cellLineId: null,
            targetName: null,

            // 'Volume' or 'Slice'
            localizationMode: 'Slice',

            // 'GFP' or 'DAPI' or 'Both'
            localizationChannel: 'Both',

            // 'Volcano' or 'Table'
            msDisplayMode: 'Volcano',

            // 'None', 'Family', 'Status'
            msColorMode: 'Status',

            // whether to plot the GFP-positive population
            facsShowGFP: 'On',

            // whether to show the annotations (median/max intensity etc)
            facsShowAnnotations: 'On',

            // HACK: these values must match the initial values hard-coded in the sliders below
            gfpMin: 0,
            gfpMax: 50,
            dapiMin: 5,
            dapiMax: 50,
            zIndex: 30,

        };


        this.changeTarget = this.changeTarget.bind(this);
        this.onSearchChange = this.onSearchChange.bind(this);

        this.allCellLines = [];
        this.cellLine = {};
        this.rois = [];
    
    }


    changeTarget (cellLine) {
        
        const targetName = cellLine.target_name;

        // check that the target has changed
        if (targetName===this.state.targetName) return;

        const rois = [...cellLine.fovs[0].rois, ...cellLine.fovs[1].rois];

        this.rois = rois;
        this.cellLine = cellLine;

        // reset stacksLoaded to false, since we now need to load new z-stacks
        this.setState({
            targetName,
            cellLineId: cellLine.cell_line_id,
            roiId: rois[0].id,
            stacksLoaded: false, 
            gfpMax: manualMetadata[targetName]?.gfp_max || 50,
        });
    }


    onSearchChange (value) {
        // fired when the user hits enter in the header's target search text input
        // `value` is the value of the input

        let url = `${this.apiUrl}/lines?target_name=${value}&kind=all`;
        d3.json(url).then(lines => {
            for (const line of lines) {
                if (line && line.fovs.length) {
                    this.changeTarget(line);
                    break;
                }
            }
        });
    }


    loadImage(url, onLoad) {

        // hard-coded xy size and number of z-slices
        // WARNING: these must match the stack to be loaded
        const imageSize = 600;
        const numSlices = 65;

        const imageWidth = imageSize;
        const imageHeight = imageSize*numSlices;

        const volume = {
            xLength: imageSize,
            yLength: imageSize,
            zLength: numSlices,
            data: new Uint8Array(imageWidth*imageHeight),
        };

        const img = new Image;

        // this is required to avoid the 'tainted canvas' error
        img.setAttribute('crossOrigin', '');

        img.onload = function () {
            const canvas = document.createElement('canvas');
            const context = canvas.getContext('2d');
            canvas.setAttribute('width', imageWidth);
            canvas.setAttribute('height', imageHeight);
            context.drawImage(img, 0, 0);

            const imageData = context.getImageData(0, 0, imageWidth, imageHeight);
            for (let ind = 0; ind < volume.data.length; ind++) {
                volume.data[ind] = imageData.data[ind*4];
            }
            
            onLoad(volume);
        };

        img.src = url;

    }


    loadStacks() {

        const loadStack = (filepath) => {
            return new Promise((resolve, reject) => {
                this.loadImage(filepath, volume => resolve(volume));
            });
        }

        if (!this.state.roiId) {
            this.setState({stacksLoaded: true});
            return;
        }

        // ***WARNING***
        // the order of the channels in the `filepaths` array below matters,
        // because it is *independently* hard-coded in SliceViz and VolumeViz
        const filepaths = [
            `${this.apiUrl}/rois/405/crop/${this.state.roiId}`,
            `${this.apiUrl}/rois/488/crop/${this.state.roiId}`,
        ];

        Promise.all(filepaths.map(loadStack)).then(volumes => {
            this.volumes = volumes;
            this.setState({stacksLoaded: true});
        });
    }


    componentDidMount() {

        let url = `${this.apiUrl}/lines`;
        d3.json(url).then(lines => {
            this.allCellLines = lines;     
            this.setState({linesLoaded: true});
        });

        // initial target to display
        this.onSearchChange(this.urlParams.get('target') || 'LMNB1');
        
    }


    componentDidUpdate(prevProps, prevState, snapshot) {
        // reload the z-stacks only if the roi has changed
        if (prevState.roiId!==this.state.roiId) {
            this.loadStacks();
        }
    }


    render() {

        function renderROIItem (roi, props) {
            if (!props.modifiers.matchesPredicate) return null;
            return (
                <MenuItem
                    key={roi.id}
                    text={`ROI ${roi.id}`}
                    label={`(FOV ${roi.fov_id})`}
                    active={props.modifiers.active}
                    onClick={props.handleClick}
                />
            );
        };

        let localizationContent;
        if (this.state.localizationMode==='Volume') {
            localizationContent = <VolumeViz volumes={this.volumes} {...this.state}/>
        }
        if (this.state.localizationMode==='Slice') {
            localizationContent = <SliceViz volumes={this.volumes} {...this.state}/>
        }

        // append gene_name to metadataDefinitions 
        // (used only for the table of all targets at the bottom)
        let tableDefs = [
            {   
                id: 'gene_name',
                Header: 'Gene name',
                accessor: row => row.target_name,
            },
            ...metadataDefinitions,
        ];


        return (

            <div>
            <Navbar/>

            {/* main container */}
            <div className="w-100 pl4 pr4">

                {/* page header and metadata */}
                <Header cellLine={this.cellLine} onSearchChange={this.onSearchChange}/>

                {/* Expression scatterplot and FACS histograms */}
                <div className="fl w-25 dib pl3 pr4 pt0">

                    <div className="bb b--black-10">
                        <div className="f3 container-header">About this protein</div>
                    </div>

                    <div
                        className='pt0 pb3 w-100 protein-function-container'
                        style={{height: 100, overflow: 'auto', lineHeight: 1.33}}>
                        <div>
                            <p>{uniprotMetadata[this.state.targetName]?.uniprot_function}</p>
                        </div>
                    </div>


                    {/* expression scatterplot*/}
                    <div className="pt4 bb b--black-10">
                        <div className="f3 container-header">Expression level</div>
                    </div>
                    <div 
                        className="fl pt3 pb3 w-100 expression-plot-container" 
                        style={{marginLeft: -20, marginTop: 0}}>
                        <ExpressionPlot targetName={this.state.targetName}/>
                    </div>


                    <div className="bb b--black-10">
                        <div className="f3 container-header">FACS histograms</div>
                    </div> 
                   
                    {/* FACS plot controls */}
                    <div className="pt3 pb2">
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
                    </div>

                    {/* FACS plot itself*/}
                    <div 
                        className="fl pt3 w-100 facs-container" 
                        style={{marginLeft: -20, marginTop: -20}}>
                        <FACSPlot 
                            width={400}
                            height={300}
                            isSparkline={false}
                            cellLineId={this.state.cellLineId}
                            showGFP={this.state.facsShowGFP==='On'}/>
                    </div>
                   
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
                            <div className="dib pr3">
                                <Select 
                                    items={this.rois} 
                                    itemRenderer={renderROIItem} 
                                    filterable={false}
                                    onItemSelect={roi => this.setState({stacksLoaded: false, roiId: roi.id})}
                                    activeItem={this.rois.filter(roi => roi.id === this.state.roiId)[0]}
                                >
                                    <Button 
                                        className="bp3-button-custom"
                                        text={`ROI ${this.state.roiId}`}
                                        rightIcon="double-caret-vertical"/>
                                </Select>
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


                {this.urlParams.get('annotations')!=='yes' ? (

                    <div className="fl w-33 dib pl3">
                        <div className="bb b--black-10">
                            <div className="f3 container-header">Interactions</div>
                        </div>
                        <VolcanoPlotContainer
                            targetName={this.state.targetName}
                            changeTarget={name => this.onSearchChange(name)}
                        />
                    </div>

                ) : (

                    <div className="fl w-33 dib pl3 pb3">
                        <div className="bb b--black-10">
                            <div className="f3 container-header">Annotations</div>
                        </div>       
                        {/* note that fovIds should include only the *displayed* FOVs */}
                        <AnnotationsForm 
                            cellLineId={this.state.cellLineId} 
                            fovIds={this.rois.map(roi => roi.fov_id)}
                        />
                    </div>

                )}


                {/* table of all targets */}
                <div className="fl w-90 pt0 pl4 pb5">

                    <div className="">
                        <div className="f3 container-header">All cell lines</div>
                    </div>
        
                    <ReactTable 
                        pageSize={50}
                        showPageSizeOptions={false}
                        filterable={true}
                        columns={tableDefs}
                        data={this.allCellLines.map(line => {
                            return {...line, isActive: this.state.targetName===line.target_name};
                        })}
                        getTrProps={(state, rowInfo, column) => {
                            const isActive = rowInfo ? rowInfo.original.isActive : false;
                            return {
                                onClick: () => this.onSearchChange(rowInfo.original.target_name),
                                style: {
                                    background: isActive ? '#ddd' : null,
                                    fontWeight: isActive ? 'bold' : 'normal'
                                }
                            }
                        }}
                        getPaginationProps={(state, rowInfo, column) => {
                            return {style: {fontSize: 16}}
                          }}
                    />
                </div>

            </div>

            {this.state.linesLoaded & this.state.stacksLoaded ? (null) : (<div className='loading-overlay'/>)}

            </div>

        );
    }
}


export default App;



