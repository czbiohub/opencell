
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

        // WARNING: hard-coded indicies for DAPI and GFP volume data
        // that is, the DAPI volume is given by `this.props.volumes[this.dapiInd]`
        // this order is determined in App.componentDidMount
        this.dapiInd = 0;
        this.gfpInd = 1;

        // the same indicies keyed by the values of this.props.localizationChannel 
        this.volumeInds = {
            'DAPI': this.dapiInd,
            'GFP': this.gfpInd,
        };

        // hard-coded size of the image data (assuming square aspect ratio)
        this.imageSize = 600;

    }

    
    componentDidMount() {
        this.initViewer();
        if (this.props.stacksLoaded) {
            this.maybeInitData();
            this.displaySlice();
        }
    }


    componentDidUpdate (prevProps) {

        if (!this.props.stacksLoaded) return;

        this.maybeInitData();

        // TODO check whether any of the display-related props have changed
        // (if not, there's no reason to call displaySlice)
        this.displaySlice();
    }


    maybeInitData() {

        // get the volume shape and initialize the image array 
        // only if this is the first update after the NRRD files loaded
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
        
        const context = canvas.node().getContext('2d');
        //const displaySlice = this.displaySlice();

        // trying and failing to add zoom and pan to the canvas
        //canvas.call(d3.zoom().scaleExtent([1, 8]).on('zoom', zoom));
        function zoom () {

            const transform = d3.event.transform;
            const imageData = context.getImageData(0, 0, this.imageSize, this.imageSize);

            context.save();

            context.clearRect(0, 0, canvas.property('width'), canvas.property('height'));

            context.translate(transform.x, transform.y);
            context.scale(transform.k, transform.k);

            // TODO: how to re-draw the image (in imageData) without using putImageData?
            // (because putImageData ignores the context's transform, 
            // which we just set above using .translate and .scale)
            context.restore();
        }

        this.canvas = canvas.node();
    }


    displaySlice() {

        if (!this.props.volumes) return;

        const scaleIntensity = (intensity, min, max, gamma) => {
            if (intensity < min) return 0;
            if (intensity > max) return 255;
            intensity -= min;
            intensity /= (max - min);
            intensity = Math.pow(intensity, gamma);
            intensity *= 255;
            return intensity;
        }

        const gfpRange = [this.props.gfpMin, this.props.gfpMax].map(val => val*255/100);
        const dapiRange = [this.props.dapiMin, this.props.dapiMax].map(val => val*255/100);

        // display a single channel in grayscale
        if (this.props.localizationChannel!=='Both') {

            const ind = this.volumeInds[this.props.localizationChannel];
    
            const [min, max] = [dapiRange, gfpRange][ind];
            const gamma = [this.props.dapiGamma, this.props.gfpGamma][ind];

            const slice = this.props.volumes[ind].data.slice(
                this.props.zIndex*this.numPx, (this.props.zIndex + 1)*this.numPx
            );

            let val;
            let sliceInd = 0;
            for (let ind = 0; ind < this.imData.length; ind += 4) {
                val = scaleIntensity(slice[sliceInd], min, max, gamma);
                this.imData[ind] = val;
                this.imData[ind + 1] = val;
                this.imData[ind + 2] = val;
                sliceInd += 1;
            }
        
        // display color image (DAPI in gray and GFP in green)
        } else {

            // hard-coded weights for the green channel
            //const [redRatio, greenRatio, blueRatio] = [.1, .92, .1];

            // hard-coded weights for blue (DAPI)
            const [redRatio, greenRatio, blueRatio] = [0, 0, 1];

            const slices = this.props.volumes.map(volume => {
                return volume.data.slice(this.props.zIndex*this.numPx, (this.props.zIndex + 1)*this.numPx);
            });
            
            let sliceInd = 0;
            let gfpVal, dapiVal;
            for (let ind = 0; ind < this.imData.length; ind += 4) {

                gfpVal = scaleIntensity(slices[this.gfpInd][sliceInd], gfpRange[0], gfpRange[1], this.props.gfpGamma);
                dapiVal = scaleIntensity(slices[this.dapiInd][sliceInd], dapiRange[0], dapiRange[1], this.props.dapiGamma);

                this.imData[ind] = gfpVal + redRatio*dapiVal;
                this.imData[ind + 1] = gfpVal + greenRatio*dapiVal;
                this.imData[ind + 2] = gfpVal + blueRatio*dapiVal;
                sliceInd += 1;
            }
        }

        // draw the image on the canvas
        let context = this.canvas.getContext('2d');
        const imageData = context.getImageData(0, 0, this.imageSize, this.imageSize);
        imageData.data.set(this.imData);
        context.putImageData(imageData, 0, 0);

        // HACK: flip the image vertically 
        // to align it with the initial top-down view in the volume rendering
        if (context.getTransform().m22===1) {
            context.scale(1, -1);
            context.translate(0, -this.canvas.height);
        }
        context.drawImage(this.canvas, 0, 0, this.imageSize, this.imageSize);
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
