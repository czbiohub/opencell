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
    return roi && `FOV ${roi.fov_id} (ROI ${roi.id}) (${roi.kind[0].toUpperCase()})`
}

function roiItemRenderer (roi, props) {
    if (!props.modifiers.matchesPredicate) return null;
    return (
        <MenuItem
            key={roi.id}
            text={`FOV ${roi.fov_id}`}
            label={`(ROI ${roi.id}) (${roi.kind[0].toUpperCase()})`}
            active={props.modifiers.active}
            onClick={props.handleClick}
        />
    );
};


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
        
        if (!this.props.rois.length) return null;

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
                            activeItem={roi}
                            items={this.props.rois} 
                            itemRenderer={roiItemRenderer} 
                            filterable={false}
                            onItemSelect={roi => {
                                this.setState({stacksLoaded: false});
                                this.props.changeRoi(roi.id, roi.fov_id)}
                            }
                        >
                            <Button 
                                className="bp3-button-custom"
                                rightIcon="double-caret-vertical"
                                text={roiLabel(roi)}
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
            <MetadataContainer
                className='pt2'
                data={fov}
                definitions={fovMetadataDefinitions}
                orientation='row'
                scale={4}
            />

            {this.state.stacksLoaded ? (null) : (<div className='loading-overlay'/>)}

        </div>
        );

    };

}
