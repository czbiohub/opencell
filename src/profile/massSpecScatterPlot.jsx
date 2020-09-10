
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

        this.pvalueAccessor = d => parseFloat(d.pval);
        this.enrichmentAccessor = d => parseFloat(d.enrichment);
        this.abundanceStoichAccessor = d => parseFloat(d.abundance_stoich);
        this.interactionStoichAccessor = d => parseFloat(d.interaction_stoich);
        
        this.onZoom = this.onZoom.bind(this);
        this.resetZoom = this.resetZoom.bind(this);
        this.hitIsSignificant = this.hitIsSignificant.bind(this);
        this.captionOpacity = this.captionOpacity.bind(this);
        this.constructData = this.constructData.bind(this);
        this.constructFDRCurve = this.constructFDRCurve.bind(this);
        this.updateScatterPlot = this.updateScatterPlot.bind(this);
        this.drawLegend = this.drawLegend.bind(this);

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
            const baitColor = chroma('#01a1dd').alpha(0.7);  // blue
            const sigHitColor = chroma('#ff463a').alpha(0.5);  // dark red
            const minorHitColor = chroma('#ff9b89').alpha(0.5);  // light red
            const notSigHitColor = chroma('#333').alpha(0.2);
            if (d.is_bait) return baitColor
            if (!this.hitIsSignificant(d)) return notSigHitColor;
            return d.is_minor_hit ? minorHitColor : sigHitColor;
        }

        this.calcDotClass = d => {
            // use this to experiment with the dot colors by editing the css classes in devtools
            if (d.is_bait) return 'bait-dot';
            if (!this.hitIsSignificant(d)) return 'not-sig-hit-dot';
            return d.is_minor_hit ? 'minor-hit-dot' : 'sig-hit-dot';
        }

        this.calcDotStroke = d => {
            if (!this.hitIsSignificant(d)) return 'none';
            // stroke in black if the hit is also an opencell target
            if (d.opencell_target_names?.length) return chroma('#333').alpha(.9);
            return chroma(this.calcDotColor(d)).darken(2);
        }
    
        this.calcDotRadius = d => {
        
            const minRadius = 2;

            // constant dot size in stoichoimetry mode
            if (this.props.mode==='Stoichiometry') return this.plotProps.dotRadius;

            // any hit with negative enrichment is necessarily not significant
            // if (!this.hitIsSignificant(d)) return minRadius;

            // make dot size depend on pvalue and enrichment in volcano mode,
            // using distance from the origin as a proxy for significance/prominence
            const width = 15;
            const minDist = 2;
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
        const url = `${settings.apiUrl}/lines/${this.props.cellLineId}/pulldown_hits`;
        d3.json(url).then(data => {

            let sigHits = data.significant_hits;
            let nonSigHits = data.nonsignificant_hits;

            // create an array of dicts for nonsig hits to be consistent with sig hits
            nonSigHits = nonSigHits.map(d => ({pval: d[0], enrichment: d[1]}));

            // to speed up the rendering of the plot, randomly drop most non-significant hits
            nonSigHits = nonSigHits.filter(d => d.pval > 3 || d3.randomUniform(0, 1)() > .5);

            sigHits.forEach(hit => {
                // label the significant hits (so we can concatenate all of the hits together)
                hit.is_significant_hit = true;

                // construct a label from the gene names (there is one gene name for each ensg_id)
                hit.label = hit.uniprot_gene_names?.sort().join(', ');
            });
                        
            this.hits = [...sigHits, ...nonSigHits];

            // create a unique id for each hit
            // (this is needed later to correctly bind the data to the scatter dots and captions)
            const pulldownId = data.metadata.id;
            this.hits.forEach((hit, ind) => hit.id = `${pulldownId}-${ind}`);

            this.pulldownMetadata = data.metadata;

            // construct data points for the FDR curves
            this.onePercentFDRData = this.constructFDRCurve({
                x0: data.metadata.fdr_1_offset, c: data.metadata.fdr_1_curvature
            });
            this.fivePercentFDRData = this.constructFDRCurve({
                x0: data.metadata.fdr_5_offset, c: data.metadata.fdr_5_curvature
            });
            this.setState({loaded: true});
        },
        error => {
            console.log(error);
            this.hits = [];
            this.pullDownMetadata = null;
            this.setState({loaded: true});
        });
    }


    constructFDRCurve (fdrParams) {
        // 
        // for reference: parameters for 5% FDR calculated from 2019-08-02 data were
        // fdrParams = {x0: 1.62, c: 4.25};

        const xVals = d3.range(fdrParams.x0 + .01, 20, .1);
        const dataLeft = xVals.map(x => ({x: -x, y: fdrParams.c / (x - fdrParams.x0)}));
        const dataRight = xVals.map(x => ({x: x, y: fdrParams.c / (x - fdrParams.x0)}));
        return {left: dataLeft, right: dataRight};
    }

    hitIsSignificant (d) {
        // whether the hit is 'significant' and should be colored, labeled, interactive, etc
        return d.is_significant_hit || d.is_minor_hit;
    }


    updatePlotSettings () {

        if (this.props.mode==='Volcano') {
            this.xAxisAccessor = this.enrichmentAccessor;
            this.yAxisAccessor = this.pvalueAccessor;

            this.minX = hits => -d3.max(hits, this.xAxisAccessor) - 1;
            this.maxX = hits => d3.max(hits, this.xAxisAccessor) + 1;
            this.minY = hits => 0;
            this.maxY = hits => d3.max(hits, this.yAxisAccessor) + 10;

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

        const p = this.plotProps;

        // override manuallly defined widths
        p.width = ReactDOM.findDOMNode(this.node).offsetWidth;
        p.height = p.width * p.aspectRatio;
        
        const svg = d3.select(this.node)
            .append('svg')
            .attr('width', p.width)
            .attr('height', p.height);

        // semi-opaque loading status div (visible when data is loading or there is no data)
        const loadingDiv = d3.select(this.node)
            .append('div')
            .attr('class', 'f2 tc loading-overlay')
            .style('visibility', 'hidden');
                
        this.xScale = d3.scaleLinear().range([p.padLeft, p.width - p.padRight]);
        this.yScale = d3.scaleLinear().range([p.height - p.padBottom, p.padTop]);

        this.xAxis = d3.axisBottom(this.xScale)
            .tickSize(-p.height + p.padTop + p.padBottom, 0)
            .ticks(p.numTicks);

        this.yAxis = d3.axisLeft(this.yScale)
            .tickSize(-p.width + p.padLeft + p.padRight, 0)
            .ticks(p.numTicks);  

        // y axis container
        svg.append("g")
            .attr("class", "axis")
            .attr("id", "y-axis")
            .attr("transform", `translate(${p.padLeft}, 0)`);

        // x-axis container
        svg.append("g")
            .attr("class", "axis")
            .attr("id", "x-axis")
            .attr("transform", `translate(0, ${p.height - p.padBottom})`);

        // x-axis label
        svg.append("text")
            .attr("class", "axis-label")
            .attr("id", "x-axis-label")
            .attr("text-anchor", "middle")
            .attr("x", p.width/2)
            .attr("y", p.height - p.xAxisLabelOffset);

        // y-axis label
        svg.append("text")
            .attr("class", "axis-label")
            .attr("id", "y-axis-label")
            .attr("text-anchor", "middle")
            .attr("x", -p.height/2)
            .attr("y", p.yAxisLabelOffset)
            .attr("transform", "rotate(-90)");

        // scatter dot container
        const g = svg.append("g")
            .attr("class", "dot-g")
            .attr("clip-path", `url(#clip)`);

        // clipPath to mask dots outside of the axes (needed for zooming)
        g.append("clipPath")
            .attr("id", `clip`)
            .append("rect")
            .attr("x", p.padLeft)
            .attr("y", p.padTop)
            .attr("width", p.width - p.padLeft - p.padRight)
            .attr("height", p.height - p.padTop - p.padBottom);

        // container for the legend (added last so its on top)
        const legendContainer = svg.append("g");

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
        this.legendContainer = legendContainer;

        // define the lines for FDR curves and the core complex circle
        this.fdrLines = {
            oneLeft: g.append("path").attr("class", "volcano-fdr-path"),
            oneRight: g.append("path").attr("class", "volcano-fdr-path"),
            fiveLeft: g.append("path").attr("class", "volcano-fdr-path"),
            fiveRight: g.append("path").attr("class", "volcano-fdr-path"),
        }

        this.coreComplexRegion = g.append("path")
            .attr("class", "core-complex-path")
            .datum(this.coreComplexRegionData);
    }


    drawLegend () {

        const legend = this.legendContainer;
        legend.selectAll("rect").remove();
        legend.selectAll("circle").remove();
        legend.selectAll("line").remove();
        legend.selectAll("text").remove();

        let lineNum, d;
        const dotSize = 5,
            padLeft = 40,
            padTop = 20,
            textOffset = 15,
            lineHeight = 20,
            fontSize = "13px";

        const numLines = this.props.mode==="Stoichiometry" ? 3 : 5;
        legend.append("rect")
            .attr("x", 0)
            .attr("y", 0)
            .attr("width", 200)
            .attr("height", padTop + lineHeight * numLines)
            .attr("fill", chroma("white").alpha(0.7));

        const appendText = (lineNum, text) => {
            legend.append("text")
            .attr("x", padLeft + textOffset)
            .attr("y", padTop + lineNum * lineHeight)
            .text(text)
            .style("font-size", fontSize)
            .attr("alignment-baseline", "middle");
        }

        // bait hit (define dummy opencell_target_names array so that the dot stroke is black)
        lineNum = 0;
        d = {is_bait: true, opencell_target_names: [null]}
        legend.append("circle")
            .attr("cx", padLeft)
            .attr("cy", padTop + lineNum * lineHeight)
            .attr("r", dotSize)
            .attr("fill", this.calcDotColor(d))
            .attr("stroke", "#333");
        appendText(lineNum, "Bait");

        // significant hits
        lineNum = 1;
        d = {is_bait: false, is_significant_hit: true, is_minor_hit: false};
        legend.append("circle")
            .attr("cx", padLeft)
            .attr("cy", padTop + lineNum * lineHeight)
            .attr("r", dotSize)
            .attr("fill", this.calcDotColor(d))
            .attr("stroke", this.calcDotStroke(d));
        appendText(lineNum, "Significant hit");

        // minor hits
        lineNum = 2;
        d = {is_bait: false, is_significant_hit: false, is_minor_hit: true};
        legend.append("circle")
            .attr("cx", padLeft)
            .attr("cy", padTop + lineNum * lineHeight)
            .attr("r", dotSize)
            .attr("fill", this.calcDotColor(d))
            .attr("stroke", this.calcDotStroke(d));
        appendText(lineNum, "Minor hit");

        // no need for non-sig hits or FDR curves in stoich mode
        if (this.props.mode==="Stoichiometry") return;

        // not-significant hits
        lineNum = 3;
        d = {is_bait: false, is_significant_hit: false, is_minor_hit: false};
        legend.append("circle")
            .attr("cx", padLeft)
            .attr("cy", padTop + lineNum * lineHeight)
            .attr("r", dotSize)
            .attr("fill", this.calcDotColor(d))
            .attr("stroke", this.calcDotStroke(d));
        appendText(lineNum, "Non-significant hit");

        // FDR curves
        lineNum = 4;
        legend.append("line")
            .attr("x1", padLeft - 10)
            .attr("x2", padLeft + 10)
            .attr("y1", padTop + lineNum * lineHeight)
            .attr("y2", padTop + lineNum * lineHeight)
            .attr("class", "volcano-fdr-path");
        appendText(lineNum, "1% and 5% FDR curves");

    }


    updateScatterPlot () {

        this.updatePlotSettings();
        this.drawLegend();
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

        // update the FDR curve data
        this.fdrLines.oneLeft.datum(this.onePercentFDRData.left);
        this.fdrLines.oneRight.datum(this.onePercentFDRData.right);
        this.fdrLines.fiveLeft.datum(this.fivePercentFDRData.left);
        this.fdrLines.fiveRight.datum(this.fivePercentFDRData.right);

        // the hits to plot (note that we show only significant hits in stoichiometry mode)
        let hits;
        if (this.props.mode==='Stoichiometry') {
            hits = this.hits.filter(d => this.hitIsSignificant(d));
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
            for (const fdrLine of Object.values(this.fdrLines)) {
                fdrLine.style('visibility', 'visible').attr('d', line);
            }
            this.coreComplexRegion.style('visibility', 'hidden');
        } 
        if (this.props.mode==='Stoichiometry') {
            for (const fdrLine of Object.values(this.fdrLines)) {
                fdrLine.style('visibility', 'hidden');
            }
            this.coreComplexRegion.style('visibility', 'visible').attr('d', line);
        }

        // update the scatterplot dots
        const dots = this.g.selectAll('.scatter-dot').data(hits, d => d.id);
        dots.exit().remove();    
        dots.enter().append('circle')
            .attr('class', 'scatter-dot') //d => 'scatter-dot ' + this.calcDotClass(d))
            .merge(dots)
            .attr('r', this.calcDotRadius)
            .attr('fill', this.calcDotColor)
            .attr('stroke', this.calcDotStroke)
            .attr('cx', d => xScale(this.xAxisAccessor(d)))
            .attr('cy', d => yScale(this.yAxisAccessor(d)))
            .on("mouseover", function (d) {
                if (!_this.hitIsSignificant(d)) return;
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

        if ((!this.state.loaded) || (!this.hits.length)) return;

        this.zoomTransform = d3.event.transform;
        const xScaleZoom = this.zoomTransform.rescaleX(this.xScale);
        const yScaleZoom = this.zoomTransform.rescaleY(this.yScale);

        // update the FDR or core-complex lines
        const line = d3.line().x(d => xScaleZoom(d.x)).y(d => yScaleZoom(d.y));
        if (this.props.mode==='Volcano') {
            for (const fdrLine of Object.values(this.fdrLines)) {
                fdrLine.attr("d", line);
            }
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
