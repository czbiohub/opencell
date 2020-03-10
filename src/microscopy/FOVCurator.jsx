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


function thumbnail (fov, fovId, changeFov) {
    const className = classNames('thumbnail', {'thumbnail-active': fov.id === fovId});
    return (
        <div className='pa1' key={fov.id} onClick={() => changeFov(fov.id)}>
            <img className={className} src={`data:image/jpg;base64,${fov.thumbnails.data}`}/>
        </div>
    );
}



export default class FOVCurator extends Component {

    constructor (props) {
        super(props);

        this.state = {
            fovId: null,
            loaded: false,
        };

        this.changeFov = this.changeFov.bind(this);

    }

    changeFov (fovId) {
        this.setState({fovId});
    }

    componentDidMount () {
        this.fetchData();
    }

    componentDidUpdate(prevProps) {
        if (this.props.cellLineId!==prevProps.cellLineId) {
            this.fetchData();
        }
    }

    fetchData () {
        if (!this.props.cellLineId) return;
        this.setState({loaded: false});
        const url = `${settings.apiUrl}/lines/${this.props.cellLineId}?kind=thumbnails`;
        d3.json(url).then(line => {
            this.data = line;
            this.setState({loaded: true, fovId: this.data.fovs[0].id});
        });
    }



    render () {

        const fov = this.data?.fovs.filter(fov => fov.id === this.state.fovId)[0];

        return (
            <div className="">

                <div className="flex">

                    <div className="w-20 pr3 flex" style={{flexDirection: 'column'}}>
                        <SectionHeader title='FOV metadata'/>
                        {FOVMetadataItem('FOV ID', fov?.id || 'NA', '')}
                        {FOVMetadataItem('Laser power', fov?.laser_power_488.toFixed(1) || 'NA', '%')}
                        {FOVMetadataItem('Exposure time', fov?.exposure_time_488.toFixed() || 'NA', 'ms')}
                        {FOVMetadataItem('Max intensity', fov?.max_intensity_488 || 'NA', '')}
                        {FOVMetadataItem('Score', fov?.score.toFixed(2) || 'NA', '')}
                        {FOVMetadataItem('Dataset ID', fov?.pml_id || 'NA', '')}

                        {/* show the src_filepath
                        note that white-space: pre-line allows '\n' to create a newline */}
                        <div className="" style={{whiteSpace: 'pre-line'}}>
                            {fov?.src_filename.replace(/\//g, '\n') || 'NA'}
                        </div>
    
                    </div>

                    {/* FOV display */}
                    <div className="w-66">
                        <img width='66%' src={`${settings.apiUrl}/fovs/rgb/proj/${this.state.fovId}`}/>
                    </div>

                </div>

                {/* thumbnail grid */}
                <div className="w-100 thumbnail-grid">
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
        <div className='header-metadata-item pb2'>
            <strong className='f4'>{value}</strong>
            <abbr className='f5' title='units description'>{units}</abbr>
            <div className='f6 header-metadata-item-label'>{label}</div>
        </div>
    );
}
