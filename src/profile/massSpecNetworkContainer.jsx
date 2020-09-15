
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
                    height: 5,
                    width: 5,
                    'background-color': '#555',
                    // turn off the overlay when the node is clicked
                    'overlay-padding': '0px',
                    'overlay-opacity': 0, 
                }
            },{
                selector: "node[type='bait']",
                style: {
                    'background-color': '#51ade1',
                    'opacity': 1.0,
                }
            },{
                selector: "node[type='hit']",
                style: {
                    'background-color': '#ff827d',
                    'opacity': 1.0,
                }
            },{
                selector: 'edge',
                style: {
                    width: 0.5,
                    opacity: 0.15,
                    // this turns off overlay and disables clicking/dragging the edges
                    'overlay-opacity': 0,
                    'line-color': "#333",
                    "curve-style": "haystack",
                    "target-arrow-shape": "triangle-backcurve",
                    "arrow-scale": 0.5,
                }
            },{
                selector: "edge[type='prey-prey']",
                style: {
                    'line-style': "solid",
                }
            },{
                selector: "edge[type='bait-prey']",
                style: {
                    //'line-style': "dotted",
                    //visibility: 'hidden',
                }
            }
        ];

        this.nodeHtmlLabel = [
            {
                query: 'node',
                cssClass: 'cy-node-label-container',
                valign: 'top',
                valignBox: 'top',

                // the tpl function is used to set the label container's innerHTML property,
                // and therefore must return a string of serialized HTML
                tpl: d => {
                    const names = d.uniprot_gene_names.map(name => {
                        const inOpencell = d.opencell_target_names.includes(name);
                        if (inOpencell) {
                            return `<span class='cy-node-label-in-opencell'>${name}</span>`
                        }
                        return `<span class=''>${name}</span>`
                    })
                    return `<span>${names.join(', ')}</span>`;
                }
            }
        ];

        this.coseLayout = {
            name: 'cose',
            padding: 30,
            nodeOverlap: 4,
            nestingFactor: 1,
            initialTemp: 1000,
            coolingFactor: 0.99,
            minTemp: 1.0,
            gravity: 1.0,
            idealEdgeLength: 60,
            edgeElasticity: 600, // smaller is tighter
            nodeRepulsion: 4000,

        }

        this.getData = this.getData.bind(this);
        this.defineLabelEventHandlers = this.defineLabelEventHandlers.bind(this);

    }

    getCiseLayout () {
        // the cise layout includes a list of clusters (each a list of node ids),
        // so it must be dynamically generated
        return {name: 'cise', clusterInfo: this.ciseClusters}
    }

    componentDidMount() {
        if (this.props.cellLineId) {
            this.getData();
        }
    }

    componentDidUpdate (prevProps) {
        if (this.cy && this.state.loaded) {
            try {
                this.cy.nodeHtmlLabel(this.nodeHtmlLabel);
                const layout = this.cy.layout(this.coseLayout);
                layout.on('layoutstop', this.defineLabelEventHandlers);
                layout.run();
            }
            catch (err) {
                console.log(err);
            }
        }
        if (prevProps.cellLineId!==this.props.cellLineId) {
            this.getData();
        }
    }


    defineLabelEventHandlers () {
        const changeTarget = this.props.changeTarget;
        const labels = d3.selectAll(".cy-node-label-in-opencell")
            .on("click", function () {
                const targetName = d3.select(this).text();
                changeTarget(targetName);
            });
    }


    getData () {
        this.setState({loaded: false, loadingError: false});
        const url = `${settings.apiUrl}/lines/${this.props.cellLineId}/pulldown_interactions`;
        d3.json(url).then(data => {

            // create a single cluster from the direct interactors
            const baitId = data.nodes.filter(node => node.is_bait)[0];
            this.ciseClusters = [
                data.edges.filter(edge => edge.source===baitId).map(edge => edge.target)
            ];

            this.elements = [...data.nodes, ...data.edges];
            this.setState({loaded: true, loadingError: false});
        },
        error => {
            this.elements = [];
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
