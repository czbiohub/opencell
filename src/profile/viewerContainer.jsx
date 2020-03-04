
import React, { Component } from 'react';
import { Button, MenuItem } from "@blueprintjs/core";
import { Select } from "@blueprintjs/select";

import Slider from './slider.jsx';
import ButtonGroup from './buttonGroup.jsx';
import SliceViewer from './sliceViewer.jsx';
import VolumeViewer from './volumeViewer.jsx';
import settings from '../common/settings.js';
import * as utils from '../common/utils.js';

import 'tachyons';
import './Profile.css';

function SectionHeader (props) {
    return (
        <div className="bb b--black-10">
            <div className="f3 section-header">{props.title}</div>
        </div>
    );
}

export default class ViewerContainer extends Component {

    constructor (props) {

        super(props);
        this.state = {

            stacksLoaded: false,

            // 'Volume' or 'Slice'
            localizationMode: 'Slice',

            // 'GFP' or 'DAPI' or 'Both'
            localizationChannel: 'Both',

            // initial slider values
            gfpMin: 0,
            gfpMax: 50,
            dapiMin: 5,
            dapiMax: 50,
            zIndex: 27, // the middle of the 55-slice stack
        };
    }


    componentDidUpdate(prevProps, prevState, snapshot) {
        // reload the z-stacks only if the roi has changed
        if (prevProps.roiId!==this.props.roiId) {
            this.loadStacks();
        }
    }


    loadStacks() {

        this.setState({stacksLoaded: false});

        const loadStack = (filepath) => {
            return new Promise((resolve, reject) => {
                utils.loadImage(filepath, volume => resolve(volume));
            });
        }

        if (!this.props.roiId) {
            this.setState({stacksLoaded: true});
            return;
        }

        // ***WARNING***
        // the order of the channels in the `filepaths` array below matters,
        // because it is *independently* hard-coded in SliceViewer and VolumeViewer
        const filepaths = [
            `${settings.apiUrl}/rois/405/crop/${this.props.roiId}`,
            `${settings.apiUrl}/rois/488/crop/${this.props.roiId}`,
        ];

        Promise.all(filepaths.map(loadStack)).then(volumes => {
            this.volumes = volumes;
            this.setState({stacksLoaded: true});
        });
    }


    render () {
        
        if (!this.props.fovs.length) return null;

        function renderROIItem (roi, props) {
            if (!props.modifiers.matchesPredicate) return null;
            return (
                <MenuItem
                    key={roi.id}
                    text={`FOV ${roi.fov_id}`}
                    label={`(ROI ${roi.id})`}
                    active={props.modifiers.active}
                    onClick={props.handleClick}
                />
            );
        };

        let localizationContent;
        if (this.state.localizationMode==='Volume') {
            localizationContent = <VolumeViewer volumes={this.volumes} {...this.state}/>
        }
        if (this.state.localizationMode==='Slice') {
            localizationContent = <SliceViewer volumes={this.volumes} {...this.state}/>
        }
        
        const fov = this.props.fovs.filter(fov => fov.id == this.props.fovId)[0];
        const allROIs = [...this.props.fovs[0].rois, ...this.props.fovs[1].rois];

        return (
            <div>

            {/* display controls */}
            <div className="pt3 pb2">
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
                            items={allROIs} 
                            itemRenderer={renderROIItem} 
                            filterable={false}
                            onItemSelect={roi => {
                                this.setState({stacksLoaded: false});
                                this.props.changeRoi(roi.id, roi.fov_id)}
                            }
                            activeItem={allROIs.filter(roi => roi.id === this.props.roiId)[0]}
                        >
                            <Button 
                                className="bp3-button-custom"
                                text={`FOV ${this.props.fovId} (ROI ${this.props.roiId})`}
                                rightIcon="double-caret-vertical"
                            />
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
                    <div className=''>DAPI range</div>
                    <Slider 
                        label='Min'
                        min={0} max={100} value={this.state.dapiMin}
                        onChange={value => this.setState({dapiMin: value})}/>
                    <Slider 
                        label='Max'
                        min={0} max={150} value={this.state.dapiMax}
                        onChange={value => this.setState({dapiMax: value})}/>
                </div>

                <div className='flex-0-0-auto w-50'>
                    <div className=''>GFP range</div>
                    <Slider 
                        label='Min'
                        min={0} max={100} value={this.state.gfpMin}
                        onChange={value => this.setState({gfpMin: value})}/>
                    <Slider 
                        label='Max'
                        min={0} max={150} value={this.state.gfpMax}
                        onChange={value => this.setState({gfpMax: value})}/>
                </div>

                <div className='flex-0-0-auto w-100 pt2'>
                    <div className=''>Z-slice</div>
                    <Slider 
                        label='z-index'
                        min={0} max={55} value={this.state.zIndex}
                        onChange={value => this.setState({zIndex: value})}/>
                </div>
            </div>
            
            <SectionHeader title='FOV metadata'/>
            <div className='flex pt2'>
                {FOVMetadataItem('Laser power', fov.laser_power_488?.toFixed(1) || 'NA', '%')}
                {FOVMetadataItem('Exposure time', fov.exposure_time_488?.toFixed() || 'NA', 'ms')}
                {FOVMetadataItem('Max intensity', fov.max_intensity_488 || 'NA', '')}
            </div>

            {this.state.stacksLoaded ? (null) : (<div className='loading-overlay'/>)}

        </div>
        );

    };

}


// warning: this is almost a direct copy of a function in header.jsx
function FOVMetadataItem(label, value, units) {
    return (
        <div className='flex-0-0-auto header-metadata-item'>
            <strong className='f4'>{value}</strong>
            <abbr className='f5' title='units description'>{units}</abbr>
            <div className='f6 header-metadata-item-label'>{label}</div>
        </div>
    );
}