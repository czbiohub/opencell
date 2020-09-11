
import * as d3 from 'd3';
import React, { Component } from 'react';
import chroma from 'chroma-js';

import cytoscape from 'cytoscape';
import cise from 'cytoscape-cise';
import CytoscapeComponent from 'react-cytoscapejs';

import ButtonGroup from './buttonGroup.jsx';
import settings from '../common/settings.js';

import 'tachyons';
import './Profile.css';

cytoscape.use(cise);

export default class MassSpecNetworkContainer extends Component {

    constructor (props) {
        super(props);
        this.state = {

            // placeholder for future plot mode
            mode: '',

            // placeholder for resetting the visualization
            resetPlotZoom: false,

            loaded: false,
            loadingError: false,
        };
    
        this.elements = [
            {data: {id: 'a'}}, 
            {data: {id : 'b'}}, 
            {data: {source: 'a', target: 'b'}}
        ];

        this.style = [
            {
              selector: 'node',
              style: {
                'background-color': '#666',
                label: 'data(id)',
                height: 10,
                width: 10
              }
            },{
              selector: 'edge',
              style: {
                'width': 1,
              }
            }
        ];

        this.getData = this.getData.bind(this);

    }

    componentDidMount() {
        if (this.props.cellLineId) {
            this.getData();
        }
    }

    componentDidUpdate (prevProps) {
        if (prevProps.cellLineId!==this.props.cellLineId) {
            this.getData();
        }
    }

    getData () {
        this.setState({loaded: false, loadingError: false});
        const url = `${settings.apiUrl}/lines/${this.props.cellLineId}/pulldown_clusters`;
        d3.json(url).then(data => {

            const targetNames = [
                ...data.rows.map(row => row.uniprot_gene_names[0]),
                ...data.columns.map(col => col.target_name),
            ];
            
            this.elements = [];
            
            // generate the nodes
            targetNames.forEach(name => this.elements.push({data: {id: name}}));

            // generate the edges
            data.tiles.forEach(tile => {
                const rowName = data.rows.filter(row => row.row_index===tile.row_index)[0].uniprot_gene_names[0];
                const colName = data.columns.filter(col => col.col_index===tile.col_index)[0].target_name;
                if (rowName!==colName) this.elements.push({data: {source: rowName, target: colName}});
            });

            this.setState({loaded: true, loadingError: false});
        },
        error => {
            this.setState({loaded: true, loadingError: true});
        });
    }



    render () {
        return (
            <div>
                {/* display controls */}
                <div className="flex pt3 pb2">

                    {/* Top row - scatterplot controls */}
                    <div className='w-100 flex flex-wrap items-end'>
                        <div className='pr2'>
                            <ButtonGroup 
                                label='Options' 
                                values={['val1', 'val2']}
                                labels={['Option 1', 'Option 2']}
                                activeValue={this.state.mode}
                                onClick={value => this.setState({mode: value})}/>
                        </div>
                        <div 
                            className='f6 simple-button' 
                            onClick={() => {
                                this.setState({resetPlotZoom: !this.state.resetPlotZoom})
                                debugger;
                            }}>
                            {'Reset zoom'}
                        </div>
                    </div>
                </div>

                <div className="w-100 cluster-heatmap-container">
                    {this.state.loaded ? (
                        <CytoscapeComponent
                            style={{width: '500px', height: '500px'}}
                            elements={this.elements}
                            stylesheet={this.style}
                            layout={{name: 'cise'}}
                            cy={cy => {this.cy = cy}}
                        />
                    ) : (
                        null
                    )}
                </div>
            </div>

        );
    }
}
