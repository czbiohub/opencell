
// the xy size of the z-stacks
const zSliceSize = 600;

// the number of z-slices in the z-stacks
const numZSlices = 27;

// API URLs
const devApi = 'http://localhost:5000';
const prodApi = `http://${window.location.host}/api`;

let apiUrl = prodApi;

export default {
    zSliceSize,
    numZSlices,
    apiUrl,
}
