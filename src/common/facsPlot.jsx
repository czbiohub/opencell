import * as d3 from 'd3';
import React, { Component } from 'react';
import chroma from 'chroma-js';

import XYFrame from "semiotic/lib/XYFrame"
import ResponsiveXYFrame from "semiotic/lib/ResponsiveXYFrame"

import settings from '../common/settings.js';


class FACSPlot extends Component {
    //
    // A single FACS plot
    // 
    // props.width : absolute width in pixels (required)
    // props.height : absolute height (optional; hard-coded aspect ratio used if not provided)
    // props.data : 
    // props.isSparkline : whether to generate a minimal (and tiny) plot or a full plot with axes
    // props.showGFP : whether to show the GFP-positive population (the subtracted histogram)  

    constructor (props) {
        super(props);

        this.state = {
            loaded: false,
        };

        this.aspectRatio = .7;

        const strokeColor = {
            'sample': 'none',
            'reference': '#555',
            'gfp': 'green',
        };

        const fillColor = {
            'sample': 'gray',
            'reference': 'none',
            'gfp': 'lightgreen',
        };

        const xExtent = [0, 10000];
        const yExtent = [0, 600];

        const axes = [
            {
                orient: 'left',
                label: 'Frequency',
                tickValues: [0, 200, 400, 600,],
                tickFormat: val => val==700 ? '' : val.toFixed(0),
            },{
                orient: 'bottom',
                label: 'Intensity',
                tickValues: [0, 2000, 4000, 6000, 8000, 10000],
                tickFormat: val => val.toFixed(0),
            }
        ];

        // legend
        const foregroundGraphics = [(
            <text key={'gfp'} x={70} y={30} style={{fill: chroma('#a8d7a8').darken().saturate()}}>
                <tspan fontSize="14">{'● GFP-positive population'}</tspan>
            </text>
        ),(
            <text key={'curve'} x={70} y={50} style={{fill: '#666'}}>
                <tspan fontSize="14">{'— Estimated background'}</tspan>
            </text>
        )];

        const tightMargin = {left: 5, bottom: 5, right: 5, top: 5};
        const wideMargin = {left: 60, bottom: 60, right: 10, top: 10};

        // default hard-coded props for the XYFrame
        this.frameProps = {  
            
            // tight margin for sparkline mode
            margin: this.props.isSparkline ? tightMargin : wideMargin,

            xAccessor: "x",
            yAccessor: "y",
            yExtent,
            xExtent,

            lineType: 'area',
            lineStyle: (d, i) => {
                return {
                    strokeWidth: 1,
                    stroke: strokeColor[d.id],
                    fill: fillColor[d.id],
                    fillOpacity: .5,
                };
            },

            // no axes in sparkline mode
            axes: this.props.isSparkline ? [] : axes,

            foregroundGraphics: this.props.isSparkline ? null : foregroundGraphics,
        };

    }


    constructLineData (data) {

        if (!data || !data.x) return;

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
                // clamp values less than the (mean + std dev) of the negative control
                y: val > 2800 ? data.y_sample[ind] - data.y_ref_fitted[ind] : 0
            })),
        };
        
        // clamp negative values in the subtracted histogram to zero
        gfpLine.coordinates.forEach(coord => {
            coord.y = coord.y < 0 ? 0 : coord.y;
        });

        // line data to pass to XYFrame
        this.lines = {sample: sampleLine, ref: refLine, gfp: gfpLine};
    }


    fetchAndConstructData () {
        fetch(`${settings.apiUrl}/lines/${this.props.cellLineId}/facs`)
            .then(result => result.json())
            .then(data => {
                    this.constructLineData(data.histograms);
                    this.setState({loaded: true});
                },
                error => console.log(error)
            );
    }


    componentDidMount () {
        // only fetch the data if it was not passed as a prop
        if (this.props.data) {
            this.constructLineData(props.data);
            this.setState({loaded: true});
        } else if (this.props.cellLineId) {
            this.fetchAndConstructData();
        }
    }


    componentDidUpdate (prevProps) {
        // re-fetch the data only if it was not passed as a prop and if the cellLineId has changed
        if (this.props.cellLineId!==prevProps.cellLineId) {
            this.fetchAndConstructData();
        }
    }


    render () {

        if (!this.state.loaded) return null;
        
        // HACK: if constructLineData failed, we should not render the plot
        if (!this.lines) return null;

        // plot size (though only the height will be used by ResponsiveXYFrame)
        const height = this.props.height ? this.props.height : this.props.width * this.aspectRatio;
        const size = [this.props.width, height];
    
        const lines = [this.lines.sample, this.lines.ref];
        if (this.props.showGFP) lines.push(this.lines.gfp);

        return (
            <ResponsiveXYFrame 
                responsiveWidth={true} 
                lines={lines} 
                size={size}
                {...this.frameProps}/>
        );
    }
}


export default FACSPlot;