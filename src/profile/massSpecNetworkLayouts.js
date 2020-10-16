
const colaLayout = {
    name: 'cola',

    // number of ticks per frame; higher is faster but more jerky
    refresh: 1, 

    // max length in ms to run the layout
    maxSimulationTime: 2000, 

    // so you can't drag nodes during layout
    ungrabifyWhileSimulating: false, 

    // on every layout reposition of nodes, fit the viewport
    fit: true, 

    // padding around the simulation
    padding: 5, 

    // constrain layout bounds; { x1, y1, x2, y2 } or { x1, y1, w, h }
    boundingBox: undefined, 

    // whether labels should be included in determining the space used by a node
    nodeDimensionsIncludeLabels: false, 

    // if true, prevents overlap of node bounding boxes
    avoidOverlap: true, 

    // if true, avoids disconnected components from overlapping
    handleDisconnected: true, 

    // when the alpha value (system energy) falls below this value, the layout stops
    convergenceThreshold: 0.01, 

    // extra spacing around nodes (default 10)
    // for node width 30 and height 10, this should be a minimum of 3
    nodeSpacing: 10,

    // edgeLength can be a constant or a function
    // (a range of 10 - 200 works well for node sizes around 10-30)
    edgeLength: undefined, 

    // use DAG/tree flow layout if specified, e.g. { axis: 'y', minSeparation: 30 }
    flow: undefined, 

    // relative alignment constraints on nodes, e.g. {
    // vertical: [[{node: node1, offset: 0}, {node: node2, offset: 5}]], 
    // horizontal: [[{node: node3}, {node: node4}], [{node: node5}, {node: node6}]]}
    alignment: undefined, 

    // list of inequality constraints for the gap between the nodes
    // e.g. [{"axis":"y", "left":node1, "right":node2, "gap":25}]
    gapInequalities: undefined, 

    // symmetric diff edge length in simulation
    edgeSymDiffLength: undefined,

    // jaccard edge length in simulation
    edgeJaccardLength: undefined, 
};


const coseLayout = {
    name: 'cose',

    // multiplier for ideal edge length for 'nested' edges
    // TODO: what are nested edges?
    // small values (less than 1) yield overlapped nodes 
    // 10 yields very large compound node rectangles
    // default 1.2
    nestingFactor: 1.0,

    // default 32
    idealEdgeLength: 100,

    // extra space between components(nodes?) in non-compound graphs
    // doesn't seem to have much of an effect
    // default 40
    componentSpacing: 40,

    // smaller elasticity yields tighter networks
    // note: this appears to be the inverse of the edgeElasticity
    // in the fcose and cose-bilkent layouts
    // default 32
    edgeElasticity: 600,

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


const fcoseLayout = {
    name: 'fcose',
    uniformNodeDimensions: true,

    // default 0.1
    nestingFactor: 1,

    idealEdgeLength: 100,

    // divisor to compute edge forces
    // very large values (e.g. 1000) yield stacked nodes
    // default 0.45
    edgeElasticity: 0.1,

    // separation between nodes (this is specific to fcose)
    // small values (e.g. 1) encourage stacked nodes
    // default 75
    nodeSeparation: 75,

    // default 4500
    // small values seem to encourage stacked nodes
    nodeRepulsion: 4500,

    gravity: 1,
};


const coseBilkentLayout = {
    name: 'cose-bilkent',

    // default 50
    idealEdgeLength: 30,

    // larger values yield tighter networks
    // default 0.45
    edgeElasticity: .5,

    // default 4500
    nodeRepulsion: 4500,

    // default 0.1
    // higher values yield better-separated compound nodes
    nestingFactor: 2,

    // default 0.25
    gravity: 0.25,

    gravityRangeCompound: 1.5,
    gravityCompound: 1.0,
    gravityRange: 3.8,

};


const circleLayout = {
    name: 'circle',
    radius: 150,
    spacingFactor: 1.0
};


const concentricLayout = {
    name: 'concentric',
};


const ciseLayout = {
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


export default {
    cola: colaLayout,
    cose: coseLayout,
    fcose: fcoseLayout,
    coseb: coseBilkentLayout,
    cise: ciseLayout,
    circle: circleLayout,
    concentric: concentricLayout,
};