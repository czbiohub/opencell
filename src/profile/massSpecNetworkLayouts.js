
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

    // gravity: 1,
};


const coseBilkentLayout = {
    name: 'cose-bilkent',

    // default 50
    idealEdgeLength: 20,

    // larger values yield tighter networks
    // default 0.45
    edgeElasticity: 1,

    // default 4500
    nodeRepulsion: 4000,

    // default 0.1
    // higher values yield better-separated compound nodes
    nestingFactor: 2,

    // default 0.25
    gravity: 0.25,

    gravityRangeCompound: 1.5,
    gravityCompound: 0.25,
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
    cose: coseLayout,
    fcose: fcoseLayout,
    coseb: coseBilkentLayout,
    cise: ciseLayout,
    circle: circleLayout,
    concentric: concentricLayout,
};