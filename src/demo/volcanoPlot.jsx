
import * as d3 from 'd3';
import tip from 'd3-tip';
import React, { Component } from 'react';
import ReactDOM from 'react-dom';

import 'tachyons';
import './Demo.css';

import msData from './data/20190816_ms-data.json';
import msMetadata from './data/20190816_ms-metadata.json';


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
        }

        this.zoom = this.zoom.bind(this);
        this.updateScatterPlot = this.updateScatterPlot.bind(this);
        this.constructData = this.constructData.bind(this);

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
        }
    
        this.updateScatterPlot();
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

        this.tip = tip()
                .offset([-10, 0])
                .attr("class", "d3-tip")
                .html(d => `<strong>${d.gene_name}</strong><br>${d.protein_names}`);
        
        svg.call(d3.zoom().on('zoom', this.zoom));
        svg.call(this.tip);

        this.svg = svg;
        this.g = g;

        this.fdrLineLeft = g.append("path")
                            .attr('class', 'volcano-fdr-line')
                            .datum(this.fdrDataLeft);

        this.fdrLineRight = g.append("path")
                             .attr('class', 'volcano-fdr-line')
                             .datum(this.fdrDataRight);

    }



    updateScatterPlot () {

        // reset the transform
        this.currentTransform = undefined;

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
            // color dots that correspond to significant hits  

            const baitColor = '#a8d7a8'; //'#ffff33ff';
            const sigColor = '#ff666677';
            const notSigColor = '#33333333';
    
            // special color if the hit is the target itself
            if (msMetadata[d.gene_id].gene_name===this.props.targetName) return baitColor;

            // negatively-enriched hits are (definitionally) not significant
            if (this.props.enrichmentAccessor(d) < this.fdrParams.x0) return notSigColor;

            // check if the positive enrichment is above the FDR curve
            const thresh = this.fdrParams.c / (this.props.enrichmentAccessor(d) - this.fdrParams.x0);
            if (this.props.pvalueAccessor(d) > thresh) return sigColor;

            return notSigColor;
        }


        const calcDotStroke = d => {
            // outline the dot if we have data for it
            if (this.genesWithData.includes(msMetadata[d.gene_id].gene_name)) {
                return '#666';
            }
            return 'none';
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

        // to retain the zoom/pan state when the target is changed
        // if (this.currentTransform) {
        //     xScale = this.currentTransform.rescaleX(xScale);
        //     yScale = this.currentTransform.rescaleY(yScale);
        // }

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


        const captions = this.g.selectAll('.scatter-caption')
                               .data(this.data, d => d.gene_id);
            
        captions.exit().remove();

        captions.enter().append('text')
                .attr('class', 'scatter-caption')
                .attr('text-anchor', 'middle')
                .text(d => msMetadata[d.gene_id].gene_name)
                .merge(captions)
                .attr('x', d => xScale(this.props.enrichmentAccessor(d)))
                .attr('y', d => yScale(this.props.pvalueAccessor(d)) - 10)
                .attr('fill-opacity', d => {
                    return this.currentTransform ? this.captionOpacityScale(this.currentTransform.k) : 0
                });


        this.svg.select("#x-axis").call(this.xAxis.scale(xScale));
        this.svg.select("#y-axis").call(this.yAxis.scale(yScale));

        this.svg.select("#x-axis-label").text('Relative enrichment');
        this.svg.select("#y-axis-label").text('-log10 p-value');

    }


    zoom () {

        const transform = d3.event.transform;
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
            .attr("fill-opacity", d => transform ? this.captionOpacityScale(transform.k) : 0);

        this.svg.select("#x-axis").call(this.xAxis.scale(xScaleZoom));
        this.svg.select("#y-axis").call(this.yAxis.scale(yScaleZoom));

        this.currentTransform = transform;
    }


    render() {
        return (
            <div ref={node => this.node = node}/>
        );
    }

}

