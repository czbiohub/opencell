import * as d3 from 'd3';
import React, { Component } from 'react';

import chroma from 'chroma-js';
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
        const yExtent = [0, 4];

        // GFP intensity
        const xExtent = [0, 2.5];

        const axes = [
            {
                orient: 'left',
                label: 'RNA abundance (log tpm)',
                tickValues: [0, 1, 2, 3, 4, ],
                tickFormat: val => val.toFixed(0),
            },{
                orient: 'bottom',
                label: 'Fluorescence intensity (log a.u.)',
                tickValues: [0, .5, 1, 1.5, 2, 2.5,],
                tickFormat: val => val.toFixed(1),
            }
        ];

        // legend
        const foregroundGraphics = [(
            <text key={'active'} x={70} y={30} style={{fill: chroma('#a8d7a8').darken().saturate()}}>
                <tspan fontSize="14">{'● Selected cell line'}</tspan>
            </text>
        ),(
            <text key={'all'} x={70} y={50} style={{fill: '#777'}}>
                <tspan fontSize="14">{'● All cell lines'}</tspan>
            </text>
        )];

        const margin = {left: 60, bottom: 60, right: 10, top: 10};

        // HACK: eliminate duplicates in the data
        // (these are the CLTA and BCAP controls)
        const clta = expressionData.filter(d => d.target_name==='CLTA');
        const bcap = expressionData.filter(d => d.target_name==='BCAP31');
        
        let data = expressionData.filter(d => !['CLTA', 'BCAP31'].includes(d.target_name));
        data.push(clta[0], bcap[0]);
        
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

            points: data,

            foregroundGraphics,

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
                fill: isActive ? '#a9d7a8' : '#66666633',

                stroke: isActive ? '#088104' : null,

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