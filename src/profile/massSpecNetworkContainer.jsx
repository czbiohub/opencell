
import * as d3 from 'd3';
import React, { Component } from 'react';
import chroma from 'chroma-js';

import cytoscape from 'cytoscape';
import cise from 'cytoscape-cise';
import fcose from 'cytoscape-fcose';
import coseBilkent from 'cytoscape-cose-bilkent';
import CytoscapeComponent from 'react-cytoscapejs';
import nodeHtmlLabel from 'cytoscape-node-html-label';

import ButtonGroup from './buttonGroup.jsx';
import settings from '../common/settings.js';

import 'tachyons';
import './Profile.css';

cytoscape.use(cise);
cytoscape.use(fcose);
cytoscape.use(coseBilkent);
cytoscape.use(nodeHtmlLabel);


export default class MassSpecNetworkContainer extends Component {

    constructor (props) {
        super(props);

        // this.cy = React.createRef();

        this.state = {

            // placeholder for future plot mode
            layoutName: 'cose',

            includeParentNodes: false,

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
                selector: ':parent',
                style: {
                    'shape': 'ellipse',
                    'background-opacity': .2,
                    'background-color': "#ffffa7",
                    // 'border-color': '#999',
                    'border-opacity': 0,
                    'border-width': 0.5,
                }
            },{
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
                    'line-color': "#333",

                    // haystack without arrows
                    opacity: 0.15,
                    "curve-style": "haystack",

                    // bezier with arrows
                    // opacity: 0.5,
                    // "curve-style": "bezier",
                    // "target-arrow-shape": "triangle-backcurve",
                    // "arrow-scale": 0.5,
                    // "target-arrow-color": "#333",

                    // this turns off overlay and disables clicking/dragging the edges
                    'overlay-opacity': 0,
                }
            },{
                selector: "edge[cluster_status='intracluster']",
                style: {
                    //'line-color': "red",
                }
            },{
                selector: "edge[cluster_status='intercluster']",
                style: {
                    //'line-color': "blue",
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

            // multiplier for ideal edge length for 'nested' edges
            // TODO: what are nested edges?
            // small values (less than 1) yield overlapped nodes 
            // 10 yields very large compound node rectangles
            // default 1.2
            nestingFactor: 1.0,

            // default 32
            idealEdgeLength: (edge) => edge._private.data.cluster_status==='intracluster' ? 100 : 30,

            // extra space between components(nodes?) in non-compound graphs
            // doesn't seem to have much of an effect
            // default 40
            componentSpacing: 40,

            // smaller elasticity yields tighter networks
            // note: this appears to be the inverse of the edgeElasticity
            // in the fcose and cose-bilkent layouts
            // default 32
            edgeElasticity: edge => edge._private.data.cluster_status==='intracluster' ? 600 : 600,

            // node repulsion multiplier for overlapping nodes
            // default 4
            nodeOverlap: 4,

            // node repulsion multiplier for non-overlapping nodes
            // default 2048
            nodeRepulsion: 4000,

            // gravity force
            // default is 1.0
            gravity: 1.0,

        };

        this.fcoseLayout = {
            name: 'fcose',
            uniformNodeDimensions: true,

            // default 0.1
            //nestingFactor: 0.1,

            idealEdgeLength: 100,

            // divisor to compute edge forces
            // large values yield stacked nodes
            // default 0.45
            edgeElasticity: 999,

            // separation between nodes (this is specific to fcose)
            // small values encourage stacked nodes
            // default 75
            nodeSeparation: 1,

            // default 4500
            // small values seem to encourage stacked nodes
            nodeRepulsion: 100,

            // gravity: 1,
        };

        this.coseBilkentLayout = {
            name: 'cose-bilkent',

            idealEdgeLength: 100,

            // larger values yield tighter networks
            edgeElasticity: 1,

            nodeRepulsion: 6000,
        };

        this.circleLayout = {
            name: 'circle',
            radius: 150,
            spacingFactor: 1.0
        };

        this.concentricLayout = {
            name: 'concentric',
        };

        this.ciseLayout = {
            name: 'cise',
            animate: false,

            // separation between nodes in a cluster
            // higher values increase simulation time
            // default 12.5
            nodeSeparation: 10,

            // inter-cluster edge length relative to intra-cluster edges 
            // default 1.2
            idealInterClusterEdgeLengthCoefficient: 1.2,

            // higher spring coeffs give tighter clusters
            // default 0.45
            springCoeff: 0.3,

            // default 4500
            nodeRepulsion: 2000,
        };

        this.getData = this.getData.bind(this);
        this.getLayout = this.getLayout.bind(this);
        this.defineLabelEventHandlers = this.defineLabelEventHandlers.bind(this);

    }

    componentDidMount() {
        if (this.props.cellLineId) {
            this.getData();
        }
    }

    componentDidUpdate (prevProps, prevState) {

        if (
            prevProps.cellLineId!==this.props.cellLineId || 
            this.state.includeParentNodes!==prevState.includeParentNodes
        ) {
            this.getData();
        }
        else if (this.cy && this.state.loaded) {
            try {
                this.cy.nodeHtmlLabel(this.nodeHtmlLabel);
                const layout = this.cy.layout(this.getLayout());
                layout.on('layoutstop', this.defineLabelEventHandlers);
                layout.run();
                //debugger;
            }
            catch (err) {
                console.log(err);
            }
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

    getLayout () {
        let layout;
        const layoutName = this.state.layoutName;
        if (layoutName==='cose') layout = this.coseLayout;
        if (layoutName==='fcose') layout = this.fcoseLayout;
        if (layoutName==='cosebilkent') layout = this.coseBilkentLayout;
        if (layoutName==='circle') layout = this.circleLayout;
        if (layoutName==='concentric') layout = this.concentricLayout;
        if (layoutName==='cise') layout = {...this.ciseLayout, clusters: this.clusterInfo};
        return layout;
    }

    getData () {
        this.setState({loaded: false, loadingError: false});
        const url = `${settings.apiUrl}/lines/${this.props.cellLineId}/pulldown_interactions`;
        d3.json(url).then(data => {

            // include only clusters with at least three nodes
            const clusters = data.clusters.filter(cluster => cluster.protein_group_ids.length > 1);
            
            // lists of node ids in each cluster (required for the CiSE layout)
            this.clusterInfo = clusters.map(cluster => cluster.protein_group_ids);

            // drop edges between the bait (since all nodes interact with the bait)
            const edges = data.edges; //.filter(edge => edge.data.type!=='bait-prey');

            // assign parents to nodes
            data.nodes.forEach(
                node => node.data.parent = node.data.cluster_id.length ? node.data.cluster_id[0] : undefined
            );
            
            // create parent nodes to represent the clusters
            const clusterIds = [...new Set(clusters.map(cluster => cluster.cluster_id))]
            const parentNodes = clusterIds.map(clusterId => {
                return {'data': {'id': clusterId}};
            });
            
            if (this.state.includeParentNodes) {
                this.elements = [...parentNodes, ...data.nodes, ...edges];
            } else {
                this.elements = [...data.nodes, ...edges];
            }
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
                                label='Layout' 
                                values={['circle', 'concentric', 'cose', 'fcose', 'cosebilkent', 'cise']}
                                labels={['Circle', 'Concentric', 'CoSE', 'fCoSE', 'CoSE-Bilkent', 'CiSE']}
                                activeValue={this.state.layoutName}
                                onClick={value => this.setState({layoutName: value})}
                            />
                        </div>
                        <div className='pr2'>
                        <ButtonGroup 
                            label='Use compound nodes for clusters' 
                            values={[true, false]}
                            labels={['Yes', 'No']}
                            activeValue={this.state.includeParentNodes}
                            onClick={value => this.setState({includeParentNodes: value})}
                        />
                        </div>
                        <div 
                            className='f6 simple-button' 
                            onClick={() => {}}
                        >
                            {'Reset'}
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
