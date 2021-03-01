import * as d3 from 'd3';
import React, { Component } from 'react';

import classNames from 'classnames';
import { Button, Checkbox } from "@blueprintjs/core";

import 'tachyons';
import 'react-table/react-table.css';
import "@blueprintjs/core/lib/css/blueprint.css";

import settings from '../../settings/settings.js';
import * as utils from '../../utils/utils.js';
import { SectionHeader, MetadataContainer } from '../../components/common.jsx';
import {fovMetadataDefinitions} from '../../settings/metadataDefinitions.js';
import { CellLineMetadataTable, ExternalLinks } from '../../components/cellLineMetadata.jsx';

import '../../components/common.css';
import '../../components/Profile.css';
import './fovAnnotator.css';


function Thumbnail (props) {

    const metadata = props.fov.metadata;
    const imgClassName = classNames(
        'thumbnail', 
        {
            'thumbnail-annotated': (
                props.fov.annotation && props.fov.annotation.roi_position_left!==null
            ),
            'thumbnail-flagged': (
                !metadata.score ||
                metadata.cell_layer_center < 4 || 
                metadata.max_intensity_488===65535 ||
                props.fov.annotation?.categories.includes('discarded')
            ),
        }
    );

    const divClassName = classNames(
        'pa1', 'thumbnail-container',
        {
            'thumbnail-container-active': metadata.id===props.fovId
        }
    );

    return (
        <div className={divClassName} onClick={() => props.changeFov(metadata.id)}>
            <img 
                className={imgClassName} 
                src={`data:image/jpg;base64,${props.fov.thumbnails?.data}`}
            />
            <div className='thumbnail-caption'>
                <span>{`${metadata.pml_id}`}</span>
                <br></br>
                <span>{`FOV ${metadata.id}`}</span>
            </div>
        </div>
    );
}


function RoiOutline (props) {
    const visibility = props.visible ? 'visible' : 'hidden';
    if (isNaN(props.top) || isNaN(props.left)) return null;
    return (
        <div 
            className={`fov-curator-roi ${props.className}`}
            style={{
                top: props.top, 
                left: props.left, 
                width: props.size, 
                height: props.size, 
                visibility
            }}
        />
    );
};


export default class FovAnnotator extends Component {

    constructor (props) {
        super(props);

        this.fovs = [];
        this.state = {

            fovId: undefined,

            // the coordinates of the new user-selected ROI
            pixelRoiTop: undefined,
            pixelRoiLeft: undefined,

            // FOV annotation categories
            categories: [],
            
            // whether the FOV metadata and/or image (z-projection) has loaded
            loaded: false,

            // whether to show or hide the new and existing ROI outlines
            showNewRoi: false,
            showExistingRoi: true,

            // whether annotation submission or deletion was successful
            submissionStatus: '',
            deletionStatus: '',
        };

        this.FOVImgRef = React.createRef();
        this.changeFov = this.changeFov.bind(this);
        this.onFOVClick = this.onFOVClick.bind(this);
        this.updateFovScale = this.updateFovScale.bind(this);
        this.toggleCategory = this.toggleCategory.bind(this);

        // the hard-coded size of the ROI in real/raw pixels
        this.roiSize = 600;
    }


    componentDidMount () {
        this.fetchData();
    }


    componentDidUpdate(prevProps) {
        if (this.props.cellLineId!==prevProps.cellLineId) {
            this.setState({fovId: null});
            this.fetchData();
        }
    }

    updateFovScale() {
        const img = this.FOVImgRef.current;
        this.setState({fovScale: img.clientWidth / img.naturalWidth});
    }


    changeFov (fovId) {

        // loaded is only false if the fovId has changed, which will trigger a new img to load
        const loaded = this.state.fovId===fovId;

        const fov = this.fovs.filter(fov => fov.metadata.id === fovId)[0];
        this.setState({
            fovId, 
            loaded,
            pixelRoiTop: undefined,
            pixelRoiLeft: undefined,
            showNewRoi: false, 
            showExistingRoi: true,
            submissionStatus: '',
            deletionStatus: '',
            categories: fov?.annotation?.categories || [],
        });
    }


    toggleCategory (category) {
        let categories = this.state.categories;
        if (categories.includes(category)) {
            categories = categories.filter(value => value!==category);
        } else {
            categories.push(category);
        }
        this.setState({categories});
    }


    fetchData () {
        if (!this.props.cellLineId) return;
        this.setState({loaded: false, roiVisible: false});

        // get metadata for all of the cell line's FOVs
        const url = `${settings.apiUrl}/lines/${this.props.cellLineId}/fovs?fields=thumbnails&onlyannotated=false`;
        d3.json(url).then(fovs => {
            this.fovs = fovs;
            this.setState({
                loaded: true, 
                submissionStatus: 'none',
            });
            this.changeFov(this.state.fovId || fovs[0]?.metadata.id);
        });
    }


    onFOVClick (event) {

        const img = this.FOVImgRef.current;
        const bounds = img.getBoundingClientRect();

        // the position of the click relative to the image as it is displayed in the browser
        const clientX = event.clientX - bounds.left;
        const clientY = event.clientY - bounds.top;

        // the size of the ROI in the client
        const clientRoiSize = this.roiSize * this.state.fovScale;

        // the top left corner of the ROI in the client
        const clientRoiLeft = d3.min([
            d3.max([0, clientX - clientRoiSize/2]), 
            img.clientWidth - clientRoiSize
        ]);
        const clientRoiTop = d3.min([
            d3.max([0, clientY - clientRoiSize/2]), 
            img.clientHeight - clientRoiSize
        ]);

        // the top-left corner in raw pixels
        const pixelRoiLeft = parseInt(clientRoiLeft / this.state.fovScale);
        const pixelRoiTop = parseInt(clientRoiTop / this.state.fovScale);

        this.setState({
            pixelRoiTop,
            pixelRoiLeft,
            showNewRoi: true,
            submissionStatus: '',
            deletionStatus: '',
        })
    }


    onSubmit () {
        // save the changes to an FOV annotation

        this.setState({deletionStatus: ''});

        const fov = this.fovs.filter(fov => fov.metadata.id === this.state.fovId)[0];

        const data = {
            categories: this.state.categories,
            roi_position_top: fov.annotation?.roi_position_top,
            roi_position_left: fov.annotation?.roi_position_left,
            client_metadata: {
                last_modified: (new Date()).toString(),
            }
        };

        // if the existing ROI is hidden, the 'clear existing ROI' button was clicked
        if (!this.state.showExistingRoi) {
            data.roi_position_top = null;
            data.roi_position_left = null;
        }
        // if the new ROI is visible, the user must have clicked to select a new ROI
        if (this.state.showNewRoi) {
            data.roi_position_top = this.state.pixelRoiTop;
            data.roi_position_left = this.state.pixelRoiLeft;
        }

        utils.putData(`${settings.apiUrl}/fovs/${this.state.fovId}/annotation`, data)
            .then(response => {
                console.log(response.json());
                if (!response.ok) throw new Error('Error submitting FOV annotation');
                this.setState({submissionStatus: 'success'});
                this.fetchData();
            })
            .catch(error => this.setState({submissionStatus: 'danger'}));
    }


    onClear () {
        // clear an existing FOV annotation
        this.setState({
            pixelRoiTop: undefined,
            pixelRoiLeft: undefined,
            submissionStatus: ''
        });

        utils.deleteData(`${settings.apiUrl}/fovs/${this.state.fovId}/annotation`)
            .then(response => {
                console.log(response);
                if (!response.ok) throw new Error('Error deleting FOV annotation');
                this.setState({deletionStatus: 'success'});
                this.fetchData();
            })
            .catch(error => this.setState({deletionStatus: 'danger'}));
    }


    render () {

        // if (!this.fovs.length) return (<div className="f3 tc pa5">No ROIs found</div>);

        const clientRoiSize = this.state.fovScale * this.roiSize;
        const fov = this.fovs.filter(fov => fov.metadata.id === this.state.fovId)[0];

        const thumbnails = this.fovs.map(fov => {
            return (
                <Thumbnail 
                    key={fov.metadata.id} 
                    fov={fov} 
                    fovId={this.state.fovId} 
                    changeFov={this.changeFov}
                />
            )
        });

        return (
            <div className="w-70">
                <div className="flex">

                    {/* left panel: FOV metadata */}
                    <div className="w-20 pr3">
                        <CellLineMetadataTable data={this.props.cellLine}/>

                        <SectionHeader title='FOV metadata'/>
                        <MetadataContainer
                            data={fov}
                            orientation='column'
                            definitions={fovMetadataDefinitions}
                            scale={4}
                        />

                        {/* 
                        show the src_filepath on multiple lines
                        note that 'white-space: pre-line' allows '\n' to create a newline 
                        */}
                        <div className="pt3" style={{whiteSpace: 'pre-line'}}>
                            {fov?.metadata.src_filename.replace(/\//g, '\n') || 'NA'}
                        </div>

                        <div className='pt3'>
                            {`ROI position: ${this.state.pixelRoiTop}, ${this.state.pixelRoiLeft}`}
                        </div>

                    </div>

                    {/* FOV z-projection */}
                    <div className="pt3" style={{flex: '0 0 auto'}}>
                        <div style={{position: 'relative', float: 'left'}}>
                            <img 
                                width='600px' 
                                ref={this.FOVImgRef}
                                onClick={event => this.onFOVClick(event)}
                                src={`${settings.apiUrl}/fovs/${this.state.fovId}/proj/rgb`}
                                onLoad={() => {this.setState({loaded: true}); this.updateFovScale()}}
                            />

                            {/* outline of new user-selected ROI */}
                            <RoiOutline
                                top={this.state.pixelRoiTop*this.state.fovScale}
                                left={this.state.pixelRoiLeft*this.state.fovScale}
                                size={clientRoiSize}
                                className='fov-curator-roi-new'
                                visible={this.state.showNewRoi}
                            />

                            {/* outline of existing user-selected ROI */}
                            {
                                (fov?.annotation && fov?.annotation.roi_position_left!==null) ? (
                                    <RoiOutline
                                        top={fov.annotation.roi_position_top*this.state.fovScale}
                                        left={fov.annotation.roi_position_left*this.state.fovScale}
                                        size={clientRoiSize}
                                        visible={this.state.showExistingRoi}
                                    />
                                ) : (null)
                            }

                            {this.state.loaded ? (null) : (<div className='loading-overlay'/>)}
                            
                            {/* thumbnail grid */}
                            <div className="w-100 pt3 thumbnail-grid">{thumbnails}</div>
            
                        </div>
                    </div>

                    {/* FOV annotation submission and clear buttons */}
                    <div className="pt3 pl4 w-25 flex" style={{flexDirection: 'column'}}>
                        <Button
                            text={'Remove new ROI'}
                            className={'ma2 bp3-button'}
                            onClick={() => {
                                this.setState({showNewRoi: false});
                            }}
                            intent={'none'}
                        />
                        <Button
                            text={'Remove existing ROI'}
                            className={'ma2 bp3-button'}
                            onClick={() => {
                                this.setState({showExistingRoi: false});
                            }}
                            intent={'none'}
                        />
                        <Checkbox
                            className='pt2 ml2'
                            label='Discard this FOV'
                            checked={this.state.categories.includes('discarded')}
                            onChange={() => this.toggleCategory('discarded')}
                        />
                        <Checkbox
                            className='pt2 ml2'
                            label='Include this FOV in the public dataset'
                            checked={this.state.categories.includes('public')}
                            onChange={() => this.toggleCategory('public')}
                        />
                        <Button
                            text={'Submit changes'}
                            className={'ma2 mt3 bp3-button'}
                            onClick={event => this.onSubmit()}
                            intent={this.state.submissionStatus || 'none'}
                        />                       
                        <Button
                            text={'Delete entire annotation'}
                            className={'ma2 mt3 bp3-button'}
                            onClick={event => this.onClear()}
                            intent={this.state.deletionStatus || 'none'}
                        /> 
                    </div>

                </div>

            </div>
        );
    }
}



