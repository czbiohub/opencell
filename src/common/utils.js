
import * as d3 from 'd3';
import settings from './settings.js';


export function loadAnnotatedFovs (cellLineId, onLoad) {

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
    });
}


export function loadStack(url, onLoad) {
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


export function loadProj(url, onLoad) {
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