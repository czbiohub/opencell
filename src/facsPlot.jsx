import * as d3 from 'd3';
import React, { Component } from 'react';

import XYFrame from "semiotic/lib/XYFrame"


class FACSPlot extends Component {

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

        // default hard-coded props for the XYFrame
        this.frameProps = {  
            
            // line data is constructed in constructLineData
            lines: [],
            
            margin: { left: 5, bottom: 5, right: 5, top: 5 },

            xAccessor: "x",
            yAccessor: "y",
            yExtent: [0, 7e-4 * 1e6],
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
        this.frameProps.lines = [sampleLine, refLine, gfpLine];
        
        // plot size
        this.frameProps.size = [this.props.width, this.props.width * this.aspectRatio];

    }


    fetchData () {

        fetch(`http://localhost:5000/facshistograms/${this.props.cellLineId}`)
            .then(result => result.json())
            .then(
                data => {
                    this.fetchedData = fetchedData;
                    this.setState({loaded: true});
                },
                error => console.log(error)
            );
    }


    componentDidMount () {

        // only fetch the data if it was not passed as a prop
        if (this.props.data) {
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
    }


    render () {

        if (!this.state.loaded) return null;
        
        // construct the line data object expected by XYFrame 
        // (from either this.props.data or this.fetchedData)
        this.constructLineData();

        // HACK: if constructLineData failed, we should not render the plot
        if (!this.frameProps.lines.length) return null;

        return (
            <XYFrame lines={this.frameProps.lines} {...this.frameProps}/>
        );
    }
}


export default FACSPlot;