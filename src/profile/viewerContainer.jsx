import React, { Component } from 'react';
import { Button, MenuItem, Slider, RangeSlider } from "@blueprintjs/core";
import { Select } from "@blueprintjs/select";
import classNames from 'classnames';

// import Slider from './slider.jsx';
import ButtonGroup from './buttonGroup.jsx';
import SliceViewer from './sliceViewer.jsx';
import VolumeViewer from './volumeViewer.jsx';
import settings from '../common/settings.js';
import * as utils from '../common/utils.js';
import { SectionHeader, MetadataContainer } from './common.jsx';
import { fovMetadataDefinitions } from './metadataDefinitions.js';

import 'tachyons';
import './Profile.css';


function Thumbnail (props) {
    const divClassName = classNames(
        'pa1 pr2 pl2', 'roi-thumbnail-container',
        {'roi-thumbnail-container-active': props.active}
    );

    return (
        <div className={divClassName} onClick={props.onClick}>
            <img 
                width={60}
                height={60}
                src={`data:image/jpg;base64,${props.thumbnail?.data}`}
            />
            <div className='roi-thumbnail-caption'>
                <span>{props.text}</span>
            </div>
        </div>
    );
}


function roiItemRenderer (roi, props) {
    if (!props.modifiers.matchesPredicate) return null;
    return (
        <Thumbnail
            key={roi.id}
            text={`FOV ${roi.fov_id}`}
            thumbnail={roi.thumbnail}
            active={props.modifiers.active}
            onClick={props.handleClick}
        />
    );
};


export default class ViewerContainer extends Component {
    static contextType = settings.ModeContext;

    constructor (props) {
        super(props);

        // the number of slices in the 2x-upsampled z-stacks
        this.numSlices = settings.numZSlices * 2 - 1;

        // default values for the display settings
        this.defaultDisplayState = {
            min488: 0,
            max488: 90,
            gamma488: 1.0,
            min405: 10,
            max405: 80,
            gamma405: 1.0,
        }

        this.defaultZoomState = {
            cameraPosition: {x: 300, y: 300},
            cameraZoom: 1,
        }

        this.state = {

            // 'Volume', 'Slice' or 'Proj'
            mode: "Proj",

            // '405', '488', or 'Both'
            channel: "Both",

            // 'Auto' or 'High'
            imageQuality: "Auto",

            // the middle of the z-stack
            zIndex: parseInt(this.numSlices/2),

            stacksLoaded: false,
            projsLoaded: false,
            shouldResetZoom: false,
        };
        this.state = {...this.defaultDisplayState, ...this.defaultZoomState, ...this.state};

        this.resetZoom = this.resetZoom.bind(this);
    }


    componentDidMount() {
        if (this.props.roiId) this.loadStacks();
    }

    componentDidUpdate(prevProps, prevState, snapshot) {

        if (
            prevProps.roiId!==this.props.roiId || 
            prevState.imageQuality!==this.state.imageQuality
        ) this.loadStacks();

        // reset the camera zoom and the GFP black point if the target has changed
        // (because the black point is different for low-GFP targets)
        if (prevProps.cellLineId!==this.props.cellLineId) {
            this.setState({min488: this.props.isLowGfp ? 10 : 0,});
            this.resetZoom();
        }
    }


    loadStacks() {

        this.setState({stacksLoaded: false, projsLoaded: false});

        const loadStack = (filepath) => {
            return new Promise((resolve, reject) => {
                utils.getZStack(filepath, data => resolve(data));
            });
        }

        const loadProj = (filepath) => {
            return new Promise((resolve, reject) => {
                utils.getZProjection(filepath, data => resolve(data));
            });
        }

        if (!this.props.roiId) {
            this.setState({stacksLoaded: true});
            return;
        }

        // ***WARNING***
        // the order of the channels in the `filepaths` array below matters,
        // because it is *independently* hard-coded in SliceViewer and VolumeViewer
        const quality = this.state.imageQuality==='Auto' ? 'lqtile' : 'hqtile';
        const stackFilepaths = [
            `${settings.apiUrl}/rois/${this.props.roiId}/${quality}/405`,
            `${settings.apiUrl}/rois/${this.props.roiId}/${quality}/488`,
        ];
        Promise.all(stackFilepaths.map(loadStack)).then(volumes => {
            this.volumes = volumes;
            this.setState({stacksLoaded: true});
        });

        // load the z-projections
        const projFilepaths = [
            `${settings.apiUrl}/rois/${this.props.roiId}/proj/405`,
            `${settings.apiUrl}/rois/${this.props.roiId}/proj/488`,
        ];
        Promise.all(projFilepaths.map(loadProj)).then(projs => {
            this.projs = projs;
            this.setState({projsLoaded: true});
        });
    }


    resetZoom() {
        this.setState({shouldResetZoom: true, ...this.defaultZoomState});
    }


    render () {
        

        const zIndexToMicrons = (index) => {
            const micronsPerSlice = 0.4;
            return (index * micronsPerSlice).toFixed(1);
        }

        if (!this.props.rois.length) {
            return (
                <div className="relative" style={{height: "500px"}}>
                    <div className="f2 tc loading-overlay">No ROIs found</div>
                </div>
            );
        }

        let viewer;
        if (this.state.mode==='Volume') {
            viewer = <VolumeViewer 
                {...this.state} 
                volumes={this.volumes}
                setCameraZoom={cameraZoom => this.setState({cameraZoom})}
                setCameraPosition={cameraPosition => this.setState({cameraPosition})}
                didResetZoom={() => this.setState({shouldResetZoom: false})}
            />
        }
        else {
            let volumes, loaded;
            if (this.state.mode==='Slice') {
                volumes = this.volumes;
                loaded = this.state.stacksLoaded;
            }
            else if (this.state.mode==='Proj') {
                volumes = this.projs;
                loaded = this.state.projsLoaded;
            }
            viewer = (
                <SliceViewer 
                    {...this.state}
                    volumes={volumes} 
                    loaded={loaded} 
                    setCameraZoom={cameraZoom => this.setState({cameraZoom})}
                    setCameraPosition={cameraPosition => this.setState({cameraPosition})}
                    didResetZoom={() => this.setState({shouldResetZoom: false})}
                />
            );
        }

        // the current FOV and ROI
        const fov = this.props.fovs.filter(fov => fov.metadata.id == this.props.fovId)[0];
        const roi = this.props.rois.filter(roi => roi.id == this.props.roiId)[0];
    
        return (
            // use relative position so that the loading-overlay div only overlays this component
            <div className='relative'>

            {/* display controls */}
            <div className="pt3 pb2">

                {/* top row */}
                <div className='flex flex-wrap w-100 pb2'>

                    <div className="roi-thumbnail-select-container pr3">
                        <Select 
                        className={'roi-select'}
                            activeItem={roi}
                            items={this.props.rois} 
                            itemRenderer={roiItemRenderer} 
                            itemListRenderer={props => {
                                return (
                                    <div className="roi-select-menu-container">
                                        {props.items.map(props.renderItem)}
                                    </div>
                                );
                            }}
                            filterable={false}
                            onItemSelect={roi => {
                                this.props.changeRoi(roi.id, roi.fov_id);
                                this.resetZoom();
                            }}
                        >
                            <div className='simple-button-group'>
                                <div className="simple-button-group-label">Select FOV</div>
                                <Button 
                                    className="bp3-button-custom"
                                    rightIcon="double-caret-vertical"
                                    text={`FOV ${roi.fov_id}`}
                                />
                            </div>
                        </Select>
                    </div>

                    <div className='pr3'>
                        <ButtonGroup 
                            label='Image quality' 
                            values={['Auto', 'High']}
                            activeValue={this.state.imageQuality}
                            onClick={value => this.setState({imageQuality: value})}
                            disabled={this.state.mode==='Proj'}
                        />
                    </div>
                    <div className='pr3'>
                        <ButtonGroup 
                            label='Channel' 
                            values={['405', '488', 'Both']}
                            labels={['DNA', 'Protein', 'Both']}
                            activeValue={this.state.channel}
                            onClick={value => this.setState({channel: value})}
                        />
                    </div>
                </div>
                    
                {/* bottom row of controls */}
                <div className='flex items-center w-100' style={{justifyContent: 'space-between'}}>
                    <div className='flex'>
                        <ButtonGroup 
                            label='' 
                            values={['Proj', 'Slice', 'Volume']}
                            labels={['Z-projection', 'Z-slice', 'Volume rendering']}
                            activeValue={this.state.mode}
                            onClick={value => this.setState({mode: value})}
                        />
                    </div>
                    
                    <div className='flex' style={{alignSelf: 'flex-end'}}>
                        <Button
                            className="bp3-button-custom"
                            text={"Reset zoom"}
                            onClick={() => this.resetZoom()}
                        />
                        <Button
                            className="ml2 bp3-button-custom"
                            text={"Reset display settings"}
                            onClick={() => this.setState({...this.defaultDisplayState})}
                        />
                    </div>
                </div>
            </div>

            {/* the z-slice viewer or volume rendering */}
            <div className="fl">{viewer}</div>

            {/* Display settings */}
            <div className='flex flex-wrap w-100 pt2 pb2'>

                {/* z-index slider */}
                <div className='w-100 flex flex-0-0-auto pr3'>
                    <div className={classNames('w-30', {'black-30': this.state.mode!=='Slice'})}>
                        <b>
                        {`Z-position: ${zIndexToMicrons(this.state.zIndex)}`}
                        <span>&micro;m</span>
                        </b>
                    </div>
                    <Slider 
                        min={0} 
                        max={this.numSlices - 1} 
                        stepSize={1}
                        labelStepSize={50}
                        showTrackFill={false}
                        disabled={this.state.mode!=='Slice'}
                        value={this.state.zIndex}
                        onChange={value => this.setState({zIndex: parseInt(value)})}
                    />
                </div>

                {/* 405 min/max/gamma */}
                <div className='flex-0-0-auto w-50 pr4'>
                    <div className='pb1'>
                        {`DNA intensity range: ${this.state.min405}% to ${this.state.max405}%`}
                    </div>
                    <RangeSlider 
                        min={0} 
                        max={150} 
                        stepSize={1}
                        labelStepSize={50}
                        labelRenderer={value => String(Math.round(value))}
                        value={[this.state.min405, this.state.max405]}
                        onChange={values => this.setState({min405: values[0], max405: values[1]})}
                    />
                    <div className='pb1'>
                        {`DNA intensity gamma: ${this.state.gamma405.toFixed(2)}`}
                    </div>
                    <Slider
                        min={0.5} 
                        max={1.5} 
                        stepSize={0.05} 
                        labelStepSize={0.5}
                        showTrackFill={false}
                        value={this.state.gamma405}
                        onChange={value => this.setState({gamma405: parseFloat(value)})}
                    />
                </div>

                {/* 488 min/max/gamma */}
                <div className='flex-0-0-auto w-50 pl1 pr3'>
                    <div className='pb1'>
                        {`Protein intensity range: ${this.state.min488}% to ${this.state.max488}%`}
                    </div>
                    <RangeSlider 
                        min={0} 
                        max={150} 
                        stepSize={1}
                        labelStepSize={50}
                        labelRenderer={value => String(Math.round(value))}
                        value={[this.state.min488, this.state.max488]}
                        onChange={values => this.setState({min488: values[0], max488: values[1]})}
                    />
                    <div className='pb1'>
                        {`Protein intensity gamma: ${this.state.gamma488.toFixed(2)}`}
                    </div>
                    <Slider
                        min={0.5} 
                        max={1.5} 
                        stepSize={0.05} 
                        labelStepSize={0.5}
                        showTrackFill={false}
                        value={this.state.gamma488}
                        onChange={value => this.setState({gamma488: parseFloat(value)})}
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

            {(
                this.state.stacksLoaded || (this.state.projsLoaded && this.state.mode==='Proj')
            ) ? (
                null
            ) : (
                <div className="f2 tc loading-overlay">Loading...</div>
            )}

        </div>
        );

    };

}
