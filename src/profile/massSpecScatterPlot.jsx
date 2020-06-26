
import * as d3 from 'd3';
import tip from 'd3-tip';
import React, { Component } from 'react';
import ReactDOM from 'react-dom';
import chroma from 'chroma-js';

import 'tachyons';
import './Profile.css';

import settings from '../common/settings.js';


export default class MassSpecScatterPlot extends Component {

    constructor (props) {
        super(props);

        this.state = {
            loaded: false,
        };
        
        // the list of mass spec hits populated in constructData from the pulldown/ endpoint
        this.hits = [];

        this.plotProps = {
            aspectRatio: .8,
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
            bait: '#01a1dd', // blue
            sigHit: '#ff6666',
            notSigHit: '#aaa',
        };

        this.pvalueAccessor = d => parseFloat(d.pval);
        this.enrichmentAccessor = d => parseFloat(d.enrichment);
        this.abundanceStoichAccessor = d => parseFloat(d.abundance_stoich);
        this.interactionStoichAccessor = d => parseFloat(d.interaction_stoich);
        
        this.onZoom = this.onZoom.bind(this);
        this.resetZoom = this.resetZoom.bind(this);
        this.hitIsSignificant = this.hitIsSignificant.bind(this);
        this.captionOpacity = this.captionOpacity.bind(this);
        this.constructData = this.constructData.bind(this);
        this.updateScatterPlot = this.updateScatterPlot.bind(this);

        // parameters for 5% FDR calculated from 2019-08-02 data
        this.fdrParams = {x0: 1.62, c: 4.25};

        this.fdrDataLeft = d3.range(-20, -this.fdrParams.x0, .1).map(enrichment => {
            return {x: enrichment, y: this.fdrParams.c / (-enrichment - this.fdrParams.x0)};
        });
        
        this.fdrDataRight = d3.range(this.fdrParams.x0 + .1, 20, .1).map(enrichment => {
            return {x: enrichment, y: this.fdrParams.c / (enrichment - this.fdrParams.x0)};
        });

        // define a circular region of the interaction scatterplot
        // that corresponds to 'core complex' interactors
        const dx = 0.01;
        const radius = 1;
        const offset = -0.3;
    
        // top and bottom halves of a circular region
        const topArc = d3.range(-radius + offset, radius + offset + dx, dx).map(x => {
            return {x, y: Math.sqrt(radius**2 - (x - offset)**2)}
        });

        const bottomArc = topArc.map(({x, y}) => ({x, y: -y}));
        bottomArc.reverse();

        // the full circular region
        this.coreComplexRegionData = [...topArc, ...bottomArc];

        // transform when zoomed/panned
        this.zoomTransform = undefined;

        this.calcDotColor = d => {

            // special color if the hit is the target (i.e., the bait) itself
            if (d.is_bait) return chroma(this.sigModeDotColors.bait).alpha(.7);
            
            // if not sig, always the same color
            if (!this.hitIsSignificant(d)) return chroma(this.sigModeDotColors.notSigHit).alpha(.7);

            // if we're still here and coloring by significance only
            if (this.props.colorMode==='Significance') {
                return chroma(this.sigModeDotColors.sigHit).alpha(.6);
            }
            
            // if we're still here and coloring by annotation (what the UI calls 'function')
            if (this.props.colorMode==='Function') {
                let ant = 'Other'; 
                const color = this.functionModeDotColors.filter(d => d.annotation===ant)[0].color;
                return chroma(color).alpha(.6);
            }
        }

        this.calcDotStroke = d => {
            if (!this.hitIsSignificant(d)) return 'none';

            // stroke in black we have data for it
            if (d.opencell_target_names?.length) return '#333';

            return chroma(this.calcDotColor(d)).darken(1);
        }
    
        this.calcDotRadius = d => {
        
            // constant dot size in stoichoimetry mode
            if (this.props.mode==='Stoichiometry') return this.plotProps.dotRadius;

            // make dot size depend on pvalue and enrichment in volcano mode;
            const minRadius = 2;
            const width = 15;
            const minDist = 2;

            // any hit with negative enrichment is necessarily not significant
            if (this.enrichmentAccessor(d) < this.fdrParams.x0) return minRadius;

            // distance from the origin in the log(pvalue) vs enrichment space
            // as a measure of overall 'significance'
            let dist = (this.pvalueAccessor(d)**2 + this.enrichmentAccessor(d)**2)**.5;
            const weight = (1 - Math.exp(-((dist - minDist)**2 / width)));

            if (dist < minDist) return minRadius;
            return (this.plotProps.dotRadius - minRadius) * weight + minRadius;
        }

    
        this.captionOpacityScale = k => {
            const val = d3.scaleLinear()
                .range([0, 1])
                .domain([2.5, 4.5])
                .clamp(true)(k);
            return val**2;
        }
    }


    componentDidMount() {
        this.createScatterPlot();
        if (this.props.cellLineId) {
            this.constructData();
            this.updateScatterPlot();
        }
    }


    componentDidUpdate (prevProps) {
        if (prevProps.cellLineId!==this.props.cellLineId) {
            this.constructData();
            this.resetZoom();
        }
        if (prevProps.resetZoom!==this.props.resetZoom) this.resetZoom();
        if (prevProps.mode!==this.props.mode) this.resetZoom();
        this.updateScatterPlot();
    }


    resetZoom () {
        // reset the pan/zoom transform
        this.zoomTransform = undefined;
        this.svg.call(this.zoom.transform, d3.zoomIdentity);
    }


    constructData () {
        // fetch the pulldown metadata and the hits from the backend

        this.setState({loaded: false});
        const url = `${settings.apiUrl}/lines/${this.props.cellLineId}/pulldown`;
        d3.json(url).then(data => {
            let hits = data.hits;

            // to speed up the rendering of the plot, we drop all hits with a pvalue less than 0.5,
            // and randomly drop hits with a pvalue between 0.5 and 1
            hits = hits.filter(d => d.pval > .5);
            hits = hits.filter(d => {
                return (d.pval > 1) || (d.pval < 1 && d3.randomUniform(0, 1)() > .5);
            });

            // construct a label from the gene names 
            // (there is one gene name for each ensg_id)
            hits.forEach(hit => hit.label = hit.uniprot_gene_names?.sort().join(', '));

            this.hits = hits;
            this.pulldownMetadata = data.metadata;
            this.setState({loaded: true});
        },
        error => {
            console.log(error);
            this.hits = [];
            this.pullDownMetadata = null;
            this.setState({loaded: true});
        });
    }


    hitIsSignificant (d) {
        
        return d.is_significant_hit;
    
        // negatively-enriched hits are (by definition) not significant
        if (this.enrichmentAccessor(d) < this.fdrParams.x0) return false;

        // check if the positive enrichment is above the FDR curve
        const thresh = this.fdrParams.c / (this.enrichmentAccessor(d) - this.fdrParams.x0);
        if (this.pvalueAccessor(d) > thresh) return true;
        return false;
    }


    updatePlotSettings () {

        if (this.props.mode==='Volcano') {
            this.xAxisAccessor = this.enrichmentAccessor;
            this.yAxisAccessor = this.pvalueAccessor;

            this.minX = hits => -d3.max(hits, this.xAxisAccessor) - 1;
            this.maxX = hits => d3.max(hits, this.xAxisAccessor) + 1;
            this.minY = hits => 0;
            this.maxY = hits => d3.max(hits, this.yAxisAccessor) + 1;

            this.xAxisLabel = 'Relative enrichment';
            this.yAxisLabel = 'p-value (-log10)';
        }

        if (this.props.mode==='Stoichiometry') {
            const log10 = value => value ? Math.log10(value) : undefined;
            this.xAxisAccessor = hit => log10(this.interactionStoichAccessor(hit));
            this.yAxisAccessor = hit => log10(this.abundanceStoichAccessor(hit));
            
            // use hard-coded min/max values
            const pad = 0.25;
            this.minX = hits => -5 - pad;
            this.maxX = hits => 1 + pad;
            this.minY = hits => -3 - pad;
            this.maxY = hits => 3 + pad;

            this.xAxisLabel = 'Interaction stoichiometry (log10)';
            this.yAxisLabel = 'Abundance stoichiometry (log10)';
        }
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

        // semi-opaque loading status div (visible when data is loading or there is no data)
        const loadingDiv = d3.select(this.node)
                             .append('div')
                             .attr('class', 'f2 tc loading-overlay')
                             .style('visibility', 'hidden');
                
        this.xScale = d3.scaleLinear().range([pp.padLeft, pp.width - pp.padRight]);
        this.yScale = d3.scaleLinear().range([pp.height - pp.padBottom, pp.padTop]);

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
        const g = svg.append("g")
            .attr("class", "dot-g")
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
            .offset([-15, 0])
            .attr("class", "d3-tip")
            .html(d => `<strong>${d.label}</strong>`);
        svg.call(this.tip);

        this.zoom = d3.zoom().on('zoom', this.onZoom);
        svg.call(this.zoom);

        this.svg = svg;
        this.g = g;
        this.loadingDiv = loadingDiv;

        // define the lines for FDR curves and the core complex circle
        this.fdrLineLeft = g.append("path")
                            .attr("class", "volcano-fdr-path")
                            .datum(this.fdrDataLeft);

        this.fdrLineRight = g.append("path")
                             .attr("class", "volcano-fdr-path")
                             .datum(this.fdrDataRight);

        this.coreComplexRegion = g.append("path")
            .attr("class", "core-complex-path")
            .datum(this.coreComplexRegionData);
    }


    updateScatterPlot () {

        this.updatePlotSettings();
        const _this = this;

        if (!this.state.loaded) {
            this.loadingDiv.style('visibility', 'visible').text('Loading...');
            return;
        }
        if (!this.hits.length) {
            this.g.selectAll('.scatter-dot').remove();
            this.loadingDiv.style('visibility', 'visible').text('No data');
            return;
        }
        this.loadingDiv.style('visibility', 'hidden');

        // the hits to plot (note that we show only significant hits in stoichiometry mode)
        let hits = [];
        if (this.props.mode==='Stoichiometry') {
            hits = this.hits.filter(d => d.is_significant_hit);
        } else {
            hits = this.hits;
        }
    
        // dynamically determine the domain of the plot
        this.xScale.domain([this.minX(hits), this.maxX(hits)]);
        this.yScale.domain([this.minY(hits), this.maxY(hits)]);

        let xScale = this.xScale;
        let yScale = this.yScale;

        // retain the zoom/pan state when the target is changed
        if (this.zoomTransform) {
            xScale = this.zoomTransform.rescaleX(xScale);
            yScale = this.zoomTransform.rescaleY(yScale);
        }
    
        // update the line generator
        const line = d3.line().x(d => xScale(d.x)).y(d => yScale(d.y));
    
        if (this.props.mode==='Volcano') {
            this.fdrLineLeft.style('visibility', 'visible').attr('d', line);
            this.fdrLineRight.style('visibility', 'visible').attr('d', line);
            this.coreComplexRegion.style('visibility', 'hidden');
        } 
        if (this.props.mode==='Stoichiometry') {
            this.fdrLineLeft.style('visibility', 'hidden');
            this.fdrLineRight.style('visibility', 'hidden');
            this.coreComplexRegion.style('visibility', 'visible').attr('d', line);
        }

        // update the scatterplot dots
        const dots = this.g.selectAll('.scatter-dot').data(hits, d => d.id);
        dots.exit().remove();    
        dots.enter().append('circle')
            .attr('class', 'scatter-dot')
            .merge(dots)
            .attr('r', this.calcDotRadius)
            .attr('fill', this.calcDotColor)
            .attr('stroke', this.calcDotStroke)
            .attr('cx', d => xScale(this.xAxisAccessor(d)))
            .attr('cy', d => yScale(this.yAxisAccessor(d)))
            .on("mouseover", function (d) {
                // enlarge and outline the dots on hover
                d3.select(this)
                  .attr("r", _this.plotProps.dotRadius + 2)
                  .classed("scatter-dot-hover", true);
                _this.tip.show(d, this); 
             })
             .on("mouseout", function (d) {
                d3.select(this)
                  .attr("r", _this.calcDotRadius)
                  .classed("scatter-dot-hover", false);
                _this.tip.hide(d, this);
             })
            .on('click', d => this.props.changeTarget(d.opencell_target_names[0]));

        // bind data - filter for only significant hits
        const captions = this.g.selectAll('.scatter-caption')
                               .data(hits.filter(this.hitIsSignificant), d => d.id);

        captions.exit().remove();
        captions.enter().append('text')
                .attr('class', 'scatter-caption')
                .attr('text-anchor', 'middle')
                .text(d => d.label)
                .merge(captions)
                .attr('x', d => xScale(this.xAxisAccessor(d)))
                .attr('y', d => yScale(this.yAxisAccessor(d)) - 10)
                .attr('fill-opacity', this.captionOpacity);

        this.svg.select("#x-axis").call(this.xAxis.scale(xScale));
        this.svg.select("#y-axis").call(this.yAxis.scale(yScale));

        this.svg.select("#x-axis-label").text(this.xAxisLabel);
        this.svg.select("#y-axis-label").text(this.yAxisLabel);
    }


    captionOpacity () {
        let opacity;
        if (this.props.showCaptions==='Always') {
            opacity = 1;
        } else if (this.props.showCaptions==='Never') {
            opacity = 0;
        } else {
            opacity = this.zoomTransform ? this.captionOpacityScale(this.zoomTransform.k) : 0;
        }
        return opacity;
    }


    onZoom () {
        this.zoomTransform = d3.event.transform;
        const xScaleZoom = this.zoomTransform.rescaleX(this.xScale);
        const yScaleZoom = this.zoomTransform.rescaleY(this.yScale);

        // update the FDR or core-complex lines
        const line = d3.line().x(d => xScaleZoom(d.x)).y(d => yScaleZoom(d.y));
        if (this.props.mode==='Volcano') {
            this.fdrLineLeft.attr("d", line);
            this.fdrLineRight.attr("d", line);
        } else if (this.props.mode==='Stoichiometry') {
            this.coreComplexRegion.attr("d", line);
        }

        this.g.selectAll(".scatter-dot")
            .attr("cx", d => xScaleZoom(this.xAxisAccessor(d)))
            .attr("cy", d => yScaleZoom(this.yAxisAccessor(d)));

        this.g.selectAll(".scatter-caption")
            .attr("x", d => xScaleZoom(this.xAxisAccessor(d)))
            .attr("y", d => yScaleZoom(this.yAxisAccessor(d)) - 10)
            .attr("fill-opacity", this.captionOpacity);

        this.svg.select("#x-axis").call(this.xAxis.scale(xScaleZoom));
        this.svg.select("#y-axis").call(this.yAxis.scale(yScaleZoom));
    }


    render() {
        // the relative position is required to correctly position the loading-overlay div 
        return (
            <div className="relative" ref={node => this.node = node}/>
        );
    }

}
