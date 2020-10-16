
const networkStylesheet = [
    {
        selector: 'node',
        style: {
            // use wide nodes to prevent node labels from overlapping in the cola layout
            height: 10,
            width: 30,
            'background-color': '#555',

            // this turns off the overlay when the node is clicked
            'overlay-padding': '0px',
            'overlay-opacity': 0, 
        }
    },{
        selector: 'node:parent',
        style: {
            // compound node labels (for debugging)
            //'label': 'data(id)',
            'shape': 'round-rectangle',
        }
    },{
        // compound nodes for clusters
        selector: 'node[type="cluster"]:parent',
        style: {
            'shape': 'round-rectangle',
            'background-color': "#ccc",
            'background-opacity': 0.2,
            'border-opacity': 0,
            'border-width': 0,
        }
    },{
        // compound nodes for subclusters (always within a cluster compound node)
        selector: 'node[type="subcluster"]:parent',
        style: {
            'shape': 'round-rectangle',
            'background-color': "#ccc",
            'background-opacity': 0.3,
            'border-color': "#999",
            'border-width': 1.0,
            'border-opacity': 0.0,
        }
    },{
        // compound nodes of un-clustered and un-subclustered nodes 
        selector: 'node[id="unclustered"]:parent,node[type="unsubclustered"]:parent',
        style: {
            'shape': 'round-rectangle',
            'border-color': "#ccc",
            'border-width': 1,
            'border-opacity': 0,
            'background-opacity': 0,
        }
    },{
        selector: 'node[type="bait"]',
        style: {
            'background-color': '#51ade1',
            'opacity': 0.0,
        }
    },{
        selector: 'node[type="hit"]',
        style: {
            'background-color': '#ff827d',
            'opacity': 0.0,
        }
    },{
        selector: 'node[type="pulldown"]',
        style: {
            'opacity': 0.0,
        }
    },{
        selector: 'edge',
        style: {
            width: 0.5,
            'line-color': "#333",

            // haystack without arrows
            opacity: 0.10,
            "curve-style": "haystack",

            // bezier with arrows
            // opacity: 0.5,
            // "curve-style": "bezier",
            // "target-arrow-shape": "triangle-backcurve",
            // "arrow-scale": 0.5,
            // "target-arrow-color": "#333",

            // this turns off overlay and disables clicking/dragging the edges
            'overlay-opacity': 0,
            'overlay-padding': '0px',
        }
    },{
        selector: '.hovered-node-edge',
        style: {
            'width': 0.5,
            'opacity': 0.9,
            'line-color': "#000",
        },
    }
];

export default networkStylesheet;