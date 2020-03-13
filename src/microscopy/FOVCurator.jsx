import * as d3 from 'd3';
import React, { Component } from 'react';

import classNames from 'classnames';
import { Button, Radio, RadioGroup, MenuItem } from "@blueprintjs/core";
import { Select } from "@blueprintjs/select";

import Slider from '../profile/slider.jsx';
import ButtonGroup from '../profile/buttonGroup.jsx';
import CellLineTable from '../profile/cellLineTable.jsx';

import 'tachyons';
import 'react-table/react-table.css';
import "@blueprintjs/core/lib/css/blueprint.css";

import settings from '../common/settings.js';
import * as utils from '../common/utils.js';
import { SectionHeader } from '../profile/common.jsx';

import '../common/common.css';
import '../profile/Profile.css';


async function putData(url, data) {
    const response = await fetch(url, {
        method: 'PUT',
        mode: 'cors',
        cache: 'no-cache',
        credentials: 'same-origin',
        headers: {'Content-Type': 'application/json'},
        referrerPolicy: 'no-referrer',
        body: JSON.stringify(data),
    });
    return await response;
}

async function deleteData(url) {
    const response = await fetch(url, {
        method: 'DELETE',
        mode: 'cors',
        cache: 'no-cache',
        credentials: 'same-origin',
        referrerPolicy: 'no-referrer',
    });
    return await response;
}

function thumbnail (fov, fovId, changeFov) {
    const className = classNames(
        'thumbnail', 
        {
            'thumbnail-annotated': !!fov.annotation,
            'thumbnail-active': fov.id===fovId,
        }
    );

    return (
        <div className='pa1' key={fov.id} onClick={() => changeFov(fov.id)}>
            <img className={className} src={`data:image/jpg;base64,${fov.thumbnails.data}`}/>
        </div>
    );
}


function roiOutline (top, left, roiSize, className, visible) {
    const visibility = visible ? 'visible' : 'hidden';
    if (top===undefined || left===undefined) return null;
    return (
        <div 
            className={`fov-curator-roi ${className}`}
            style={{top, left, width: roiSize, height: roiSize, visibility}}
        />
    );
};


export default class FOVCurator extends Component {

    constructor (props) {
        super(props);

        this.state = {
            fovId: null,
            loaded: false,
            roiVisible: false,
            categories: [],
            submissionStatus: '',
            deletionStatus: '',
        };

        this.FOVImgRef = React.createRef();
        this.changeFov = this.changeFov.bind(this);
        this.onFOVClick = this.onFOVClick.bind(this);
        this.updateFovScale = this.updateFovScale.bind(this);
    
        // the hard-coded size of the ROI in real/raw pixels
        this.roiSize = 600;
    
    }

    updateFovScale() {
        const img = this.FOVImgRef.current;
        this.setState({fovScale: img.clientWidth / img.naturalWidth});
    }

    changeFov (fovId) {
        this.setState({
            fovId, 
            roiVisible: false, 
            submissionStatus: '',
            deletionStatus: ''
        });
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

    fetchData () {
        if (!this.props.cellLineId) return;
        this.setState({loaded: false, roiVisible: false});
        const url = `${settings.apiUrl}/lines/${this.props.cellLineId}?kind=thumbnails`;
        d3.json(url).then(line => {
            this.data = line;
            this.setState({loaded: true, fovId: this.state.fovId || this.data.fovs[0].id});
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
        const clientRoiLeft = d3.min([d3.max([0, clientX - clientRoiSize/2]), img.clientWidth - clientRoiSize]);
        const clientRoiTop = d3.min([d3.max([0, clientY - clientRoiSize/2]), img.clientHeight - clientRoiSize]);

        // the top-left corner in raw pixels
        const pixelRoiLeft = parseInt(clientRoiLeft / this.state.fovScale);
        const pixelRoiTop = parseInt(clientRoiTop / this.state.fovScale);

        this.setState({
            pixelRoiTop,
            pixelRoiLeft,
            roiVisible: true,
            submissionStatus: '',
            deletionStatus: '',
        })
    }


    onSubmit () {
        // submit an FOV annotation
        
        this.setState({deletionStatus: ''});
        if (this.state.pixelRoiLeft===undefined || this.state.pixelRoiTop===undefined) {
            this.setState({submissionStatus: 'danger'});
            return;
        }

        const data = {
            categories: this.state.categories,
            roi_position_top: this.state.pixelRoiTop, 
            roi_position_left: this.state.pixelRoiLeft,
            client_metadata: {
                last_modified: (new Date()).toString(),
            }
        };

        putData(`${settings.apiUrl}/fov_annotations/${this.state.fovId}`, data)
            .then(response => {
                console.log(response);
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

        deleteData(`${settings.apiUrl}/fov_annotations/${this.state.fovId}`)
            .then(response => {
                console.log(response);
                if (!response.ok) throw new Error('Error deleting FOV annotation');
                this.setState({deletionStatus: 'success'});
                this.fetchData();
            })
            .catch(error => this.setState({deletionStatus: 'danger'}));
    }



    render () {

        const clientRoiSize = this.state.fovScale * this.roiSize;
        const fov = this.data?.fovs.filter(fov => fov.id === this.state.fovId)[0];

        return (
            <div className="">
                <div className="flex">

                    {/* left panel: FOV metadata */}
                    <div className="w-20 pr3 flex" style={{flexDirection: 'column'}}>
                        <SectionHeader title='FOV metadata'/>
                        {FOVMetadataItem('Laser power', fov?.laser_power_488.toFixed(1) || 'NA', '%')}
                        {FOVMetadataItem('Exposure time', fov?.exposure_time_488.toFixed() || 'NA', 'ms')}
                        {FOVMetadataItem('Max intensity', fov?.max_intensity_488 || 'NA', '')}
                        {FOVMetadataItem('Score', fov?.score?.toFixed(2) || 'NA', '')}
                        {FOVMetadataItem('Step size', fov?.z_step_size?.toFixed(1) || 'NA', 'um')}
                        {FOVMetadataItem('Dataset ID', fov?.pml_id || 'NA', '')}
                        {FOVMetadataItem('FOV ID', fov?.id || 'NA', '')}

                        {/* 
                        show the src_filepath on multiple lines
                        note that 'white-space: pre-line' allows '\n' to create a newline 
                        */}
                        <div className="pt3" style={{whiteSpace: 'pre-line'}}>
                            {fov?.src_filename.replace(/\//g, '\n') || 'NA'}
                        </div>

                        <div className='pt3'>
                            {`ROI position: ${this.state.pixelRoiTop}, ${this.state.pixelRoiLeft}`}
                        </div>

                    </div>

                    {/* FOV z-projection */}
                    <div className="" style={{flex: '0 0 auto'}}>
                        <div style={{position: 'relative', float: 'left'}}>
                            <img 
                                width='600px' 
                                ref={this.FOVImgRef}
                                onClick={event => this.onFOVClick(event)}
                                src={`${settings.apiUrl}/fovs/rgb/proj/${this.state.fovId}`}
                                onLoad={event => this.updateFovScale()}
                            />

                            {/* outline of new user-selected ROI */}
                            {roiOutline(
                                this.state.pixelRoiTop * this.state.fovScale, 
                                this.state.pixelRoiLeft * this.state.fovScale, 
                                clientRoiSize,
                                'fov-curator-roi-new',
                                this.state.roiVisible)}

                            {/* outline of existing user-selected ROI */}
                            {fov?.annotation ? roiOutline(
                                fov.annotation.roi_position_top * this.state.fovScale,
                                fov.annotation.roi_position_left * this.state.fovScale,
                                clientRoiSize,
                                '',
                                true)
                            : null}
                        </div>
                    </div>

                    {/* FOV annotation submission and clear buttons */}
                    <div className="w-20 pl3 flex" style={{flexDirection: 'column'}}>
                        <Button
                            text={'Submit'}
                            className={'ma2 bp3-button'}
                            onClick={event => this.onSubmit()}
                            intent={this.state.submissionStatus || 'none'}
                        />
                        <Button
                            text={'Clear'}
                            className={'ma2 bp3-button'}
                            onClick={event => this.onClear()}
                            intent={this.state.deletionStatus || 'none'}
                        />
                    </div>

                </div>

                {/* thumbnail grid */}
                <div className="w-100 pt3 thumbnail-grid">
                    {this.data?.fovs.map(fov => thumbnail(fov, this.state.fovId, this.changeFov))}
                </div>

                {/* table of all targets */}
                <div className="w-100">
                    <CellLineTable 
                        cellLineId={this.props.cellLineId}
                        cellLines={this.props.cellLines}
                        onCellLineSelect={this.props.onCellLineSelect}
                    />
                </div>

            </div>
        );
    }

}


// warning: this is almost a direct copy of a function in header.jsx
function FOVMetadataItem(label, value, units) {
    return (
        <div className='header-metadata-item pt2'>
            <strong className='f4'>{value}</strong>
            <abbr className='f5' title='units description'>{units}</abbr>
            <div className='f6 header-metadata-item-label'>{label}</div>
        </div>
    );
}
