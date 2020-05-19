
import * as d3 from 'd3';
import settings from './settings.js';


export function loadFovs (cellLineId, onLoad) {

    // retrieve the FOV metadata
    const url = `${settings.apiUrl}/lines/${cellLineId}/fovs?fields=rois`
    d3.json(url).then(fovs => {

        // only FOVs with manual annotations should be displayed
        const viewableFovs = fovs.filter(fov => fov.annotation);

        // concat all ROIs (because fov.rois is a list)
        let rois = [].concat(...viewableFovs.map(fov => fov.rois));
        
        const fovState = {
            rois,
            fovs: viewableFovs,
            roiId: rois[0]?.id,
            fovId: rois[0]?.fov_id, 
        };
        onLoad(fovState);
    });
}


export function loadImage(url, onLoad) {

    // hard-coded xy size and number of z-slices
    // WARNING: these must match the stack to be loaded
    const imageSize = settings.zStackShape[0];
    const numSlices = settings.zStackShape[2];

    const imageWidth = imageSize;
    const imageHeight = imageSize*numSlices;

    const volume = {
        xLength: imageSize,
        yLength: imageSize,
        zLength: numSlices,
        data: new Uint8Array(imageWidth*imageHeight),
    };

    const img = new Image;

    // this is required to avoid the 'tainted canvas' error
    img.setAttribute('crossOrigin', '');

    img.onload = function () {
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        canvas.setAttribute('width', imageWidth);
        canvas.setAttribute('height', imageHeight);
        context.drawImage(img, 0, 0);

        const imageData = context.getImageData(0, 0, imageWidth, imageHeight);
        for (let ind = 0; ind < volume.data.length; ind++) {
            volume.data[ind] = imageData.data[ind*4];
        }
        
        onLoad(volume);
    };

    img.src = url;

}
