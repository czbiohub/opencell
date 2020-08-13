
// the xy size of the z-stack
const zSliceSize = 600;

// the number of z-slices in the z-stack
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
