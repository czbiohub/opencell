
import * as d3 from 'd3';
import tip from 'd3-tip';
import React, { Component } from 'react';

import 'tachyons';
import './Demo.css';

import msData from './data/ms_data.json';
import msMetadata from './data/ms_metadata.json';


// wrapper around a d3-based interactive scatterplot

class ScatterPlot extends Component {

    constructor (props) {

        super(props);
        this.state = {};

        this.plotProps = {
            width: 500,
            height: 400,
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
        this.constructData = this.constructData.bind(this);

        // list of gene/target names with an MS dataset
        this.genesWithData = msData.map(d => d.target_name);

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
        let data = msData.filter(d => d.target_name==this.props.targetName)[0].hits;
        data = data.filter(d => {
            return (d.pvalue > 1) || (d.pvalue < 1 && d3.randomUniform(0, 1)() > .5);
        }).filter(d => d.pvalue > .5);
        return data;
    }


    createScatterPlot () {
        
        const pp = this.plotProps;
        const svg = d3.select(this.node)
                      .append('svg')
                      .attr('width', pp.width)
                      .attr('height', pp.height);

        this.xScale = d3.scaleLinear().range([pp.padLeft, pp.width - pp.padRight]);
        this.yScale = d3.scaleLinear().range([pp.height - pp.padBottom, pp.padTop]);

        this.captionOpacityScale = d3.scaleLinear()
                                .range([0, 1])
                                .domain([2.5, 4.5])
                                .clamp(true);

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

    }



    updateScatterPlot () {

        const calcDotRadius = d => {
            // scatter plot dot size from pvalue and enrichment values

            const minRadius = 2;
            const width = 15;
            const minDist = 2;

            // any hit with negative enrichment is necessarily not significant
            if (this.props.xAccessor(d) < 0) return minRadius;

            // distance from the origin in the log(pvalue) vs enrichment space
            // as a measure of overall 'significance'
            let dist = (this.props.yAccessor(d)**2 + this.props.xAccessor(d)**2)**.5;
            if (dist < minDist) return minRadius;
            const weight = (1 - Math.exp(-((dist - minDist)**2 / width)));
            return (plotProps.dotRadius - minRadius) * weight + minRadius;
        }


        const calcDotColor = d => {
            // color dots that correspond to significant hits  
            return '#333';
        }


        const calcDotStroke = d => {
            // outline the dot if we have data for it
            if (this.genesWithData.includes(msMetadata[d.gene_id].gene_name)) {
                return '#111';
            }
            return 'none';
        }



        const tip = this.tip;
        const plotProps = this.plotProps;

        this.xScale.domain(this.props.xDomain);
        this.yScale.domain(this.props.yDomain);

        let xScale = this.xScale;
        let yScale = this.yScale;
        if (this.currentTransform) {
            xScale = this.currentTransform.rescaleX(xScale);
            yScale = this.currentTransform.rescaleY(yScale);
        }

        const dots = this.g.selectAll('.scatter-dot')
                           .data(this.data, d => d.gene_id);
        
        dots.exit().remove();
    
        dots.enter().append('circle')
            .attr('class', 'scatter-dot')
            .attr('fill-opacity', d => {
                // data-independent opacity for now
                return plotProps.dotAlpha;
            })
            .merge(dots)
            .attr('r', calcDotRadius)
            .attr('fill', calcDotColor)
            .attr('stroke', calcDotStroke)
            .attr('cx', d => xScale(this.props.xAccessor(d)))
            .attr('cy', d => yScale(this.props.yAccessor(d)))
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
                .attr('x', d => xScale(this.props.xAccessor(d)))
                .attr('y', d => yScale(this.props.yAccessor(d)) - 10)
                .attr('fill-opacity', d => {
                    return this.currentTransform ? this.captionOpacityScale(this.currentTransform.k) : 0
                });


        this.svg.select("#x-axis").call(this.xAxis.scale(xScale));
        this.svg.select("#y-axis").call(this.yAxis.scale(yScale));

        this.svg.select("#x-axis-label").text('Enrichment');
        this.svg.select("#y-axis-label").text('-log p-value');

    }


    zoom () {

        const transform = d3.event.transform;
        const xScaleZoom = transform.rescaleX(this.xScale);
        const yScaleZoom = transform.rescaleY(this.yScale);

        this.g.selectAll(".scatter-dot")
            .attr("cx", d => xScaleZoom(this.props.xAccessor(d)))
            .attr("cy", d => yScaleZoom(this.props.yAccessor(d)));

        this.g.selectAll(".scatter-caption")
            .attr("x", d => xScaleZoom(this.props.xAccessor(d)))
            .attr("y", d => yScaleZoom(this.props.yAccessor(d)) - 10)
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

export default ScatterPlot;