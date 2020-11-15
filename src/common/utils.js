
import * as d3 from 'd3';
import settings from './settings.js';


export async function putData(url, data) {
    const response = await fetch(url, {
        method: 'PUT',
        mode: 'cors',
        cache: 'no-cache',
        credentials: 'same-origin',
        headers: {'Content-Type': 'application/json'},
        referrerPolicy: 'no-referrer',
        body: JSON.stringify(data),
    });
    return await response;
}


export async function deleteData(url) {
    const response = await fetch(url, {
        method: 'DELETE',
        mode: 'cors',
        cache: 'no-cache',
        credentials: 'same-origin',
        referrerPolicy: 'no-referrer',
    });
    return await response;
}


export function getAnnotatedFovMetadata (cellLineId, onLoad, onError) {

    // retrieve the FOV metadata
    const url = `${settings.apiUrl}/lines/${cellLineId}/fovs?fields=rois&onlyannotated=true`
    d3.json(url).then(fovs => {

        // concat all ROIs (note that fov.rois is always list)
        let rois = [].concat(...fovs.map(fov => fov.rois));
        
        const fovState = {
            fovs,
            rois,
            roiId: rois[0]?.id,
            fovId: rois[0]?.fov_id, 
        };
        onLoad(fovState);
    },
    error => onError(error)
    );
}


export function getZStack(url, onLoad) {
    // Load the z-stack of an ROI (as a tiled JPG)
    //
    const sliceSize = settings.zSliceSize;
    const numRawSlices = settings.numZSlices;
    const canvasWidth = sliceSize;
    const canvasHeight = sliceSize * numRawSlices;
    const numPixelsPerSlice = sliceSize * sliceSize;

    const volume = {
        xLength: sliceSize,
        yLength: sliceSize,
        zLength: numRawSlices * 2 - 1,
        data: new Uint8Array(numPixelsPerSlice * (numRawSlices * 2 - 1)),
    };

    const img = new Image;
    let thisPixel, nextPixel;

    // this is required to avoid the 'tainted canvas' error
    img.setAttribute('crossOrigin', '');

    img.onload = function () {
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        canvas.setAttribute('width', canvasWidth);
        canvas.setAttribute('height', canvasHeight);
        context.drawImage(img, 0, 0);
        const imageData = context.getImageData(0, 0, canvasWidth, canvasHeight);

        // copy each raw z-slice and its average with the next raw z-slice
        // into the volume.data array
        for (let z = 0; z < numRawSlices - 1; z++) {
            for (let ind = 0; ind < numPixelsPerSlice; ind++) {
                thisPixel = imageData.data[4*(ind + (z + 0)*numPixelsPerSlice)];
                nextPixel = imageData.data[4*(ind + (z + 1)*numPixelsPerSlice)];
                volume.data[ind + (2*z + 0)*numPixelsPerSlice] = thisPixel;
                volume.data[ind + (2*z + 1)*numPixelsPerSlice] = (thisPixel + nextPixel)/2;
            }
        }

        // copy the last raw z-slice
        let z = numRawSlices - 1;
        for (let ind = 0; ind < numPixelsPerSlice; ind++) {
            thisPixel = imageData.data[(ind + z*numPixelsPerSlice)*4];
            volume.data[ind + 2*z*numPixelsPerSlice] = thisPixel;
        }
        onLoad(volume);
    };
    img.src = url;
}


export function getZProjection(url, onLoad) {
    // Load the 2D z-projection of an ROI
    //
    const sliceSize = settings.zSliceSize;
    const canvasWidth = sliceSize;
    const canvasHeight = sliceSize ;
    const numPixels = sliceSize * sliceSize;

    const proj = {
        xLength: sliceSize,
        yLength: sliceSize,
        zLength: 1,
        data: new Uint8Array(numPixels),
    };

    const img = new Image;
    img.setAttribute('crossOrigin', '');
    img.onload = function () {
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        canvas.setAttribute('width', canvasWidth);
        canvas.setAttribute('height', canvasHeight);
        context.drawImage(img, 0, 0);
        const imageData = context.getImageData(0, 0, canvasWidth, canvasHeight);
        for (let ind = 0; ind < numPixels; ind++) {
            proj.data[ind] = imageData.data[4*ind];
        }
        onLoad(proj);
    };
    img.src = url;
}


export function getNetworkElements(id, idType, subclusterType, onLoad, onError) {
    // 
    // idType : either 'pulldown' or 'ensg'
    // subclusterType : either 'core-complexes' or 'subclusters'
    // onLoad : a function of (parentNodes, nodes, edges)

    const endpoint = idType==='pulldown' ? 'pulldowns' : 'interactors';
    const url = `${settings.apiUrl}/${endpoint}/${id}/network?subcluster_type=${subclusterType}&clustering_analysis_type=${settings.clusteringAnalysisType}`;
    d3.json(url).then(
        data => onLoad(data.parent_nodes, data.nodes, data.edges), error => onError(error)
    );
}


export function generateCSVContent (data) {
    // generate the content of a CSV file (as a string) from an array of dicts
    // in which the keys correspond to the CSV column names
    const sep = ",";
    const newline = "\n";
    const columnNames = Object.keys(data[0]);

    // the header row
    let content = columnNames.join(sep) + newline;

    // create the rows of the CSV from the objects in `data`
    data.forEach(row => {
        const values = columnNames.map(name => row[name]);
        content += (values.join(sep) + newline);
    });

    // remove the trailing newline
    content = content.slice(0, content.length - 1);
    return content;
}


export function triggerCSVDownload (data, filename) {
    // trigger the browser to download a CSV file
    // a little hackish, but it works (originally adapted from a stackoverflow post)
    const content = generateCSVContent(data);
    const mimeType = "text/csv;encoding:utf-8";
    let link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([content], {type: mimeType}));
    link.setAttribute("download", filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}
