import * as d3 from 'd3';
import React, { Component } from 'react';
import {Checkbox, Button} from '@blueprintjs/core';

import 'tachyons';
import "@blueprintjs/core/lib/css/blueprint.css";

import settings from '../common/settings.js';
import '../common/common.css';
import '../profile/Profile.css';


function thumbnail (fov) {
    return (
        <div className="pa1" key={fov.id}>
            <img src={`data:image/jpg;base64,${fov.thumbnails?.data}`}/>
        </div>
    );
}


function cellLineRow (data) {
    return (
        <div className="pb3" key={data?.metadata.cell_line_id}>
            <div className="pa1 flex w-100">
                <div className="pr3 f3">{data?.metadata.plate_id}</div>
                <div className="pr3 f3">{data?.metadata.well_id}</div>
                <div className="pr3 f3">{data?.metadata.target_name}</div>
            </div>
            <div className="w-100 thumbnail-grid">
                {data?.fovs.map(fov => thumbnail(fov))}
            </div>
        </div>
    );
}


export default class FOVOverview extends Component {

    constructor (props) {
        super(props);
        this.state = {
            loaded: false,
        };
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
        if (!this.props.plateId) return;
        this.setState({loaded: false});
        const url = `${settings.apiUrl}/lines?plate_id=${this.props.plateId}&kind=thumbnails`;
        d3.json(url).then(data => {
            this.data = data;
            this.setState({loaded: true});
        });
    }


    render () {
        return (
            <div className="pa3">
                {this.data?.map(d => cellLineRow(d))}
                {this.state.loaded ? (null) : (<div className='pa3 f1 loading-overlay'>Loading...</div>)}
            </div>
        );
    }
}


