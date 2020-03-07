import * as d3 from 'd3';
import React, { Component } from 'react';
import ReactTable from 'react-table';

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

import '../common/common.css';
import '../profile/Profile.css';


function thumbnail (fov, changeFov) {
    return (
        <div className="pa1" key={fov.id} onClick={() => changeFov(fov.id)}>
            <img src={`data:image/jpg;base64,${fov.thumbnails.data}`}/>
        </div>
    );
}



export default class FOVCurator extends Component {

    constructor (props) {
        super(props);

        this.state = {
            loaded: false,
            fovId: null,
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

        return (
            <div className="">

                <div className="w-33"></div>

                {/* FOV display */}
                <div className="w-66 tc">
                    <img width='50%' src={`${settings.apiUrl}/fovs/rgb/proj/${this.state.fovId}`}/>
                </div>

                {/* thumbnail grid */}
                <div className="w-100 thumbnail-grid">
                    {this.data?.fovs.map(fov => thumbnail(fov, this.changeFov))}
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


