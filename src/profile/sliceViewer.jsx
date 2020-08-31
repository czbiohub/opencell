
import * as d3 from 'd3';
import React, { Component } from 'react';

import 'tachyons';
import './Profile.css';


export default class SliceViewer extends Component {

    constructor (props) {

        super(props);
        this.state = {};

        this.initViewer = this.initViewer.bind(this);
        this.maybeInitData = this.maybeInitData.bind(this);
        this.displaySlice = this.displaySlice.bind(this);
        this.zoom = this.zoom.bind(this);

        // WARNING: hard-coded indices for 405 and 488 image data
        // that is, the 405 volume is given by `this.props.volumes[this.ind405]`
        this.ind405 = 0;
        this.ind488 = 1;

        // the same indicies keyed by the values of this.props.channel 
        this.volumeInds = {
            '405': this.ind405,
            '488': this.ind488,
        };

        // hard-coded size of the image data (assuming square aspect ratio)
        this.imageSize = 600;
    }

    componentDidMount() {
        this.initViewer();
        if (!this.props.loaded) return;
        this.maybeInitData();
        this.displaySlice();
    }

    componentDidUpdate (prevProps) {
        if (!this.props.loaded) return;
        this.maybeInitData();
        this.displaySlice();
    }

    componentWillUnmount () {
        this.props.setCameraPosition(this.cameraPosition);
        this.props.setCameraZoom(this.cameraZoom);
    }


    maybeInitData() {

        // get the volume shape and initialize the image array 
        // only if this is the first update after the images were loaded
        if (this.imData) return;
        if (!this.props.volumes) return;

        const volume = this.props.volumes[0];
        this.shape = [volume.xLength, volume.yLength, volume.zLength];
        this.numPx = this.shape[0]*this.shape[1];

        // placeholder RGBA image array into which we will dump the displayed slice
        this.imData = [...Array(this.numPx).keys()].map(ind => {
            return [0, 0, 0, 255];
        }).flat();

        this.imData = new Uint8ClampedArray(this.imData);
    }


    initViewer() {

        // how to display an image given a linearized uint8 array
        // https://stackoverflow.com/questions/42410080/draw-an-exisiting-arraybuffer-into-a-canvas-without-copying

        const canvas = d3.select(this.node)
                         .append('canvas')
                         .style('margin', 'auto')
                         .style('display', 'block')
                         .attr("width", this.imageSize)
                         .attr("height", this.imageSize);
        
        // create an in-memory canvas to call putImageData on
        // (needed because putImageData ignores the context's transform)
        const memCanvas = document.createElement("canvas");
        d3.select(memCanvas).attr("width", this.imageSize).attr("height", this.imageSize);

        this.canvas = canvas.node();
        this.memCanvas = memCanvas;

        const zoom = d3.zoom()
            .scaleExtent([0.5, 8])
            .on('zoom', () => this.zoom(d3.event.transform));

        canvas.call(zoom);
    }


    zoom(transform) {
        
        const context = this.canvas.getContext("2d");
        context.save();
        context.clearRect(0, 0, this.canvas.width, this.canvas.height);

        context.translate(transform.x, transform.y);
        context.scale(transform.k, transform.k);
        
        // flip the image vertically to align it
        // with the initial top-down view in the volume rendering
        context.scale(1, -1);
        context.translate(0, -this.canvas.height);
        
        // calculate the current xy position in the coordinates used by the volume viewer camera
        // for reference, context.transform()(.e, .f) corner coordinates are
        // (300, 300)  (-300, 300)
        // (300, -300)  (-300, -300)
        // and the threejs camera.position(.x, .y) corner coordinates are:
        // (0, 600) ---- (600, 600)
        // (0, 0)   ---- (600, 0)
        this.cameraPosition = {
            x: -(context.getTransform().e - this.canvas.width/2)/transform.k, 
            y: (context.getTransform().f - this.canvas.height/2)/transform.k,
        };
        this.cameraZoom = transform.k;

        // re-draw the image (without smoothing, to show the true pixels when zoomed in)
        context.imageSmoothingEnabled = false;
        context.drawImage(this.memCanvas, 0, 0, this.imageSize, this.imageSize);
        context.restore();

        // save the transform so we can re-apply it after changing the z-slice
        this.lastTransform = transform;
    }


    displaySlice() {

        if (!this.props.volumes) return;

        // clamp the z-index to zero in z-projection mode
        const zIndex = this.props.mode==='Proj' ? 0 : this.props.zIndex;

        const scaleIntensity = (intensity, min, max, gamma) => {
            if (intensity < min) return 0;
            if (intensity > max) return 255;
            intensity -= min;
            intensity /= (max - min);
            intensity = Math.pow(intensity, gamma);
            intensity *= 255;
            return intensity;
        }

        const range488 = [this.props.min488, this.props.max488].map(val => val*255/100);
        const range405 = [this.props.min405, this.props.max405].map(val => val*255/100);

        // a single channel in grayscale
        if (this.props.channel!=='Both') {

            const ind = this.volumeInds[this.props.channel];
    
            const [min, max] = [range405, range488][ind];
            const gamma = [this.props.gamma405, this.props.gamma488][ind];

            const slice = this.props.volumes[ind].data.slice(
                zIndex*this.numPx, (zIndex + 1)*this.numPx
            );

            let val;
            let sliceInd = 0;
            for (let ind = 0; ind < this.imData.length; ind += 4) {
                val = scaleIntensity(slice[sliceInd], min, max, gamma);
                this.imData[ind + 0] = val;
                this.imData[ind + 1] = val;
                this.imData[ind + 2] = val;
                sliceInd += 1;
            }
        
        // both channels in a gray-blue image
        } else {

            // hard-coded weights for blue (405 channel)
            const [redRatio, greenRatio, blueRatio] = [0, 0, 1];

            const slices = this.props.volumes.map(volume => {
                return volume.data.slice(
                    zIndex*this.numPx, (zIndex + 1)*this.numPx
                );
            });
            
            let sliceInd = 0;
            let val405, val488;
            for (let ind = 0; ind < this.imData.length; ind += 4) {

                val488 = scaleIntensity(
                    slices[this.ind488][sliceInd], 
                    range488[0], 
                    range488[1], 
                    this.props.gamma488
                );
        
                val405 = scaleIntensity(
                    slices[this.ind405][sliceInd], 
                    range405[0], 
                    range405[1], 
                    this.props.gamma405
                );

                this.imData[ind + 0] = val488 + redRatio * val405;
                this.imData[ind + 1] = val488 + greenRatio * val405;
                this.imData[ind + 2] = val488 + blueRatio * val405;
                sliceInd += 1;
            }
        }

        // draw the image on the in-memory canvas
        let memContext = this.memCanvas.getContext('2d');
        const imageData = memContext.getImageData(0, 0, this.imageSize, this.imageSize);
        imageData.data.set(this.imData);
        memContext.putImageData(imageData, 0, 0);

        // draw the image on the real canvas
        const context = this.canvas.getContext("2d");
        context.drawImage(this.memCanvas, 0, 0, this.imageSize, this.imageSize);

        // re-apply the existing transform
        this.zoom(this.lastTransform || d3.zoomIdentity);
    }


    render() {
        return (
            <div>
                <div 
                    ref={node => this.node = node}
                    style={{backgroundColor: 'black'}}
                />
            </div>
        );
    }
}
