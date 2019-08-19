import * as d3 from 'd3';
import React, { Component } from 'react';

import XYFrame from "semiotic/lib/XYFrame"
import ResponsiveXYFrame from "semiotic/lib/ResponsiveXYFrame"


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
            'reference': '#666',
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

        const tightMargin = {left: 5, bottom: 5, right: 5, top: 5};
        const wideMargin = {left: 60, bottom: 60, right: 10, top: 10};

        // default hard-coded props for the XYFrame
        this.frameProps = {  
            
            // line data is constructed in constructLineData
            lines: [],
            
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
        };
    }

    constructLineData () {

        // figure out where the data has come from (either via props or from fetchData)
        const data = this.props.data ? this.props.data : this.fetchedData;

        if (!data || !data.x) {
            this.frameProps.lines = [];
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
        this.frameProps.lines = [sampleLine, refLine];
        if (this.props.showGFP) this.frameProps.lines.push(gfpLine);
        
        // plot size
        const height = this.props.height ? this.props.height : this.props.width * this.aspectRatio;
        this.frameProps.size = [this.props.width, height];

    }


    fetchData () {

        fetch(`http://localhost:5000/facshistograms/${this.props.cellLineId}`)
            .then(result => result.json())
            .then(
                data => {
                    this.fetchedData = fetchedData;
                    this.constructLineData();
                    this.setState({loaded: true});
                },
                error => console.log(error)
            );
    }


    componentDidMount () {

        // only fetch the data if it was not passed as a prop
        if (this.props.data) {
            this.constructLineData();
            this.setState({loaded: true});
        } else {
            this.fetchData();
        }
    }


    componentDidUpdate(prevProps) {

        // re-fetch the data only if it was not passed as a prop and if the cellLineId has changed
        if (this.props.cellLineId !== prevProps.cellLineId) {
            this.fetchData();
        }

        // construct the line data only if the target has changed
        if (this.props.targetName!==prevProps.targetName) this.constructLineData();
    }


    render () {

        if (!this.state.loaded) return null;
        
        // HACK: if constructLineData failed, we should not render the plot
        if (!this.frameProps.lines.length) return null;

        return (
            <ResponsiveXYFrame responsiveWidth={true} lines={this.frameProps.lines} {...this.frameProps}/>
        );
    }
}


export default FACSPlot;