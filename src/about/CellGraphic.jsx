
import * as d3 from 'd3';
import React, { Component, useState, useEffect } from 'react';
import ReactDOM from 'react-dom';
import chroma from 'chroma-js';

import 'tachyons';

import settings from '../common/settings.js';
import * as utils from '../common/utils.js';

import '../common/common.css';
import './About.css';


const labels = [
    'er', 
    'golgi', 
    'mitochondria', 
    'centrosome', 
    'cytoskeleton', 
    'cell_membrane',
    'nucleus',
    'nucleolus',
    'vesicles',
];


export default class CellGraphic extends Component {

    constructor (props) {
        super(props);
        this.state = {};
        this.fillColors = {};
        this.defineEventHandlers = this.defineEventHandlers.bind(this);
    }


    componentDidMount () {
        const defineEventHandlers = this.defineEventHandlers;
        this.node.onload = () => {
            const svg = d3.select(this.node.contentDocument).select('svg');

            labels.forEach(label => {
                const id = `#${label}`;
                svg.select(id).each(function (d) { defineEventHandlers(d3.select(this)) });

                // bring the overlays to the front
                svg.select(id).selectAll('path').filter(function () {
                    return d3.select(this).attr('id')?.startsWith('overlay');
                })
                .raise();
            });    
        };
        this.node.data = '/assets/images/opencell_simpler_no_ribosome-with-labels.svg';
    }


    defineEventHandlers (selection) {
        const fillColors = this.fillColors;

        // filter out the overlay curves
        const paths = selection.selectAll('path').filter(function () {
            return !d3.select(this).attr('id')?.startsWith('overlay');
        });

        selection
            .on('mouseover', function (d) {
                const fillColor = paths.style('fill');
                fillColors[selection.attr('id')] = fillColor;
                paths.style('fill', chroma(fillColor==='none' ? 'white' : fillColor).darken(1).hex());
            })
            .on('mouseout', function (d) {
                paths.style('fill', fillColors[selection.attr('id')]);
            })
            .on('click', function (d) {
                console.log(`Clicked on ${selection.attr('id')}`);
            });
    }


    render() {
        return (
             <object 
                type='image/svg+xml'
                ref={node => this.node = node} 
                style={{width: '300px', height: '300px'}}
            /> 
        );
    }
}