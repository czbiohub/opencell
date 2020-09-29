
const networkStylesheet = [
    {
        selector: 'node',
        style: {
            height: 5,
            width: 5,
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
        }
    },{
        selector: 'node[type="cluster"]:parent',
        style: {
            'background-opacity': 0.2,
            'background-color': "#999",
            'border-opacity': 0,
            'border-width': 0.5,
        }
    },{
        selector: 'node[type="subcluster"]:parent',
        style: {
            'background-color': "#4096d4",
            'background-opacity': 0.1,
            'border-opacity': 0,
        }
    },{
        selector: 'node[id="unclustered"]:parent,node[type="unsubclustered"]:parent',
        style: {
            'border-color': "#aaa",
            'border-width': 2,
            'border-opacity': 0.5,
            'background-opacity': 0,
        }
    },{
        selector: 'node[type="bait"]',
        style: {
            'background-color': '#51ade1',
            'opacity': 1.0,
        }
    },{
        selector: 'node[type="hit"]',
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