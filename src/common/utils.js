

export function loadImage(url, onLoad) {

    // hard-coded xy size and number of z-slices
    // WARNING: these must match the stack to be loaded
    const imageSize = 600;
    const numSlices = 65;

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


