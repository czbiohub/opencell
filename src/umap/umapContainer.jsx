import React, { Component } from 'react';
import { Button, MenuItem, Slider, RangeSlider, Tooltip, Popover, Icon } from "@blueprintjs/core";
import { Select } from "@blueprintjs/select";
import classNames from 'classnames';

// import Slider from './slider.jsx';
import ButtonGroup from '../profile/buttonGroup.jsx';
import UMAPViewer from './umapViewer.jsx';
import settings from '../common/settings.js';
import * as utils from '../common/utils.js';
import * as popoverContents from '../common/popoverContents.jsx';

import 'tachyons';
import '../profile/Profile.css';

export default class UMAPContainer extends Component {

    constructor (props) {
        super(props);

        this.state = {
            
            // 'dots' or 'thumbnails'
            markerType: 'thumbnails',

            // 'grid' or 'raw' for binned or raw UMAP coordinates
            // (when markerType is 'thumbnails')
            coordType: 'grid', 

            // 'localization', 'family', etc
            // (when markerType is 'dots')
            colorBy: 'localization',

            // the size of the grid when umap type is 'grid'
            gridSize: 40,

            shouldResetZoom: false,
        };

    }


    render () {
        return (
            <div className='relative pa4'>
                
                {/* row of controsl */}
                <div className='umap-controls-container'>
                    <div className='f5 b pb3'>UMAP display controls</div>
                    <div className='pb3'>
                        <ButtonGroup 
                            label='Marker type' 
                            values={['dots', 'thumbnails']}
                            labels={['Dots', 'Thumbnails']}
                            activeValue={this.state.markerType}
                            onClick={value => this.setState({markerType: value})}
                            popoverContent={popoverContents.umapMarkerType}
                        />
                    </div>
                    <div className='pb3'>
                        <ButtonGroup 
                            label='Snap thumbnails to grid' 
                            values={['grid', 'raw']}
                            labels={['Yes', 'No']}
                            activeValue={this.state.coordType}
                            onClick={value => this.setState({coordType: value})}
                            popoverContent={popoverContents.umapSnapToGrid}
                            disabled={this.state.markerType!=='thumbnails'}
                        />
                    </div>
                    <div className='pb3'>
                        <ButtonGroup 
                            label='Grid size' 
                            values={[30, 40, 60]}
                            labels={null}
                            activeValue={this.state.gridSize}
                            onClick={value => this.setState({gridSize: value})}
                            popoverContent={popoverContents.umapGridSize}
                            disabled={this.state.markerType!=='thumbnails' || this.state.coordType!=='grid'}
                        />
                    </div>

                    <div className='pb3'>
                        <Button
                            className="bp3-button-custom"
                            text={"Reset zoom"}
                            onClick={() => this.setState({shouldResetZoom: true})}
                        />
                    </div>
                </div>

                <div className='umap-container'>
                    <UMAPViewer coordType={this.state.coordType}/>
                </div>
            </div>
        )
    }
}