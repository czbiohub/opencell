import * as d3 from 'd3';
import React, { Component } from 'react';

import XYFrame from "semiotic/lib/XYFrame";
import ResponsiveXYFrame from "semiotic/lib/ResponsiveXYFrame";

import expressionData from '../demo/data/20190819_expression-data.json';


class ExpressionPlot extends Component {
    //
    // A scatterplot of RNA-seq vs GFP intensity
    // 
    // 

    constructor (props) {
        super(props);

        this.aspectRatio = .7;

        // RNA-seq tpm
        const yExtent = [0, 10];

        // GFP intensity
        const xExtent = [0, 2.5];

        const axes = [
            {
                orient: 'left',
                label: 'Log expression (tpm)',
                tickValues: [0, 2, 4, 6, 8, 10,],
                tickFormat: val => val.toFixed(0),
            },{
                orient: 'bottom',
                label: 'Log GFP intensity',
                tickValues: [0, .5, 1, 1.5, 2, 2.5,],
                tickFormat: val => val.toFixed(1),
            }
        ];

        const margin = {left: 60, bottom: 60, right: 10, top: 10};

        // hard-coded constant XYFrame props
        this.frameProps = {  

            // note that the width here is ignored by ResponsiveXYFrame
            size: [400, 300],
            
            margin,
            xExtent,
            yExtent,
            axes,

            xAccessor: "gfp",
            yAccessor: "tpm",

            points: expressionData,

        };


    }

    componentDidMount () {
        this.bringActiveDotToFront();
    }

    componentDidUpdate (prevProps) {
        this.bringActiveDotToFront();
    }

    shouldComponentUpdate (nextProps) {
        // HACK: only update if the target has changed
        // (without this, scrolling through z-slices is laggy,
        // presumably because it takes react awhile to diff all 1700ish scatterplot dots)
        if (this.props.targetName===nextProps.targetName) return false;
        return true;
    }
    
    bringActiveDotToFront () {
        const dot = d3.select('g.expression-plot-dot-active').node();
        if (!dot || !dot.parentNode) return;
        dot.parentNode.appendChild(dot);
    }

    render () {

        const pointStyle = (d, i) => {
            const isActive = d.target_name===this.props.targetName;
            return {

                r: isActive ? 5 : 2,
        
                // current target in green
                fill: isActive ? '#a8d7a8' : '#66666633',

                stroke: isActive ? 'green' : null,

                // hide points with missing data
                visibility: (d.tpm && d.tpm > 0 && d.gfp && d.gfp > 0) ? 'visible' : 'hidden',
            };
        };

        const pointClass = (d, i) => {
            return d.target_name===this.props.targetName ? 'expression-plot-dot-active' : 'expression-plot-dot';
        };

        return (
            <ResponsiveXYFrame 
                responsiveWidth={true} 
                pointStyle={pointStyle} 
                pointClass={pointClass} 
                {...this.frameProps}/>
        );
    }
}


export default ExpressionPlot;