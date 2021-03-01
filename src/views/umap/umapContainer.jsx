import * as d3 from 'd3';
import React, { Component } from 'react';
import { Button, MenuItem, Slider, RangeSlider, Tooltip, Popover, Icon } from "@blueprintjs/core";
import { Select } from "@blueprintjs/select";
import classNames from 'classnames';

import UMAPViewer from './umapViewer.jsx';
import ButtonGroup from '../../components/buttonGroup.jsx';
import * as popoverContents from '../../components/popoverContents.jsx';
import settings from '../../settings/settings.js';

import 'tachyons';
import '../../components/Profile.css';

export default class UMAPContainer extends Component {

    constructor (props) {
        super(props);

        this.state = {

            loaded: false,
            
            // 'dots' or 'thumbnails'
            markerType: 'thumbnails',

            // 'gridded' or 'raw' for binned or raw UMAP coordinates
            // (when markerType is 'thumbnails')
            coordType: 'gridded', 

            // 'localization', 'family', etc
            // (when markerType is 'dots')
            colorBy: 'localization',

            // the size of the grid when umap type is 'grid'
            gridSize: 40,

            showCaptions: false,

            resetZoom: false,
        };
    }

    parseAnnotations (annotations) {        
        // parse the grade from the annotation categories 
        // and retain only the grade-2 or -3 annotations
        if (!annotations) return [];
        const grade3 = [];
        const grade2 = [];
        annotations.forEach(annotation => {
            const grade = annotation.split('_').slice(-1)[0];
            const name = annotation.replace(`_${grade}`, '');
            if (grade==='2') grade3.push(name);
            if (grade==='3') grade2.push(name);
        });
        return {grade2, grade3};
    }


    componentDidMount (props) { 
        d3.json(`${settings.apiUrl}/embedding_positions`).then(data => {
            let positions = data.positions;

            // some minor reformatting and parse the localization annotations
            positions.forEach(position => {
                position.raw = [position.raw_x, position.raw_y];
                position.gridded = [position.grid_x, position.grid_y];
                Object.assign(position, this.parseAnnotations(position.categories));
            });
            
            // drop targets with a missing grid position
            positions = positions.filter(
                position => ((!!position.grid_x) && (!!position.grid_y))
            );
            this.positions = positions;
            this.setState({thumbnailTileFilename: data.tile_filename, loaded: true});
        });
    }


    render () {
        return (
            <div className='relative pa4'>
                
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
                            values={['gridded', 'raw']}
                            labels={['Yes', 'No']}
                            activeValue={this.state.coordType}
                            onClick={value => this.setState({coordType: value})}
                            popoverContent={popoverContents.umapSnapToGrid}
                            disabled={false}
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
                        <ButtonGroup 
                            label='Show labels' 
                            values={[true, false]}
                            labels={['Yes', 'No']}
                            activeValue={this.state.showCaptions}
                            onClick={value => this.setState({showCaptions: value})}
                            disabled={false}
                        />
                    </div>
                    <div className='pb3'>
                        <Button
                            className="bp3-button-custom"
                            text={"Reset zoom"}
                            onClick={() => this.setState({resetZoom: !this.state.resetZoom})}
                        />
                    </div>
                </div>

                <div 
                    className='umap-legend-container' 
                    ref={node => this.legendNode = node}
                    style={{visibility: this.state.markerType==='dots' ? 'visible' : 'hidden'}}
                />
                <div className='umap-container'>
                    <UMAPViewer 
                        positions={this.state.loaded ? this.positions : undefined}
                        thumbnailTileFilename={this.state.thumbnailTileFilename}
                        markerType={this.state.markerType} 
                        coordType={this.state.coordType}
                        gridSize={this.state.gridSize}
                        showCaptions={this.state.showCaptions}
                        resetZoom={this.state.resetZoom}
                        legendNode={this.legendNode}
                    />
                </div>
            </div>
        )
    }
}