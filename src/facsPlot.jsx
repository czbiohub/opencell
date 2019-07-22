import * as d3 from 'd3';
import React, { Component } from 'react';

import XYFrame from "semiotic/lib/XYFrame"


class FACSPlot extends Component {

    constructor (props) {
        super(props);

        this.state = {
            loaded: false,
        };

        this.aspectRatio = .8;

        const strokeColor = {
            'sample': 'none',
            'reference': '#666',
            'gfp': 'green',
        };

        const fillColor = {
            'sample': 'gray',
            'reference': 'none',
            'gfp': 'lightgreen',
        };

        // default hard-coded props for the XYFrame
        this.frameProps = {  
         
            lines: [
                {
                    title: "Sample", 
                    coordinates: [],
                },{
                    title: "Fitted reference", 
                    coordinates: [],
                },
            ],
            
            margin: { left: 5, bottom: 5, right: 5, top: 5 },

            xAccessor: "x",
            yAccessor: "y",
            yExtent: [0, 7e-4],
            xExtent: [0, 10000],

            lineType: 'area',
            lineStyle: (d, i) => {
                return {
                    strokeWidth: 1,
                    stroke: strokeColor[d.id],
                    fill: fillColor[d.id],
                    fillOpacity: .5,
                };
            },

            axes: [],

            // axes: [
            //     {
            //         orient: "left", 
            //         label: "Intensity (hlog)", 
            //         tickFormat: e => e/1e3
            //     },{ 
            //         orient: "bottom", 
            //         label: { 
            //             name: "", 
            //             locationDistance: 5
            //         } 
            //     }
            // ]
        };
    }

    fetchData () {

        fetch(`http://localhost:5000/facshistograms/${this.props.cellLineId}`)
            .then(result => result.json())
            .then(data => {

                if (!data) {
                    this.setState({loaded: false});
                    return;
                }

                const sampleLine = {
                    id: 'sample',
                    title: 'Sample',
                    coordinates: data.x.map((val, ind) => ({
                        x: val, 
                        y: data.y_sample[ind]})),
                };

                const refLine = {
                    id: 'reference',
                    title: 'Fitted reference',
                    coordinates: data.x.map((val, ind) => ({
                        x: val, 
                        y: data.y_ref_fitted[ind]})),
                };

                const gfpLine = {
                    id: 'gfp',
                    title: 'Subtracted sample',
                    coordinates: data.x.map((val, ind) => ({
                        x: val, 
                        y: data.y_sample[ind] - data.y_ref_fitted[ind]
                    })),
                };
                
                // clamp negative values in the subtracted histogram to zero
                gfpLine.coordinates.forEach(coord => {
                    coord.y = coord.y < 0 ? 0 : coord.y;
                });

                // plot data
                this.frameProps.lines = [sampleLine, refLine, gfpLine];
                
                // plot size
                this.frameProps.size = [this.props.width, this.props.width * this.aspectRatio],

                this.setState({loaded: true});

            },
            error => console.log(error));
    }

    componentDidMount () {
        this.fetchData();
    }

    componentDidUpdate(prevProps) {
        if(this.props.cellLineId !== prevProps.cellLineId) {
            this.fetchData();
        }
    }

    render () {
        return this.state.loaded ? <XYFrame lines={this.frameProps.lines} {...this.frameProps}/> : null;
    }
}


export default FACSPlot;