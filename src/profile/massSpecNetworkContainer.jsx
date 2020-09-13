
import * as d3 from 'd3';
import React, { Component } from 'react';
import chroma from 'chroma-js';

import cytoscape from 'cytoscape';
import cise from 'cytoscape-cise';
import CytoscapeComponent from 'react-cytoscapejs';
import nodeHtmlLabel from 'cytoscape-node-html-label';

import ButtonGroup from './buttonGroup.jsx';
import settings from '../common/settings.js';

import 'tachyons';
import './Profile.css';

cytoscape.use(cise);
cytoscape.use(nodeHtmlLabel);

export default class MassSpecNetworkContainer extends Component {

    constructor (props) {
        super(props);

        // this.cy = React.createRef();

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
                    height: 5,
                    width: 5
                }
            },{
                selector: 'edge',
                style: {
                    width: 0.5,
                }
            },{
                selector: "edge[type='prey-prey']",
                style: {
                    'line-color': '#666',
                }
            },{
                selector: "edge[type='bait-prey']",
                style: {
                    'line-color': '#666',
                }
            }
        ];

        this.nodeHtmlLabel = [
            {
                query: 'node',
                cssClass: 'cy-node-label-container',
                valign: 'top',
                valignBox: 'top',
                tpl: d => {
                    const names = d.uniprot_gene_names.map(name => {
                        const className = d.opencell_target_names.includes(name) ? 'cy-node-label-in-opencell' : '';
                        return `<span class='${className}'>${name}</span>`
                    })
                    return `<span>${names.join(', ')}</span>`;
                }
            }
        ];

        this.coseLayout = {
            name: 'cose',
            padding: 100,
            nodeOverlap: 1,
            nestingFactor: .8,
            initialTemp: 1000,
            coolingFactor: 0.99,
            minTemp: 1.0,
            gravity: 1.4,
            idealEdgeLength: 30,
            edgeElasticity: 300, // smaller is tighter
        }

        this.getData = this.getData.bind(this);

    }

    componentDidMount() {
        if (this.props.cellLineId) {
            this.getData();
        }
    }

    componentDidUpdate (prevProps) {
        if (this.cy) {
            try {
                this.cy.nodeHtmlLabel(this.nodeHtmlLabel);
            }
            catch (err) {
                console.log(err);
            }
        }
        if (prevProps.cellLineId!==this.props.cellLineId) {
            this.getData();
        }
    }

    getData () {
        this.setState({loaded: false, loadingError: false});
        const url = `${settings.apiUrl}/lines/${this.props.cellLineId}/pulldown_interactions`;
        d3.json(url).then(data => {

            // create a single cluster from the direct interactors
            this.ciseClusters = [
                data.edges.filter(edge => edge.type==='bait-prey').map(edge => edge.target)
            ];

            this.elements = [...data.nodes, ...data.edges];
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

                <div className="w-100 cluster-heatmap-container ba">
                    {this.state.loaded ? (
                        <CytoscapeComponent
                            style={{width: '500px', height: '500px'}}
                            elements={this.elements}
                            stylesheet={this.style}
                            layout={this.coseLayout}
                            nodeHtmlLabel={this.nodeHtmlLabel}
                            zoom={1}
                            minZoom={0.5}
                            maxZoom={3}
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
