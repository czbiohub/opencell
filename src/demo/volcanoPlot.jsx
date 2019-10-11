
import * as d3 from 'd3';
import tip from 'd3-tip';
import React, { Component } from 'react';
import ReactDOM from 'react-dom';
import chroma from 'chroma-js';

import 'tachyons';
import './Demo.css';

import msData from './data/20190816_ms-data.json';
import msMetadata from './data/20191009_ms-metadata.json';


export default class VolcanoPlot extends Component {

    // A volcano plot of mass-spec enrichment data
    // The x-axis is enrichment and the y-axis is -log pvalue
    //

    constructor (props) {

        super(props);
        this.state = {};

        this.plotProps = {

            // these hard-coded width/height are overridden in createScatterPlot
            width: 500,
            height: 400,
            aspectRatio: 1,

            // note that these pad values are independent of the actual width
            padLeft: 40,
            padRight: 10,
            padTop: 10,
            padBottom: 40,

            numTicks: 3,
            dotAlpha: .3,
            dotRadius: 5,
            xAxisLabelOffset: 5,
            yAxisLabelOffset: 15,
        };

        this.sigModeDotColors = {
            bait: '#a8d7a8',
            sigHit: '#ff6666',
            notSigHit: '#33333333',
        };

        this.sigModeLegendItems = [
            {
                color: chroma(this.sigModeDotColors.bait).darken().saturate(),
                text: '● Selected protein',
            },{
               color: chroma(this.sigModeDotColors.sigHit).alpha(1),
               text: '● Significant hits',
            },{
               color: chroma(this.sigModeDotColors.notSigHit).alpha(.5),
               text: '● Non-significant hits',
            },{
               color: chroma(this.sigModeDotColors.notSigHit).alpha(1),
               text: '- - -  5% FDR curve',
            }
        ];

        this.functionModeDotColors = [
            {
                annotation: 'Intracellular transport',
                color: '#0096E7', //blue //'#9be0ee', // cyan
            },{
                annotation: 'RNA processing and stability',
                color: '#fa9523', // orange
                text: 'RNA processing',
            },{
                annotation: 'mRNA decay',
                color: '#8c7dd8', // purple
            },{
                annotation: 'Ubiquitination',
                color: '#af8852', // brown
            },{
                annotation: 'Other',
                color: this.sigModeDotColors.sigHit, 
                text: 'Other significant hits'
            },
        ];

        this.functionModeLegendItems = this.functionModeDotColors.map(d => {
            d.text = `● ${d.text || d.annotation}`;
            return d;
        });

        this.functionModeLegendItems = [
            this.sigModeLegendItems[0], ...this.functionModeLegendItems, this.sigModeLegendItems[2],
        ];

        this.onZoom = this.onZoom.bind(this);
        this.resetZoom = this.resetZoom.bind(this);
        this.hitIsSignificant = this.hitIsSignificant.bind(this);
        this.captionOpacity = this.captionOpacity.bind(this);
        this.constructData = this.constructData.bind(this);
        this.updateLegend = this.updateLegend.bind(this);
        this.updateScatterPlot = this.updateScatterPlot.bind(this);

        // list of gene/target names with an MS dataset
        this.genesWithData = msData.map(d => d.target_name);

        // parameters for 1% FDR from Hein 2015
        // this.fdrParams = {
        //     x0: 1.75,
        //     c: 3.65,
        // };

        // parameters for 5% FDR calculated from 2019-08-02 data
        this.fdrParams = {
            x0: 1.62,
            c: 4.25,
        };

        this.fdrDataLeft = d3.range(-20, -this.fdrParams.x0, .1).map(enrichment => {
            return {x: enrichment, y: this.fdrParams.c / (-enrichment - this.fdrParams.x0)};
        });
        
        this.fdrDataRight = d3.range(this.fdrParams.x0 + .1, 20, .1).map(enrichment => {
            return {x: enrichment, y: this.fdrParams.c / (enrichment - this.fdrParams.x0)};
        });

        // transform when zoomed/panned
        this.currentTransform = undefined;


    }

    
    componentDidMount() {

        // HACK: create the data (hits) to plot by dropping low-significance hits
        // for now, this is necessary to keep pan/zoom from lagging

        this.data = this.constructData();
        this.createScatterPlot();
        this.updateScatterPlot();
    }


    componentDidUpdate(prevProps) {
        // TODO check that we really need to update

        if (prevProps.targetName!==this.props.targetName) {
            this.data = this.constructData();
            this.resetZoom();
        }

        if (prevProps.resetZoom!==this.props.resetZoom) {
            this.resetZoom();
        }
    
        this.updateScatterPlot();
    }


    resetZoom () {
        // reset the pan/zoom transform
        this.currentTransform = undefined;
        this.svg.call(this.zoom.transform, d3.zoomIdentity);
    }


    constructData() {
        // to speed up the rendering of the plot,
        // we drop all hits with a pvalue less than 0.5 
        // and randomly drop hits with a pvalue between 0.5 and 1
        let data = msData.filter(d => d.target_name==this.props.targetName)[0].hits;
        data = data.filter(d => {
            return (d.pvalue > 1) || (d.pvalue < 1 && d3.randomUniform(0, 1)() > .5);
        }).filter(d => d.pvalue > .5);
        return data;
    }

    hitIsSignificant (d) {

        // negatively-enriched hits are (definitionally) not significant
        if (this.props.enrichmentAccessor(d) < this.fdrParams.x0) return false;

        // check if the positive enrichment is above the FDR curve
        const thresh = this.fdrParams.c / (this.props.enrichmentAccessor(d) - this.fdrParams.x0);
        if (this.props.pvalueAccessor(d) > thresh) return true;
        return false;
    }


    createScatterPlot () {

        const pp = this.plotProps;

        // override manuallly defined widths
        pp.width = ReactDOM.findDOMNode(this.node).offsetWidth;
        pp.height = pp.width * pp.aspectRatio;
        
        const svg = d3.select(this.node)
                      .append('svg')
                      .attr('width', pp.width)
                      .attr('height', pp.height);

        this.xScale = d3.scaleLinear().range([pp.padLeft, pp.width - pp.padRight]);
        this.yScale = d3.scaleLinear().range([pp.height - pp.padBottom, pp.padTop]);

        this.captionOpacityScale = k => {
            const val = d3.scaleLinear()
                        .range([0, 1])
                        .domain([2.5, 4.5])
                        .clamp(true)(k);
            return val**2;
        };


        this.xAxis = d3.axisBottom(this.xScale)
            .tickSize(-pp.height + pp.padTop + pp.padBottom, 0)
            .ticks(pp.numTicks);

        this.yAxis = d3.axisLeft(this.yScale)
            .tickSize(-pp.width + pp.padLeft + pp.padRight, 0)
            .ticks(pp.numTicks);  

        // y axis container
        svg.append("g")
            .attr("class", "axis")
            .attr("id", "y-axis")
            .attr("transform", `translate(${pp.padLeft}, 0)`);

        // x-axis container
        svg.append("g")
            .attr("class", "axis")
            .attr("id", "x-axis")
            .attr("transform", `translate(0, ${pp.height - pp.padBottom})`);

        // x-axis label
        svg.append("text")
            .attr("class", "axis-label")
            .attr("id", "x-axis-label")
            .attr("text-anchor", "middle")
            .attr("x", pp.width/2)
            .attr("y", pp.height - pp.xAxisLabelOffset);

        // y-axis label
        svg.append("text")
            .attr("class", "axis-label")
            .attr("id", "y-axis-label")
            .attr("text-anchor", "middle")
            .attr("x", -pp.height/2)
            .attr("y", pp.yAxisLabelOffset)
            .attr("transform", "rotate(-90)");

        // scatter dot container
        const g = svg.append("g").attr("class", "dot-g")
                .attr("clip-path", `url(#clip)`);

        // clipPath to mask dots outside of the axes (needed for zooming)
        g.append("clipPath")
            .attr("id", `clip`)
            .append("rect")
            .attr("x", pp.padLeft)
            .attr("y", pp.padTop)
            .attr("width", pp.width - pp.padLeft - pp.padRight)
            .attr("height", pp.height - pp.padTop - pp.padBottom);

        // legend container
        const legend = svg.append('g')
            .attr('id', 'volcano-plot-legend')
            .attr('transform', `translate(0, 0)`)
            .style('fill', '#ffffff55');
        
     
        this.tip = tip()
                .offset([-10, 0])
                .attr("class", "d3-tip")
                .html(d => `<strong>${d.gene_name}</strong><br>${d.protein_names}`);
        svg.call(this.tip);

        this.zoom = d3.zoom().on('zoom', this.onZoom);
        svg.call(this.zoom);

        this.svg = svg;
        this.g = g;

        this.fdrLineLeft = g.append("path")
                            .attr('class', 'volcano-fdr-line')
                            .datum(this.fdrDataLeft);

        this.fdrLineRight = g.append("path")
                             .attr('class', 'volcano-fdr-line')
                             .datum(this.fdrDataRight);

    }


    updateLegend () {

        // legend
        const legend = this.svg.select('#volcano-plot-legend');

        legend.selectAll("text").remove();
        legend.selectAll("rect").remove();
 
        let legendItems;
        if (this.props.labelColor==='Significance') {
            legendItems = this.sigModeLegendItems;
        }

        if (this.props.labelColor==='Function') {
            legendItems = this.functionModeLegendItems;
        }

        const padLeft = 30
        const padTop = 30
        const verticalSpace = 25

        legend.append('rect')
            .attr('width', 250)
            .attr('height', padTop + legendItems.length * verticalSpace)
            .style('fill', 'white')
            .style('fill-opacity', .9);

        legendItems.map((d, ind) => {
            legend.append('text')
                  .attr('class', 'volcano-plot-legend')
                  .attr('x', padLeft)
                  .attr('y', padTop + verticalSpace * ind)
                  .style('fill', d.color)
                  .text(d.text);
        });

    }


    updateScatterPlot () {

        const calcDotRadius = d => {
            // scatter plot dot size from pvalue and enrichment values

            const minRadius = 2;
            const width = 15;
            const minDist = 2;

            // any hit with negative enrichment is necessarily not significant
            if (this.props.enrichmentAccessor(d) < this.fdrParams.x0) return minRadius;

            // distance from the origin in the log(pvalue) vs enrichment space
            // as a measure of overall 'significance'
            let dist = (this.props.pvalueAccessor(d)**2 + this.props.enrichmentAccessor(d)**2)**.5;
            const weight = (1 - Math.exp(-((dist - minDist)**2 / width)));

            if (dist < minDist) return minRadius;
            return (plotProps.dotRadius - minRadius) * weight + minRadius;
        }


        const calcDotColor = d => {


            let color;

            // special color if the hit is the target (i.e., the bait) itself
            if (msMetadata[d.gene_id].gene_name===this.props.targetName) return this.sigModeDotColors.bait;
            
            // if not sig, always the same color
            if (!this.hitIsSignificant(d)) return this.sigModeDotColors.notSigHit;

            // if we're still here and coloring by significance only
            if (this.props.labelColor==='Significance') {
                return chroma(this.sigModeDotColors.sigHit).alpha(.5);
            }
            
            // if we're still here and coloring by annotation (what the UI calls 'function')
            if (this.props.labelColor==='Function') {
                let ant = msMetadata[d.gene_id].annotation || 'Other';
                const color = this.functionModeDotColors.filter(d => d.annotation===ant)[0].color;
                return chroma(color).alpha(.5);
            }

        }


        const calcDotStroke = d => {

            if (!this.hitIsSignificant(d)) return 'none';

            // stroke in black we have data for it
            if (this.genesWithData.includes(msMetadata[d.gene_id].gene_name)) {
                return '#666';
            }

            return chroma(calcDotColor(d)).darken(1);

        }

        const tip = this.tip;
        const plotProps = this.plotProps;

        // dynamically determine the domain of the plot
        const maxEnrichment = d3.max(this.data, this.props.enrichmentAccessor);
        const maxPvalue = d3.max(this.data, this.props.pvalueAccessor);

        this.xScale.domain([-maxEnrichment - 1, maxEnrichment + 1]);
        this.yScale.domain([0, maxPvalue + 1]);

        let xScale = this.xScale;
        let yScale = this.yScale;

        // retain the zoom/pan state when the target is changed
        if (this.currentTransform) {
            xScale = this.currentTransform.rescaleX(xScale);
            yScale = this.currentTransform.rescaleY(yScale);
        }

        // create the generator the significance curves
        const line = d3.line()
                       .x(d => xScale(d.x))
                       .y(d => yScale(d.y));
    
        // update the line generator
        this.fdrLineLeft.attr('d', line);
        this.fdrLineRight.attr('d', line);

        const dots = this.g.selectAll('.scatter-dot')
                           .data(this.data, d => d.gene_id);
        
        dots.exit().remove();
    
        dots.enter().append('circle')
            .attr('class', 'scatter-dot')
            .merge(dots)
            .attr('r', calcDotRadius)
            .attr('fill', calcDotColor)
            .attr('stroke', calcDotStroke)
            .attr('cx', d => xScale(this.props.enrichmentAccessor(d)))
            .attr('cy', d => yScale(this.props.pvalueAccessor(d)))
            .on("mouseover", function (d) {
                // enlarge and outline the dots on hover
                d3.select(this)
                  .attr("r", plotProps.dotRadius + 2)
                  .attr("stroke", '#111')
                  .classed("scatter-dot-hover", true);
                tip.show(msMetadata[d.gene_id], this); 
             })
             .on("mouseout", function (d) {
                d3.select(this)
                  .attr("r", calcDotRadius)
                  .attr("stroke", calcDotStroke)
                  .classed("scatter-dot-hover", false);
                tip.hide(msMetadata[d.gene_id], this);
             })
            .on('click', d => this.props.changeTarget(msMetadata[d.gene_id].gene_name));

        // bind data - filter for only significant hits
        const captions = this.g.selectAll('.scatter-caption')
                               .data(this.data.filter(this.hitIsSignificant), d => d.gene_id);
            
        captions.exit().remove();

        captions.enter().append('text')
                .attr('class', 'scatter-caption')
                .attr('text-anchor', 'middle')
                .text(d => msMetadata[d.gene_id].gene_name)
                .merge(captions)
                .attr('x', d => xScale(this.props.enrichmentAccessor(d)))
                .attr('y', d => yScale(this.props.pvalueAccessor(d)) - 10)
                .attr('fill-opacity', this.captionOpacity);

        this.svg.select("#x-axis").call(this.xAxis.scale(xScale));
        this.svg.select("#y-axis").call(this.yAxis.scale(yScale));

        this.svg.select("#x-axis-label").text('Relative enrichment');
        this.svg.select("#y-axis-label").text('-log10 p-value');

        this.updateLegend();

    }


    captionOpacity () {
        let opacity;
        if (this.props.showLabels==='Always') {
            opacity = 1;
        } else if (this.props.showLabels==='Never') {
            opacity = 0;
        } else {
            opacity = this.currentTransform ? this.captionOpacityScale(this.currentTransform.k) : 0;
        }
        return opacity;
    }


    onZoom () {

        const transform = d3.event.transform;
        this.currentTransform = transform;

        const xScaleZoom = transform.rescaleX(this.xScale);
        const yScaleZoom = transform.rescaleY(this.yScale);

        const line = d3.line()
            .x(d => xScaleZoom(d.x))
            .y(d => yScaleZoom(d.y));

        // update the line generator
        this.fdrLineLeft.attr('d', line);
        this.fdrLineRight.attr('d', line);
       
        this.g.selectAll(".scatter-dot")
            .attr("cx", d => xScaleZoom(this.props.enrichmentAccessor(d)))
            .attr("cy", d => yScaleZoom(this.props.pvalueAccessor(d)));

        this.g.selectAll(".scatter-caption")
            .attr("x", d => xScaleZoom(this.props.enrichmentAccessor(d)))
            .attr("y", d => yScaleZoom(this.props.pvalueAccessor(d)) - 10)
            .attr("fill-opacity", this.captionOpacity);

        this.svg.select("#x-axis").call(this.xAxis.scale(xScaleZoom));
        this.svg.select("#y-axis").call(this.yAxis.scale(yScaleZoom));

    }


    render() {
        return (
            <div ref={node => this.node = node}/>
        );
    }

}

