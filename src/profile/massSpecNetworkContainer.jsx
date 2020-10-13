
import * as d3 from 'd3';
import React, { Component } from 'react';
import { Button, Checkbox } from "@blueprintjs/core";
import chroma from 'chroma-js';

import cytoscape from 'cytoscape';
import cola from 'cytoscape-cola';
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

cytoscape.use(cola);
cytoscape.use(cise);
cytoscape.use(fcose);
cytoscape.use(coseBilkent);
cytoscape.use(nodeHtmlLabel);


function tplFactory(customClassName) {
    // returns the tpl function that is used by the nodeHtmlLabel cytoscape plugin
    // to generate the node label container's innerHTML property
    // (and therefore must return a string of serialized HTML)
    // this tpl function takes the data object associated with a node as its only argument

    return d => {
    
        // parent nodes, which do not have gene names, should be unlabeled
        if (!d.uniprot_gene_names) return '<span></span>';

        const names = d.uniprot_gene_names.map(name => {
            const inOpencell = d.opencell_target_names.includes(name);
            if (inOpencell) {
                return `<span class='cy-node-label cy-node-label-in-opencell'>${name}</span>`
            }
            return `<span class='cy-node-label'>${name}</span>`
        })
        return `<div class='cy-node-label-container ${customClassName}' id=${d.id}>${names.join(', ')}</div>`;
    }
}


export default class MassSpecNetworkContainer extends Component {
    static contextType = settings.ModeContext;

    constructor (props) {
        super(props);

        this.state = {

            layoutName: 'coseb',

            includeParentNodes: true,

            showSavedNetwork: false,

            // 'subclusters' or 'core-complexes'
            subclusterType: 'core-complexes',

            // placeholder for resetting the visualization
            resetPlotZoom: false,

            loaded: false,
            loadingError: false,
        };
    
        this.elements = [];

        const commonNodeLabelProps = {valign: 'center', valignBox: 'center'};
        this.nodeHtmlLabel = [
            {
                query: 'node[type="hit"]',
                tpl: tplFactory('cy-hit-node-label-container'),
                ...commonNodeLabelProps
            },{
                query: 'node[type="bait"]',
                tpl: tplFactory('cy-bait-node-label-container'),
                ...commonNodeLabelProps
            },{
                query: 'node[type="pulldown"]',
                tpl: tplFactory('cy-pulldown-node-label-container'),
                ...commonNodeLabelProps
            },
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

        // if we need to load the network data again
        if (
            this.props.pulldownId!==prevProps.pulldownId || 
            this.state.includeParentNodes!==prevState.includeParentNodes ||
            this.state.showSavedNetwork!==prevState.showSavedNetwork ||
            this.state.clusteringAnalysisType!==prevState.clusteringAnalysisType ||
            this.state.subclusterType!==prevState.subclusterType
        ) {
            this.getData();    
        }

        // run the layout only if state.loaded has switched from false to true,
        // or if the layoutName has changed
        else if (
            this.cy && 
            (this.state.loaded && !prevState.loaded) ||
            this.state.layoutName!==prevState.layoutName
        ) {
            try {
                // attempt to center and lock the target's node (this does not seem to apply to the layout)
                // const targetNode = this.cy.filter('node[type="bait"]');
                // targetNode.position({x: 250, y: 250}).lock();
                // if (targetNode.isChild()) {
                //     targetNode.parent().lock();
                // }

                // remove any unconnected nodes (other than parent nodes)
                // note: these correspond to nodes that represent pulldowns in which
                // the target appeared with a protein group different from the one with which
                // it appeared in its own pulldown
                this.cy.nodes(':childless').difference(this.cy.edges().connectedNodes()).remove();

                this.cy.nodeHtmlLabel(this.nodeHtmlLabel);

                // run the layout only if the elements were loaded from scratch
                if (!this.state.showSavedNetwork) {
                    const layout = this.cy.layout({animate: false, ...this.getLayout()});
                    // console.log('Running layout');
                    layout.run();  
                }

                // call defineLabelEventHandlers using an event that is always triggered,
                // whether the network was loaded from scratch or from a saved layout
                this.cy.on('render', this.defineLabelEventHandlers);

                // cy.fit is necessary if the network was loaded from a saved layout
                this.cy.fit();
            }
            catch (err) {
                console.log(err);
            }
        }
    }

    getData () {

        this.elements = [];
        if (this.cy) {
            this.cy.destroy();
        }

        this.setState({
            loaded: false, 
            loadingError: false,
            submissionStatus: '',
            deletionStatus: ''
        });

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

        const labels = d3.selectAll(".cy-node-label")
            .on("click", function () {
                const geneName = d3.select(this).text();
                handleGeneNameSearch(geneName);
            });

        //console.log(labels._groups);
        
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

        const url = (
            `${settings.apiUrl}/pulldowns/${this.props.pulldownId}/interactions?` +
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

        const allLayoutNames = ['cola', 'cose', 'fcose', 'coseb', 'cise'];
        const allLayoutLabels = ['Cola', 'CoSE', 'fCoSE', 'CoSE-Bilkent', 'CiSE'];
        
        const layoutNames = this.context==='public' ? ['fcose', 'coseb'] : allLayoutNames;
        const layoutLabels = this.context==='public' ? ['fCoSE', 'CoSE-Bilkent'] : allLayoutLabels;

        return (
            <div className='relative'>

                {this.state.loadingError ? <div className='f2 tc loading-overlay'>No data</div> : (null)}
                {!this.state.loaded ? <div className='f2 tc loading-overlay'>Loading...</div> : (null)}

                {/* display controls */}
                <div className="flex items-end pb2">

                    {/* Top row - scatterplot controls */}
                    {(this.context==='private') ? (
                        <div className='w-100 flex flex-wrap items-end'>
                            <div className='pt2 pr2'>
                                <ButtonGroup 
                                    label='Layout' 
                                    values={layoutNames}
                                    labels={layoutLabels}
                                    activeValue={this.state.layoutName}
                                    onClick={value => this.setState({layoutName: value})}
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
                                    label='Subcluster type' 
                                    values={['core-complexes', 'subclusters']}
                                    labels={['Core complexes', 'Subclusters']}
                                    activeValue={this.state.subclusterType}
                                    onClick={value => this.setState({subclusterType: value})}
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
                        </div>
                    ) : null}

                    <div className='f6 simple-button' onClick={() => {this.cy.fit()}}>
                        {'Reset zoom'}
                    </div>
                </div>

                <div className="w-100 cytoscape-container">
                    {this.state.loaded ? (
                        <CytoscapeComponent
                            style={{width: '700px', height: '600px'}}
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
                
                {this.context==='private' ? (
                <div className='pt5 w-100 flex'>
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
                ) : null}

            </div>

        );
    }
}
