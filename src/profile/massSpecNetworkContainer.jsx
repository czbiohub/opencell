
import * as d3 from 'd3';
import React, { Component } from 'react';
import { Button, Checkbox } from "@blueprintjs/core";
import chroma from 'chroma-js';

import cytoscape from 'cytoscape';
import cise from 'cytoscape-cise';
import fcose from 'cytoscape-fcose';
import coseBilkent from 'cytoscape-cose-bilkent';
import CytoscapeComponent from 'react-cytoscapejs';
import nodeHtmlLabel from 'cytoscape-node-html-label';

import ButtonGroup from './buttonGroup.jsx';
import settings from '../common/settings.js';
import * as utils from '../common/utils.js';
import networkLayouts from './massSpecNetworkLayouts.js';
import networkStylesheet from './massSpecNetworkStylesheet.js';


import 'tachyons';
import './Profile.css';

cytoscape.use(cise);
cytoscape.use(fcose);
cytoscape.use(coseBilkent);
cytoscape.use(nodeHtmlLabel);


export default class MassSpecNetworkContainer extends Component {

    constructor (props) {
        super(props);

        this.state = {

            layoutName: 'coseb',

            includeParentNodes: true,

            showSavedNetwork: false,

            // 'original' or 'new'
            clusteringAnalysisType: 'new',

            // 'subclusters' or 'core-complexes'
            subclusterType: 'subclusters',

            // placeholder for resetting the visualization
            resetPlotZoom: false,

            loaded: false,
            loadingError: false,
        };
    
        this.elements = [];

        this.nodeHtmlLabel = [
            {
                query: 'node',
                cssClass: 'cy-node-label-container',
                valign: 'top',
                valignBox: 'top',

                // the tpl function is used to set the label container's innerHTML property,
                // and therefore must return a string of serialized HTML
                tpl: d => {
                    // parent nodes do not have gene names
                    if (!d.uniprot_gene_names) return '<span></span>';

                    const names = d.uniprot_gene_names.map(name => {
                        const inOpencell = d.opencell_target_names.includes(name);
                        if (inOpencell) {
                            return `<span class='cy-node-label-in-opencell'>${name}</span>`
                        }
                        return `<span class=''>${name}</span>`
                    })
                    return `<div class='cy-node-label-container' id=${d.id}>${names.join(', ')}</div>`;
                }
            }
        ];

        this.getData = this.getData.bind(this);
        this.getLayout = this.getLayout.bind(this);
        this.getSavedNetwork = this.getSavedNetwork.bind(this);
        this.getNetworkElements = this.getNetworkElements.bind(this);
        this.saveNetwork = this.saveNetwork.bind(this);
        this.deleteSavedNetwork = this.deleteSavedNetwork.bind(this);
        this.defineLabelEventHandlers = this.defineLabelEventHandlers.bind(this);
    }

    componentDidMount() {
        if (this.props.pulldownId) {
            this.getData();
        }
    }

    componentDidUpdate (prevProps, prevState) {

        // load the network data
        if (
            prevProps.pulldownId!==this.props.pulldownId || 
            this.state.includeParentNodes!==prevState.includeParentNodes ||
            this.state.showSavedNetwork!==prevState.showSavedNetwork ||
            this.state.clusteringAnalysisType!==prevState.clusteringAnalysisType ||
            this.state.subclusterType!==prevState.subclusterType
        ) {
            this.getData();    
        }

        else if (this.cy && this.state.loaded) {
            try {

                // attempt to center and lock the target's node (this does not seem to apply to the layout)
                // const targetNode = this.cy.filter('node[type="bait"]');
                // targetNode.position({x: 250, y: 250}).lock();
                // if (targetNode.isChild()) {
                //     targetNode.parent().lock();
                // }

                this.cy.nodeHtmlLabel(this.nodeHtmlLabel);

                // run the layout if the elements were loaded from scratch
                if (!this.state.showSavedNetwork) {
                    const layout = this.cy.layout(this.getLayout());
                    layout.on('layoutstop', this.defineLabelEventHandlers);
                    layout.run();

                // only fit the graph to the container if the layout was loaded from
                } else {
                    // TODO: this does not work - label event handlers aren'tdefined
                    this.cy.ready(this.defineLabelEventHandlers);
                    this.cy.fit();
                }
            }
            catch (err) {
                console.log(err);
            }
        }
    }

    getData () {
        if (this.state.showSavedNetwork) {
            this.getSavedNetwork();
        } else {
            this.getNetworkElements();
        }
    }

    saveNetwork () {
        const data = {
            cytoscape_json: this.cy.json(),
            client_metadata: {last_modified: (new Date()).toString()}
        };
        this.setState({deletionStatus: ''});
        utils.putData(`${settings.apiUrl}/pulldowns/${this.props.pulldownId}/network`, data)
            .then(response => {
                console.log(response.json());
                if (!response.ok) throw new Error('Error saving cytoscape layout');
                this.setState({submissionStatus: 'success', showSavedNetwork: true});
            })
            .catch(error => this.setState({submissionStatus: 'danger'}));
    }


    deleteSavedNetwork () {
        this.setState({submissionStatus: ''});
        utils.deleteData(`${settings.apiUrl}/pulldowns/${this.props.pulldownId}/network`)
            .then(response => {
                console.log(response);
                if (!response.ok) throw new Error('Error deleting saved layout');
                this.setState({deletionStatus: 'success'});
            })
            .catch(error => this.setState({deletionStatus: 'danger'}));
    }


    defineLabelEventHandlers () {
        const cy = this.cy;
        const handleGeneNameSearch = this.props.handleGeneNameSearch;
        const labels = d3.selectAll(".cy-node-label-in-opencell")
            .on("click", function () {
                const targetName = d3.select(this).text();
                handleGeneNameSearch(targetName);
            });
        d3.selectAll(".cy-node-label-container")
            .on('mouseover', function (event) {
                const nodeId = d3.select(this).attr("id");
                cy.filter(`node[id="${nodeId}"]`).connectedEdges().addClass('hovered-node-edge');
            })
            .on('mouseout', function () {
                const nodeId = d3.select(this).attr("id");
                cy.filter(`node[id="${nodeId}"]`).connectedEdges().removeClass('hovered-node-edge');
            });
    }


    getLayout () {
        let layout = networkLayouts[this.state.layoutName];
        if (this.state.layoutName==='cise') layout = {...layout, clusters: this.clusterInfo};
        return layout;
    }


    getNetworkElements () {
        // load the elements (nodes and edges) from the /interactions endpoint

        this.setState({
            loaded: false, 
            loadingError: false,
            submissionStatus: '',
            deletionStatus: ''
        });
    
        const url = (
            `${settings.apiUrl}/pulldowns/${this.props.pulldownId}/interactions?` +
            `analysis_type=${this.state.clusteringAnalysisType}&` +
            `subcluster_type=${this.state.subclusterType}`
        );
    
        d3.json(url).then(data => {

            // include only clusters with more than one node
            const clusters = data.clusters.filter(cluster => cluster.protein_group_ids.length > 1);
            const clusterIds = [...new Set(clusters.map(cluster => cluster.cluster_id))];
            const parentNodes = data.parent_nodes;

            // whether each parent node represents a cluster or subcluster
            parentNodes.forEach(node => {
                node.data.type = node.data.parent ? 'subcluster' : 'cluster'
            });

            // the ids of the parent nodes that correspond to clusters
            const clusterParentNodeIds = parentNodes
                .filter(node => node.data.type==='cluster')
                .map(node => node.data.id);
            
            // create parent nodes for the un-subclustered nodes in each cluster
            const unsubclusteredParentNodes = [];
            data.nodes.forEach(node => {
        
                // if the node is in a real subcluster, we don't need to do anything
                if (!clusterParentNodeIds.includes(node.data.parent)) return;

                const clusterId = node.data.parent;
                const newId = `${clusterId}-'unclustered`;
                node.data.parent = newId;

                // if a parent node for this cluster already exists, don't create it
                if (unsubclusteredParentNodes.map(node => node.data.id).includes(newId)) return;
                unsubclusteredParentNodes.push({
                    data: {
                        id: newId, 
                        parent: clusterId, 
                        type: 'unsubclustered',
                    }
                });
            });

            // create a parent node for the unclustered nodes
            const unclusteredParentNodeId = 'unclustered';
            const unclusteredParentNode = {data: {id: unclusteredParentNodeId}};
            
            // make this node the parent of the unclustered nodes
            data.nodes.forEach(node => {
                if (!node.data.parent) node.data.parent = unclusteredParentNodeId;
            });
        
            let elements = [...data.nodes, ...data.edges];
            if (this.state.includeParentNodes) {
                elements = [...parentNodes, unclusteredParentNode, ...unsubclusteredParentNodes, ...elements];
            }

            // lists of the node ids in each cluster (only required for the CiSE layout)
            this.clusterInfo = clusters.map(cluster => cluster.protein_group_ids);

            this.elements = elements;
            this.setState({loaded: true, loadingError: false});
        },
        error => {
            this.elements = [];
            this.setState({loaded: true, loadingError: true});
        });
    }


    getSavedNetwork () {
        this.setState({
            loaded: false, 
            loadingError: false,
            submissionStatus: '',
            deletionStatus: ''
        });
        const url = `${settings.apiUrl}/pulldowns/${this.props.pulldownId}/network`;
        d3.json(url).then(data => {
            this.elements = [
                ...data.cytoscape_json.elements.nodes,
                ...data.cytoscape_json.elements.edges
            ];
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
                <div className="flex pb2">

                    {/* Top row - scatterplot controls */}
                    <div className='w-100 flex flex-wrap items-end'>
                        <div className='pt2 pr2'>
                            <ButtonGroup 
                                label='Layout' 
                                values={['circle', 'concentric', 'cose', 'fcose', 'coseb', 'cise']}
                                labels={['Circle', 'Concentric', 'CoSE', 'fCoSE', 'CoSE-Bilkent', 'CiSE']}
                                activeValue={this.state.layoutName}
                                onClick={value => this.setState({layoutName: value})}
                            />
                        </div>
                        <div className='pt2 pr2'>
                            <ButtonGroup 
                                label='Clustering type' 
                                values={['original', 'new']}
                                labels={['Original', 'New']}
                                activeValue={this.state.clusteringAnalysisType}
                                onClick={value => this.setState({clusteringAnalysisType: value})}
                            />
                        </div>
                        <div className='pt2 pr2'>
                            <ButtonGroup 
                                label='Subcluster type' 
                                values={['core-complexes', 'subclusters']}
                                labels={['Core complexes', 'Subclusters']}
                                activeValue={this.state.subclusterType}
                                onClick={value => this.setState({subclusterType: value})}
                            />
                        </div>
                        <div className='pt2 pr2'>
                            <ButtonGroup 
                                label='Use compound nodes' 
                                values={[true, false]}
                                labels={['Yes', 'No']}
                                activeValue={this.state.includeParentNodes}
                                onClick={value => this.setState({includeParentNodes: value})}
                            />
                        </div>
                        <div className='pt2 pr2'>
                            <ButtonGroup 
                                label='Show saved network' 
                                values={[true, false]}
                                labels={['Yes', 'No']}
                                activeValue={this.state.showSavedNetwork}
                                onClick={value => this.setState({showSavedNetwork: value})}
                            />
                        </div>
                        <div className='f6 simple-button' onClick={() => {}}>
                            {'Reset'}
                        </div>
                    </div>
                </div>

                <div className="w-100 cytoscape-container">
                    {this.state.loaded ? (
                        <CytoscapeComponent
                            style={{width: '500px', height: '500px'}}
                            elements={this.elements}
                            stylesheet={networkStylesheet}
                            minZoom={0.1}
                            maxZoom={3.0}
                            zoom={1.0}
                            cy={cy => {this.cy = cy}}
                        />
                    ) : (
                        null
                    )}
                </div>

                <div className='w-100 flex'>
                    <Button
                        text={'Save network'}
                        className={'ma2 bp3-button'}
                        onClick={() => this.saveNetwork()}
                        intent={this.state.submissionStatus || 'none'}
                    />
                    <Button
                        text={'Delete saved network'}
                        className={'ma2 bp3-button'}
                        onClick={() => this.deleteSavedNetwork()}
                        intent={this.state.deletionStatus || 'none'}
                    />
                </div>
            </div>

        );
    }
}
