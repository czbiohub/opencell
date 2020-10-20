
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

            layoutName: 'cola',

            includeParentNodes: true,

            showSavedNetwork: false,

            // 'subclusters' or 'core-complexes'
            subclusterType: 'core-complexes',

            // placeholder for resetting the visualization
            resetPlotZoom: false,

            loaded: false,
            loadingError: false,

            colaEdgeLength: 10,
            colaNodeSpacing: 5,
        };
    
        this.elements = [];

        const commonNodeLabelProps = {
            valign: 'center', 
            valignBox: 'center',
            cssClass: 'node-html-label-container'
        };
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

        this.initializeNetwork = this.initializeNetwork.bind(this);
        this.defineLabelEventHandlers = this.defineLabelEventHandlers.bind(this);
    }

    componentDidMount() {
        if (this.props.id) {
            this.getData();
        }
    }

    componentDidUpdate (prevProps, prevState) {

        // if we need to load the network data again
        if (
            this.props.id!==prevProps.id || 
            this.state.includeParentNodes!==prevState.includeParentNodes ||
            this.state.showSavedNetwork!==prevState.showSavedNetwork ||
            this.state.clusteringAnalysisType!==prevState.clusteringAnalysisType ||
            this.state.subclusterType!==prevState.subclusterType
        ) {
            this.getData(); 
            return;   
        }

        if (!this.cy) return;

        // initialize the network if state.loaded has switched from false to true,
        // or if the layout name has changed
        if((this.state.loaded && !prevState.loaded) || this.state.layoutName!==prevState.layoutName) {
            this.initializeNetwork();
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

    initializeNetwork () {
        try {
            // remove any unconnected nodes (other than parent/compound nodes)
            // (these correspond to nodes that represent pulldowns in which
            // the target appeared with a protein group different from the one with which
            // it appeared in its own pulldown)
            this.cy.nodes(':childless').difference(this.cy.edges().connectedNodes()).remove();

            // remove any existing html node labels
            d3.selectAll('.node-html-label-container').remove();

            // create the node html labels
            this.cy.nodeHtmlLabel(this.nodeHtmlLabel, {enablePointerEvents: true});

            // run the layout only if the elements were loaded from scratch
            if (!this.state.showSavedNetwork) {
                const layout = this.cy.layout({animate: true, randomize: true, ...this.getLayout()});
                layout.on('layoutstop', this.defineLabelEventHandlers);
                layout.run();  

            // if the layout was loaded from a saved layout
            } else {
                this.cy.one('render', this.defineLabelEventHandlers);
                this.cy.fit();    
            }
        }
        catch (err) {
            console.log(err);
        }
    }

    saveNetwork () {
        // save the network
        // *assumes* the network is a pulldown network (not an interactor network)
        const data = {
            cytoscape_json: this.cy.json(),
            client_metadata: {last_modified: (new Date()).toString()}
        };
        this.setState({deletionStatus: ''});
        utils.putData(`${settings.apiUrl}/pulldowns/${this.props.id}/saved_network`, data)
            .then(response => {
                console.log(response.json());
                if (!response.ok) throw new Error('Error saving cytoscape layout');
                this.setState({submissionStatus: 'success', showSavedNetwork: true});
            })
            .catch(error => this.setState({submissionStatus: 'danger'}));
    }


    deleteSavedNetwork () {
        this.setState({submissionStatus: ''});
        utils.deleteData(`${settings.apiUrl}/pulldowns/${this.props.id}/saved_network`)
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
        
        // fit the layout, just in case
        cy.fit();

        // define event handlers for the 'real' (non-compound) nodes
        cy.nodes(':childless')
            .on('mouseover', event => {
                event.target.connectedEdges().addClass('hovered-node-edge');
            })
            .on('mouseout', event => {
                event.target.connectedEdges().removeClass('hovered-node-edge');
            })
            .on('click', event => {
                console.log('Node clicked');
                const geneName = event.target.data().uniprot_gene_names[0];
                handleGeneNameSearch(geneName);
            });
        
        // define onclick event handlers for the node labels
        // TODO: this is redundant with the onClick handlers defined on the nodes themselves
        // (assuming that the nodes are wider than the labels)
        d3.selectAll(".cy-node-label")
            .on("click", function () {
                console.log('Node label clicked');
                const geneName = d3.select(this).text();
                handleGeneNameSearch(geneName);
            });
    }


    getLayout () {
        let layout = networkLayouts[this.state.layoutName];
        if (this.state.layoutName==='cola') {
            layout.edgeLength = this.state.colaEdgeLength;
            layout.nodeSpacing = this.state.colaNodeSpacing;
        }
        return layout;
    }


    getNetworkElements () {
        // load the cytoscape elements (nodes and edges)

        const endpoint = this.props.idType==='pulldown' ? 'pulldowns' : 'interactors';
        const url = (
            `${settings.apiUrl}/${endpoint}/${this.props.id}/network?` +
            `subcluster_type=${this.state.subclusterType}`
        );

        d3.json(url).then(data => {

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
                elements = [
                    unclusteredParentNode, 
                    ...parentNodes, 
                    ...unsubclusteredParentNodes, 
                    ...elements
                ];
            }

            this.elements = elements;
            this.setState({loaded: true, loadingError: false});
        },
        error => {
            this.elements = [];
            this.setState({loaded: true, loadingError: true});
        });
    }


    getSavedNetwork () {
        const url = `${settings.apiUrl}/pulldowns/${this.props.id}/saved_network`;
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

        const allLayoutNames = ['cola', 'fcose', 'coseb'];
        const allLayoutLabels = ['Cola', 'fCoSE', 'CoSE-Bilkent'];
        
        const layoutNames = this.context==='public' ? ['cola', 'coseb'] : allLayoutNames;
        const layoutLabels = this.context==='public' ? ['Cola', 'CoSE-Bilkent'] : allLayoutLabels;

        return (
            <div className='relative'>

                {this.state.loadingError ? <div className='f2 tc loading-overlay'>No data</div> : (null)}
                {!this.state.loaded ? <div className='f2 tc loading-overlay'>Loading...</div> : (null)}

                {/* display controls */}
                <div className="pb2">

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
                            <div className='pt2 pr2'>
                                <ButtonGroup 
                                    label='Cola edge length' 
                                    values={[10, 50, 100, 200]}
                                    activeValue={this.state.colaEdgeLength}
                                    onClick={value => this.setState({colaEdgeLength: value})}
                                />
                            </div>
                            <div className='pt2 pr2'>
                                <ButtonGroup 
                                    label='Cola node spacing' 
                                    values={[1, 5, 10, 20]}
                                    activeValue={this.state.colaNodeSpacing}
                                    onClick={value => this.setState({colaNodeSpacing: value})}
                                />
                            </div>
                        </div>
                    ) : null}

                    <div className='w-100 pt2'>
                    <div className='f6 simple-button' onClick={() => {this.initializeNetwork()}}>
                        {'Re-run layout'}
                    </div>
                    <div className='f6 simple-button' onClick={() => {this.cy.fit()}}>
                        {'Reset zoom'}
                    </div>
                    </div>
                </div>

                <div className="w-100 cytoscape-container">
                    {this.state.loaded ? (
                        <CytoscapeComponent
                            style={{width: this.props.width, height: this.props.height}}
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
