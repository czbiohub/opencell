
import * as d3 from 'd3';
import tip from 'd3-tip';
import React, { Component } from 'react';
import ReactDOM from 'react-dom';
import chroma from 'chroma-js';

import 'tachyons';
import settings from '../../settings/settings.js';


export default class MassSpecHeatmap extends Component {

    constructor (props) {
        super(props);

        this.state = {
            loaded: false,
            loadingError: false,
        };

        this.plotProps = {
            aspectRatio: 1.0,
            padLeft: 50,
            padRight: 10,
            padTop: 10,
            padBottom: 40,
            xAxisLabelOffset: 5,
            yAxisLabelOffset: 15,
        };

        this.colormapDomains = {
            'pval': [0, 50],
            'enrichment': [1, 10],
            'interaction_stoich': [-5, 0],
            'abundance_stoich': [-3, 3],
        }

        this.getData = this.getData.bind(this);
        this.tileColor = this.tileColor.bind(this);
        this.createHeatmap = this.createHeatmap.bind(this);
        this.updateHeatmap = this.updateHeatmap.bind(this);
        }

    componentDidMount() {
        this.createHeatmap();
        if (this.props.pulldownId) {
            this.getData();
            this.updateHeatmap();
        }
    }

    componentDidUpdate (prevProps) {
        if (prevProps.pulldownId!==this.props.pulldownId) {
            this.getData();
        }
        this.updateHeatmap();
    }


    getData () {
        this.setState({loaded: false, loadingError: false});
        const url = `${settings.apiUrl}/pulldowns/${this.props.pulldownId}/clusters`;
        d3.json(url).then(data => {
            this.rows = data.rows;
            this.columns = data.columns;
            this.tiles = data.tiles;
            this.setState({loaded: true, loadingError: false});
        },
        error => {
            this.setState({loaded: true, loadingError: true});
        });
    }

    tileColor (tile) {
        const scale = chroma.scale("Blues").domain(this.colormapDomains[this.props.colorMode]);
        return scale(tile[this.props.colorMode]);
    }

    toolTipText (tile) {
        const row = this.rows.filter(row => row.row_index===tile.row_index)[0];
        const col = this.columns.filter(col => col.col_index===tile.col_index)[0];
        return `Interactor: ${row.uniprot_gene_names[0]}<br>Pulldown: ${col.target_name}`;
    }


    createHeatmap () {
    
        const p = this.plotProps;
        p.width = ReactDOM.findDOMNode(this.node).offsetWidth;
        p.height = p.width * p.aspectRatio;
        
        const svg = d3.select(this.node)
            .append('svg')
            .attr('width', p.width)
            .attr('height', p.height);

        const loadingDiv = d3.select(this.node)
            .append('div')
            .attr('class', 'f2 tc loading-overlay')
            .style('visibility', 'hidden');

        this.xScale = d3.scaleBand().range([p.padLeft, p.width - p.padRight]);
        this.yScale = d3.scaleBand().range([p.height - p.padBottom, p.padTop]);

        this.xAxis = d3.axisBottom(this.xScale).tickSize(0);
        this.yAxis = d3.axisLeft(this.yScale).tickSize(0);

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

        // heatmap tile container
        this.g = svg.append("g").attr("class", "heatmap-tile-g");

        this.svg = svg;
        this.loadingDiv = loadingDiv;  

        this.tip = tip()
            .offset([-9, 2])
            .attr("class", "d3-tip")
            .html(d => this.toolTipText(d));
        svg.call(this.tip);

    }

    
    updateHeatmap () {

        if (!this.state.loaded) {
            this.loadingDiv.style('visibility', 'visible').text('Loading...');
            return;
        }
        if (this.state.loadingError) {
            this.g.selectAll('.scatter-dot').remove();
            this.loadingDiv.style('visibility', 'visible').text('No data');
            return;
        }
        this.loadingDiv.style('visibility', 'hidden');

        this.xScale.domain(this.columns.map(d => d.col_index));
        this.yScale.domain(this.rows.map(d => d.row_index));
        
        this.xAxis.tickFormat(index => {
            return this.columns.filter(column => column.col_index===index)[0].target_name;
        });

        this.yAxis.tickFormat(index => {
            return this.rows.filter(row => row.row_index===index)[0]?.uniprot_gene_names[0];
        });

        const toolTip = this.tip;

        const tiles = this.g.selectAll(".heatmap-tile").data(this.tiles, d => d.hit_id);
        tiles.exit().remove();
        tiles.enter().append("rect")
            .attr("class", "heatmap-tile")
            .merge(tiles)
            .attr("x", d => this.xScale(d.col_index))
            .attr("y", d => this.yScale(d.row_index))
            .attr("width", this.xScale.bandwidth())
            .attr("height", this.yScale.bandwidth())
            .style("fill", d => this.tileColor(d))
            .style("stroke", "white")
            .style("stroke-width", 0)
            .on("mouseover", function (d) {
                d3.select(this).style("stroke-width", 1);
                toolTip.show(d, this);
            })
            .on("mouseout", function (d) {
                d3.select(this).style("stroke-width", 0);
                toolTip.hide(d, this);
            });
        
        this.svg.select("#x-axis").call(this.xAxis.scale(this.xScale));
        this.svg.select("#y-axis").call(this.yAxis.scale(this.yScale));

        // rotate x-axis tick labels and make them clickable
        const handleGeneNameSearch = this.props.handleGeneNameSearch;
        this.svg.select("#x-axis")
            .selectAll("text")
            .attr("transform", "rotate(-45)")
            .style("text-anchor", "end")
            .on("click", function (d) {
                const targetName = d3.select(this).text();
                handleGeneNameSearch(targetName);
            });
    }


    render() {
        // the relative position is required to correctly position the loading-overlay div 
        return (
            <div className="relative" ref={node => this.node = node}/>
        );
    }

}