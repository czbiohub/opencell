import React, { Component } from 'react';
import { Button, MenuItem } from "@blueprintjs/core";
import { Select } from "@blueprintjs/select";

import Slider from './slider.jsx';
import ButtonGroup from './buttonGroup.jsx';
import SliceViewer from './sliceViewer.jsx';
import VolumeViewer from './volumeViewer.jsx';
import settings from '../common/settings.js';
import * as utils from '../common/utils.js';
import { SectionHeader, MetadataContainer } from './common.jsx';
import { fovMetadataDefinitions } from './metadataDefinitions.js';

import 'tachyons';
import './Profile.css';

function roiLabel (roi) {
    return roi && `FOV ${roi.fov_id} (${roi.kind[0].toUpperCase()})`
}

function roiItemRenderer (roi, props) {
    if (!props.modifiers.matchesPredicate) return null;
    return (
        <MenuItem
            key={roi.id}
            text={`FOV ${roi.fov_id}`}
            label={`(${roi.kind[0].toUpperCase()})`}
            active={props.modifiers.active}
            onClick={props.handleClick}
        />
    );
};


export default class ViewerContainer extends Component {

    constructor (props) {
        super(props);

        // the number of slices in the 2x-upsampled z-stacks
        this.numSlices = settings.numZSlices * 2 - 1;

        // default values for the display settings
        this.defaultDisplayState = {
            gfpMin: 0,
            gfpMax: 50,
            gfpGamma: 1,
            dapiMin: 5,
            dapiMax: 50,
            dapiGamma: 1,
        }

        this.state = {

            stacksLoaded: false,

            // 'Volume' or 'Slice'
            localizationMode: "Slice",

            // 'GFP', 'DAPI', or 'Both'
            localizationChannel: "Both",

            imageQuality: "Low",

            // the middle of the z-stack
            zIndex: parseInt(this.numSlices/2),
        };

        this.state = {...this.defaultDisplayState, ...this.state};
    }


    componentDidUpdate(prevProps, prevState, snapshot) {

        if (prevProps.roiId!==this.props.roiId) this.loadStacks();
        if (prevState.imageQuality!==this.state.imageQuality) this.loadStacks();

        // reset the GFP black point if the target has changed
        // (because the black point is different for low-GFP targets)
        if (prevProps.cellLineId!==this.props.cellLineId) {
            this.setState({gfpMin: this.props.isLowGfp ? 10 : 0});
        }
    }


    loadStacks() {

        this.setState({stacksLoaded: false});

        const loadStack = (filepath) => {
            return new Promise((resolve, reject) => {
                utils.loadStack(filepath, volume => resolve(volume));
            });
        }

        if (!this.props.roiId) {
            this.setState({stacksLoaded: true});
            return;
        }

        // ***WARNING***
        // the order of the channels in the `filepaths` array below matters,
        // because it is *independently* hard-coded in SliceViewer and VolumeViewer

        const quality = this.state.imageQuality==='Low' ? 'lqtile' : 'hqtile';
        const filepaths = [
            `${settings.apiUrl}/rois/${this.props.roiId}/${quality}/405`,
            `${settings.apiUrl}/rois/${this.props.roiId}/${quality}/488`,
        ];

        Promise.all(filepaths.map(loadStack)).then(volumes => {
            this.volumes = volumes;
            this.setState({stacksLoaded: true});
        });
    }


    render () {
        
        if (!this.props.rois.length) {
            return (
                <div className="relative" style={{height: "500px"}}>
                    <div className="f2 tc loading-overlay">No ROIs found</div>
                </div>
            );
        }

        let localizationContent;
        if (this.state.localizationMode==='Volume') {
            localizationContent = <VolumeViewer volumes={this.volumes} {...this.state}/>
        }
        if (this.state.localizationMode==='Slice') {
            localizationContent = <SliceViewer volumes={this.volumes} {...this.state}/>
        }

        // the current FOV and ROI
        const fov = this.props.fovs.filter(fov => fov.metadata.id == this.props.fovId)[0];
        const roi = this.props.rois.filter(roi => roi.id == this.props.roiId)[0];
    
        return (
            // use relative position so that the loading-overlay div only overlays this component
            <div className='relative'>

            {/* display controls */}
            <div className="pt3 pb2">
                <div className='fl w-100 pb3'>
                    <div className='dib pr3'>
                        <ButtonGroup 
                            label='Mode' 
                            values={['Slice', 'Volume']}
                            activeValue={this.state.localizationMode}
                            onClick={value => this.setState({localizationMode: value})}
                        />
                    </div>
                    <div className='dib pr3'>
                        <ButtonGroup 
                            label='Channel' 
                            values={['DAPI', 'GFP', 'Both']}
                            activeValue={this.state.localizationChannel}
                            onClick={value => this.setState({localizationChannel: value})}
                        />
                    </div>
                    <div className='dib pr3'>
                        <ButtonGroup 
                            label='Quality' 
                            values={['Low', 'High']}
                            activeValue={this.state.imageQuality}
                            onClick={value => this.setState({imageQuality: value})}
                        />
                    </div>
                    <div className="dib pr3">
                        <Select 
                            activeItem={roi}
                            items={this.props.rois} 
                            itemRenderer={roiItemRenderer} 
                            filterable={false}
                            onItemSelect={roi => {
                                this.props.changeRoi(roi.id, roi.fov_id)}
                            }
                        >
                            <div className='simple-button-group'>
                                <div className="simple-button-group-label">Select FOV</div>
                                <Button 
                                    className="bp3-button-custom"
                                    rightIcon="double-caret-vertical"
                                    text={roiLabel(roi)}
                                />
                            </div>
                        </Select>
                    </div>
                </div>
            </div>

            {/* slice viewer or volume rendering */}
            <div className="fl">
                {localizationContent}
            </div>

            {/* Localization controls - min/max/z-index sliders */}
            <div className='flex flex-wrap w-100 pt2 pb2'>
                <div className='flex-0-0-auto w-50'>
                    <div className=''>{`DAPI range: [${this.state.dapiMin}, ${this.state.dapiMax}]`}</div>
                    <Slider 
                        label='Min'
                        min={0} max={100} value={this.state.dapiMin}
                        onChange={value => this.setState({dapiMin: value})}/>
                    <Slider 
                        label='Max'
                        min={0} max={150} value={this.state.dapiMax}
                        onChange={value => this.setState({dapiMax: value})}/>

                    <div className='pt2'>{`DAPI gamma: ${this.state.dapiGamma.toFixed(2)}`}</div>                    
                    <Slider 
                        label='Gamma'
                        min={.5} max={2} step={0.05} value={this.state.dapiGamma}
                        onChange={value => this.setState({dapiGamma: parseFloat(value)})}/>
                </div>

                <div className='flex-0-0-auto w-50'>
                    <div className=''>{`GFP range: [${this.state.gfpMin}, ${this.state.gfpMax}]`}</div>
                    <Slider 
                        label='Min'
                        min={0} max={100} value={this.state.gfpMin}
                        onChange={value => this.setState({gfpMin: value})}/>
                    <Slider 
                        label='Max'
                        min={0} max={150} value={this.state.gfpMax}
                        onChange={value => this.setState({gfpMax: value})}/>

                    <div className='pt2'>{`GFP gamma: ${this.state.gfpGamma.toFixed(2)}`}</div>                    
                    <Slider 
                        label='Gamma'
                        min={.5} max={2} step={0.05} value={this.state.gfpGamma}
                        onChange={value => this.setState({gfpGamma: parseFloat(value)})}/>
                </div>

                <div className='flex-0-0-auto w-100 pt2'>
                    <div className=''>{`Z-slice: ${this.state.zIndex + 1}/${this.numSlices}`}</div>
                    <Slider 
                        label='z-index'
                        min={0} max={this.numSlices - 1} value={this.state.zIndex}
                        onChange={value => this.setState({zIndex: parseInt(value)})}/>
                </div>
                <div className="dib pr3">
                    <Button
                        className="pl2 bp3-button-custom"
                        text={"Reset"}
                        onClick={() => this.setState({...this.defaultDisplayState})}
                    />
                </div>
            </div>
            
            {this.props.showMetadata ? (
                <div>
                    <SectionHeader title='FOV metadata'/>
                    <MetadataContainer
                        className='pt2'
                        data={fov}
                        definitions={fovMetadataDefinitions}
                        orientation='row'
                        scale={4}
                    />
                </div>
            ) : (
                null
            )}

            {this.state.stacksLoaded ? (
                null
            ) : (
                <div className="f2 tc loading-overlay">Loading...</div>
            )}

        </div>
        );

    };

}
