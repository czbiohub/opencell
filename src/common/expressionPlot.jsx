import * as d3 from 'd3';
import React, { Component } from 'react';

import chroma from 'chroma-js';
import XYFrame from "semiotic/lib/XYFrame";
import ResponsiveXYFrame from "semiotic/lib/ResponsiveXYFrame";


class ExpressionPlot extends Component {
    // A scatterplot of two measures of target expression: 
    // tpm from RNAseq and fluorescence intensity from FACS

    constructor (props) {

        super(props);
        
        // highlight the selected cell line's dot in blue
        this.selectedCellLineColor = '#01a1dd';

        // y-axis is tpm from RNA-seq
        const yExtent = [0, 4];

        // x-axis is the log of the FACS intensity in 488 (relative to the control)
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
            <text key={'active'} x={70} y={30} style={{fill: chroma(this.selectedCellLineColor).saturate()}}>
                <tspan fontSize="14">{'● Selected cell line'}</tspan>
            </text>
        ),(
            <text key={'all'} x={70} y={50} style={{fill: '#777'}}>
                <tspan fontSize="14">{'● All cell lines'}</tspan>
            </text>
        )];

        // hard-coded constant XYFrame props
        // note that the width here is ignored by ResponsiveXYFrame
        this.frameProps = {  
            size: [400, 250],
            margin: {left: 60, bottom: 60, right: 10, top: 10},
            xExtent,
            yExtent,
            axes,
            xAccessor: 'fluorescence',
            yAccessor: 'tpm',
            foregroundGraphics,
        };

        this.state = {loaded: false};
        this.constructData = this.constructData.bind(this);
    }


    componentDidMount () {
        this.constructData();
        this.bringActiveDotToFront();
    }


    componentDidUpdate (prevProps) {
        this.constructData();
        this.bringActiveDotToFront();
    }


    shouldComponentUpdate (nextProps) {
        // HACK: only update if the target has changed
        // (without this, scrolling through z-slices is laggy,
        // presumably because it takes react awhile to diff all 1700ish scatterplot dots)
        if (this.state.loaded && this.props.cellLineId===nextProps.cellLineId) return false;
        return true;
    }


    constructData () {
        let data = this.props.cellLines.map(line => {
            return {
                'cellLineId': line.metadata.cell_line_id,
                'targetName': line.metadata.target_name,

                // this the 'rel_median_log' intensity
                'fluorescence': line.scalars.facs_intensity,

                // tpm needs to be log'd
                'tpm': Math.log10(line.metadata.hek_tpm),
            };
        });

        // // HACK: eliminate obvious duplicates in the data
        // // (these are the CLTA and BCAP31 controls)
        // const clta = data.filter(d => d.targetName==='CLTA');
        // const bcap31 = data.filter(d => d.targetName==='BCAP31');
        // data = data.filter(d => !['CLTA', 'BCAP31'].includes(d.targetName));
        // data.push(clta[0], bcap31[0]);

        this.points = data;
        this.setState({loaded: true});
    }

    
    bringActiveDotToFront () {
        const dot = d3.select('g.expression-plot-dot-active').node();
        if (!dot || !dot.parentNode) return;
        dot.parentNode.appendChild(dot);
    }


    render () {

        const pointStyle = (d, i) => {
            const isActive = d.cellLineId===this.props.cellLineId;
            return {
                r: isActive ? 5 : 2,
                fill: isActive ? chroma(this.selectedCellLineColor).alpha(.7) : '#66666633',
                stroke: isActive ? chroma(this.selectedCellLineColor).darken() : null,
                // hide points with missing data
                visibility: (d.tpm && d.tpm > 0 && d.fluorescence && d.fluorescence > 0) ? 'visible' : 'hidden',
            };
        };

        const pointClass = (d, i) => {
            return (
                d.cellLineId===this.props.cellLineId ? 
                'expression-plot-dot-active' : 'expression-plot-dot'
            );
        };

        return (
            <ResponsiveXYFrame 
                responsiveWidth={true} 
                pointStyle={pointStyle} 
                pointClass={pointClass} 
                points={this.points}
                {...this.frameProps}
            />
        );
    }
}


export default ExpressionPlot;