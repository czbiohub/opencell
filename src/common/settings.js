
// z-stack shape
const zStackShape = [600, 600, 55];


// API URLs
const devApi = 'http://localhost:5000';
const prodApi = `http://${window.location.host}/api`;

let apiUrl = devApi;

export default {
    zStackShape,
    apiUrl,
}
