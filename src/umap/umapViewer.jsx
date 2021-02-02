
import * as d3 from 'd3';
import d3tip from 'd3-tip';
import chroma from 'chroma-js';
import React, { Component } from 'react';

import 'tachyons';
import './umap.css';
import settings from '../common/settings.js';
import annotationDefs from '../common/annotationDefs.js';


const colors = {
    
    green: chroma([102., 194., 165.]).hex(),
    blue: chroma([141., 160., 203.]).hex(),
    pink: chroma([231., 138., 195.]).hex(),
    yellow: chroma([255., 217.,  47.]).hex(),
    tan: chroma([229., 196., 148.]).hex(),
    gray: chroma([179., 179., 179.]).hex(),
    
    //orange: chroma([252., 141.,  98.]).hex(),
    orange: '#ff6c33',
    
    //lime: chroma([166., 216.,  84.]).hex(),
    lime: '#5dde49',

    brightBlue: '#5bb1ea',
    purple: '#bb73d8',
    red: '#f32f2f',
};


const getColorDefs = () => {
    const colorDefs = {
        er: chroma(colors.orange),
        golgi: chroma(colors.lime),
        mitochondria: chroma(colors.yellow),
        vesicles: chroma(colors.purple),
        membrane: chroma(colors.pink),
        chromatin: chroma(colors.blue).darken(),
        nucleoplasm: chroma(colors.blue).brighten(),
        nuclear_membrane: chroma(colors.brightBlue),
        nucleolus: chroma(colors.tan),
        cytoplasmic: chroma(colors.green).darken(),
        aggregates: chroma(colors.tan).darken(1.5),
        other: '#aaa',
        unannotated: '#555',
    };

    // interpolate dark and light blue for multi-localizing in the nucleus
    colorDefs.multiNuclear = chroma.mix(colorDefs.chromatin, colorDefs.nucleoplasm);

    return colorDefs;
}


export default class UMAPViewer extends Component {

    constructor(props) {
        super(props);
        
        this.state = {
            loaded: false,
        };

        // the size of the canvas 
        // HACK: this is chosen to be large enough to prevent downsampling the thumbnails,
        // but it really should be set to max(umap_coords) * nativeThumbnailSize
        this.canvasSize = 4000;

        // the size of the canvas on the screen
        // NOTE: the ratio of canvasSize to canvasRenderedSize 
        // should be at least equal to window.devicePixelRatio
        // (which is equal to 2.0 on my macbook pro)
        this.canvasRenderedSize = undefined;

        // the native size of each thumbnail in the JPG of tiled thumbnails
        // HACK: this is hard-coded for now, but depends on props.thumbnailTileFilename
        this.nativeThumbnailSize = 100;

        this.colorDefs = getColorDefs();

        this.maybeLoadData = this.maybeLoadData.bind(this);
        this.updateDerivedConstants = this.updateDerivedConstants.bind(this);
        this.getOrCreatePattern = this.getOrCreatePattern.bind(this);
        this.calcDotColor = this.calcDotColor.bind(this);

        this.redrawLegend = this.redrawLegend.bind(this);
        this.drawThumbnail = this.drawThumbnail.bind(this);
        this.redrawThumbnails = this.redrawThumbnails.bind(this);
        this.updateThumbnailDots = this.updateThumbnailDots.bind(this);

        this.addCanvasEventHandlers = this.addCanvasEventHandlers.bind(this);
        this.onUmapZoom = this.onUmapZoom.bind(this);
        this.onCanvasMouseMove = this.onCanvasMouseMove.bind(this);
        this.resetZoom = this.resetZoom.bind(this);
    }


    componentDidMount() {

        // define the extent of the (square) canvas in client screen pixels
        this.canvasRenderedSize = d3.max([window.innerHeight, window.innerWidth]);

        // create the visible canvas
        const canvas = d3.select(this.node)
            .append('canvas')
            .attr('class', 'umap-canvas')
            .attr('width', this.canvasSize)
            .attr('height', this.canvasSize)
            .style('width', `${this.canvasRenderedSize}px`)
            .style('height', `${this.canvasRenderedSize}px`);

        this.canvas = canvas.node();

        // create the overlaid SVG
        this.svg = d3.select(this.node)
            .append('svg')
            .attr('class', 'umap-svg')
            .style('width', `${this.canvasRenderedSize}px`)
            .style('height', `${this.canvasRenderedSize}px`);

        this.tip = d3tip()
            .offset([-15, 0])
            .attr("class", "umap-tip")
            .html(d => `
                <strong>${d.target_name}</strong><br>
                Grade 3: ${d.grade3.join(', ')}<br>
                Grade 2: ${d.grade2.join(', ')}
            `);
        this.svg.call(this.tip);

        // off-screen canvas for 'holding' the rendered canvas while applying zoom transforms
        this.shadowCanvas = document.createElement('canvas');
        d3.select(this.shadowCanvas)
            .attr('width', this.canvas.width)
            .attr('height', this.canvas.height);

        // off-screen canvas for the JPG of tiled thumbnails
        this.tiledThumbnailCanvas = document.createElement("canvas");
        
        // div for outlining the hovered thumbnail
        this.hoveredThumbnailDiv = d3.select(this.node)
            .append('div')
            .attr('class', 'thumbnail-hover-container');

        // create the patterns for common combinations of localization categories 
        this.svg.append('defs');
        this.getOrCreatePattern('nucleoplasm', 'cytoplasmic', true);
        this.getOrCreatePattern('membrane', 'vesicles', true);

        // container for the legend (in dot mode)
        this.legendContainer = this.svg.append('g')
            .attr('id', 'legend-container')
            .attr('transform', 'translate(50, 500)');

    }


    getOrCreatePattern (categoryA, categoryB, create = false) {
        // create a cross-hatched SVG pattern using the colors associated with the two categories

        const patternId = `${categoryA}-${categoryB}-pattern`;
        const url = `url(#${patternId})`;
        if (!create) return url;

        const pattern =  this.svg.select('defs')
            .append('pattern')
            .attr('patternUnits', 'userSpaceOnUse')
            .attr('patternTransform', 'rotate(45)')
            .attr('id', patternId)
            .attr('width', 4)
            .attr('height', 4);
        
        pattern.append('rect')
            .attr('width', '2')
            .attr('height', '4')
            .attr('transform', 'translate(0, 0)')
            .attr('fill', this.colorDefs[categoryA]);

        pattern.append('rect')
            .attr('width', '2')
            .attr('height', '4')
            .attr('transform', 'translate(2, 0)')
            .attr('fill', this.colorDefs[categoryB]);

        return url;
    }


    redrawLegend () {

        const legendDefs = {
            er: {
                name: 'Endoplasmic reticulum',
                categories: ['er'],
            },
            golgi: {
                name: 'Golgi apparatus',
                categories: ['golgi'],
            },
            mitochondria: {
                name: 'Mitochondria',
                categories: ['mitochondria'],
            },
            aggregates: {
                name: 'Cytoplasmic aggregates',
                categories: ['small_aggregates'],
            },
            vesicles: {
                name: 'Vesicles',
                categories: ['vesicles'],
            },
            membrane: {
                name: 'Cell membrane',
                categories: ['membrane'],
            },
            membraneAndVesicles: {
                name: 'Cell membrane and vesicles',
                categories: ['membrane', 'vesicles'],
            },
            nuclearMembrane: {
                name: 'Nuclear membrane',
                categories: ['nuclear_membrane'],
            },
            nucleolus: {
                name: 'Nucleolus',
                categories: ['nucleolus_gc'],
            },
            chromatin: {
                name: 'Chromatin',
                categories: ['chromatin'],
            },
            multiNuclear: {
                name: 'Nucleus (multi-localized)',
                categories: ['nuclear_punctae'],
            },
            nucleoplasm: {
                name: 'Nucleoplasmic',
                categories: ['nucleoplasm'],
            },
            cytoplasmic: {
                name: 'Cytoplasmic',
                categories: ['cytoplasmic'],
            },
            cytoplasmicAndNucleoplasmic: {
                name: 'Cytoplasmic and nucleoplasmic',
                categories: ['cytoplasmic', 'nucleoplasm'],
            },
            other: {
                name: 'Other and/or multi-localized',
                categories: ['cilia'],
            },
            unannotated: {
                name: 'Unannotated',
                categories: [],
            },
        };

        // keys of legendDefs in order
        const orderedLegendDefNames = [
            'er', 
            'golgi', 
            'mitochondria', 
            'aggregates',
            'membrane', 
            'vesicles', 
            'membraneAndVesicles',
            'nuclearMembrane', 
            'nucleolus',
            'chromatin', 
            'multiNuclear',
            'nucleoplasm', 
            'cytoplasmic',
            'cytoplasmicAndNucleoplasmic',
            'other',
            'unannotated',
        ];

        const dotSize = 6,
            padLeft = 30,
            padTop = 20,
            textOffset = 15,
            lineHeight = 20,
            fontSize = "13px";

        const numLines = 16;

        d3.select(this.props.legendNode).select('svg').remove();
        const legend = d3.select(this.props.legendNode).append('svg')
            .attr('height', (numLines  + 1) * lineHeight)
            .attr('width', '250px');

        const drawLegendItem = (legendDef, lineNum) => {
            // mock the position object expected by this.calcDotColor
            const d = {grade3: legendDef.categories, grade2: []};

            legend.append("circle")
                .attr("cx", padLeft)
                .attr("cy", padTop + lineNum * lineHeight)
                .attr("r", dotSize)
                .attr("fill", this.calcDotColor(d))
                .attr("stroke", chroma(this.calcDotColor(d, 'stroke')).darken(2));

            legend.append("text")
                .attr("x", padLeft + textOffset)
                .attr("y", padTop + lineNum * lineHeight + 1)
                .attr("alignment-baseline", "middle")
                .style("font-size", fontSize)
                .style('fill', 'white')
                .text(legendDef.name);
        }

        orderedLegendDefNames.map((name, ind) => drawLegendItem(legendDefs[name], ind));

    }

    componentDidUpdate (prevProps, prevState) {

        // load the JPG image of tiled thumbnails and the JSON array of thumbnail positions
        this.maybeLoadData();
        
        if (this.state.loaded && !prevState.loaded) {

            // copy the positions and normalize the raw positions
            this.positions = [...this.props.positions];
            this.normalizeCoords(this.positions, 'raw');

            this.redrawLegend();
            this.redrawThumbnails();
            this.addCanvasEventHandlers();
            this.resetZoom();

        } else if (this.props.resetZoom!==prevProps.resetZoom) {
            this.resetZoom();

        } else {
            this.redrawThumbnails();
        }
        
        // re-apply the last transform
        if (this.lastTransform) this.onUmapZoom(this.lastTransform, 'all');

        console.log(this.svg.selectAll('text').data().length);
    }


    componentWillUnmount () {
        d3.selectAll(".umap-tip").remove();
    }


    updateDerivedConstants () {
        // update constants that depend on the rendered canvas size
        // and the thumbnail size (in canvas pixels)

        // the ratio of canvas pixels to screen pixels
        // (this is needed because the transform coordinates are in screen pixels, 
        // but the canvas translation is done in canvas pixels)
        this.canvasPixelsPerScreenPixel = this.canvasSize/this.canvasRenderedSize;

        // thumbnail size in client screen pixels
        this.renderedThumbnailSize = this.canvasThumbnailSize/this.canvasPixelsPerScreenPixel;
    }


    maybeLoadData () {
        if (this.state.loaded) return;

        const img = new Image;
        img.setAttribute('crossOrigin', '');
        img.onload = () => {

            // set the size of the virtual canvas to the actual size of the image
            d3.select(this.tiledThumbnailCanvas)
                .attr("width", img.naturalWidth)
                .attr("height", img.naturalHeight);

            // draw the image on the 'raw' canvas
            let context = this.tiledThumbnailCanvas.getContext('2d');
            context.drawImage(img, 0, 0);
            this.setState({loaded: true});
        }
        img.src = `${settings.apiUrl}/thumbnail_tiles/${this.props.thumbnailTileFilename}`;
    }


    calcDotColor (position, type = 'fill') {
        // Determine the dot fill color from the target localization categories

        const colorDefs = getColorDefs();

        // try using only the grade-3 categories
        if (position.grade3.length) {
            return this.getColorFromCategories(position.grade3, type);
        }
        // if there are no grade-3 categories, try using grade-2
        if (position.grade2.length) {
            return this.getColorFromCategories(position.grade2, type);
        }
        // if we're still here, there were no categories of any grade
        return colorDefs.unannotated;
    }


    getColorFromCategories (categories, type) {
        // type : 'fill' or 'stroke'
    
        const colorDefs = getColorDefs();

        // targets that are both cytoplasmic and nucleoplasmic
        if (
            (categories.length===1 && categories[0]==='nucleus_cytoplasm_variation') ||
            categories.filter(cat => ['cytoplasmic', 'nucleoplasm'].includes(cat)).length===2
        ) {
            // return colorDefs.nuclear_and_cytoplasmic;
            return (
                type==='fill' ? 
                this.getOrCreatePattern('nucleoplasm', 'cytoplasmic') : 
                chroma.mix(colorDefs.nucleoplasm, colorDefs.cytoplasmic)
            );
        }

        // targets that are both membrane and vesicles
        if (categories.filter(cat => ['membrane', 'vesicles'].includes(cat)).length===2) {
            // return colorDefs.membrane_and_vesicles;
            return (
                type==='fill' ? 
                this.getOrCreatePattern('membrane', 'vesicles') : 
                chroma.mix(colorDefs.membrane, colorDefs.vesicles)
            );
        }
    
        // all aggregates categories
        const aggregateCats = ['big_aggregates', 'small_aggregates'];
        if (categories.every(cat => aggregateCats.includes(cat))) return colorDefs.aggregates;
        
        // nucleolus categories
        const nucleolusCats = ['nucleolus_gc', 'nucleolus_fc_dfc'];
        if (categories.every(cat => nucleolusCats.includes(cat))) return colorDefs.nucleolus;

        // targets with multiple, but only, nuclear annotations
        const allNuclearCats = [
            'chromatin', 'nucleoplasm', 'nuclear_punctae', 'nucleolar_ring', ...nucleolusCats
        ];
        if (categories.length > 1 && categories.every(cat => allNuclearCats.includes(cat))) {
            return colorDefs.multiNuclear;
        }

        // we cannot handle any other category combinations
        if (categories.length > 1) return colorDefs.other;
        
        // remaining categories that are assigned to a color
        const catsWithColorDef = [
            'nuclear_membrane', 
            'er', 
            'golgi', 
            'mitochondria', 
            'vesicles', 
            'membrane',
            'chromatin', 
            'nucleoplasm', 
            'cytoplasmic'
        ];
        for (let cat of catsWithColorDef) {
            if (categories.includes(cat)) return colorDefs[cat];
        }

        // handle the nuclear categories that are not assigned their own color
        for (let cat of allNuclearCats) {
            if (categories.includes(cat)) return colorDefs.multiNuclear;
        }

        return colorDefs.other;
    }


    normalizeCoords(data, coord) {
        const xScale = d3.scaleLinear().range([0, 1]).domain([
            d3.min(data, d => d[coord][0]),
            d3.max(data, d => d[coord][0]),
        ]);
        const yScale = d3.scaleLinear().range([0, 1]).domain([
            d3.min(data, d => d[coord][1]),
            d3.max(data, d => d[coord][1]),
        ]);
        data.forEach(d => {
            d[coord] = [xScale(d[coord][0]), yScale(d[coord][1])];
        });
    }


    redrawThumbnails () {
        if (!this.positions) return;

        if (this.props.coordType==='raw') {
            // NOTE: this assumes the raw coordinates have been normalized to [0, 1]
            this.umapScale = d3.scaleLinear()
                .rangeRound([0, this.canvasSize])
                .domain([-0.01, 1.03]);

            // hard-coded thumbnail size in canvas pixels (this is empirically chosen)
            this.canvasThumbnailSize = 100;
        }
        if (this.props.coordType==='gridded') {
            this.umapScale = d3.scaleLinear()
                .rangeRound([0, this.canvasSize])
                .domain([0, this.props.gridSize + 1]);

            // the size of the thumbnail in canvas pixels in determined by the grid size
            this.canvasThumbnailSize = this.umapScale(1) - this.umapScale(0);
        }

        this.updateDerivedConstants();
        const inDotMode = this.props.markerType!=='thumbnails';

        let context = this.shadowCanvas.getContext('2d');

        // reset the entire canvas to black
        context.fillStyle = 'black';
        context.fillRect(0, 0, this.canvas.width, this.canvas.height);

        // copy the thumbnail images from the tiled thumbnail canvas to the off-screen umap canvas
        if (!inDotMode) {
            this.props.positions.map(position => this.drawThumbnail(context, position));
        }

        // bind the thumbnail containers to the positions
        let g = this.svg.selectAll('.thumbnail-container')
            .data(this.positions, d => d.cell_line_id);

        g.exit().remove();

        const tip = this.tip;
    
        // create the thumbnail containers and their circle elements (that is, the scatterplot dots)
        g.enter().append('g')
            .attr('class', 'thumbnail-container')
            .append('circle')
            .attr('class', 'thumbnail-circle')
            .attr('id', d => d.target_name)
            .on('mouseover', function (d) {

                // bring the hovered rect to the front (using .raise)
                d3.select(this).classed('thumbnail-circle-hover', true).raise();
                tip.show(d, this);
                
                // TODO: if displaying the raw umap coords, 
                // redraw the hovered thumbnail on the canvas to bring it to the front
                // notes about why this is tricky:
                // 1) this requires drawing to the shadowCanvas and then calling onCanvasZoom;
                // 2) for rounded thumbnails, this will require masking the corners somehow,
                // possibly by creating an in-memory per-thumbnail PNG with transparent corners, 
                // then drawing this PNG to the canvas for each thumbnail
                // (a PNG version of the tiled thumbnail JPG would be too large, 
                // but context.drawImage does apparently use the alpha channel of 24-bit PNGs)
            })
            .on('mouseout', function (d) {
                d3.select(this).classed('thumbnail-circle-hover', false);
                tip.hide(d, this);
            });
        
        // update the dots
        this.svg.selectAll('.thumbnail-circle')
            .style('fill', d => this.calcDotColor(d))
            .style('fill-opacity', inDotMode ? 1 : 0)
            .style('stroke', d => inDotMode ? chroma(this.calcDotColor(d, 'stroke')).darken(2) : '#999');
        
        // explicitly destroy the captions to reduce lag when zooming or panning
        // (rather than setting their visibility to 'hidden')
        this.svg.selectAll('.thumbnail-text').remove();
        if (this.props.showCaptions) {
            g.append('text')
                .attr('class', 'thumbnail-text')
                .attr('y', 20)
                .text(d => d.target_name);                
        }
    }


    updateThumbnailDots (transform) {
        // update the translation-independent but scale-dependent properties of the thumbnail dots
        
        const inDotMode = this.props.markerType!=='thumbnails';
        const zoomedThumbnailSize = this.renderedThumbnailSize*transform.k;

        this.svg.selectAll('.thumbnail-circle')
            .attr('r', inDotMode ? 6 + transform.k/1.5 : zoomedThumbnailSize/2)
            .attr('cx', zoomedThumbnailSize/2)
            .attr('cy', zoomedThumbnailSize/2)
            .style('stroke-width', inDotMode ? '1.5px' : `${0.7 + transform.k/4}px`);

        if (this.props.showCaptions) {
            this.svg.selectAll('.thumbnail-text')
                .attr('x', zoomedThumbnailSize/2)
                .attr('y', inDotMode ? 10 + 4 * transform.k : 20 + 1 * transform.k)
                //.attr('opacity', transform.k < 2 ? 0 : 1 - 2/transform.k);
        }
    }


    drawThumbnail(context, position) {
        context.drawImage(
            this.tiledThumbnailCanvas,
            
            // top-left corner of the source ROI (note that the col, row order is switched)
            position.tile_column * this.nativeThumbnailSize, 
            position.tile_row * this.nativeThumbnailSize,
            
            // source ROI width and height 
            this.nativeThumbnailSize, this.nativeThumbnailSize,
            
            // top-left corner of the destination ROI
            this.umapScale(position[this.props.coordType][1]), 
            this.umapScale(position[this.props.coordType][0]), 

            // destination ROI width height
            this.canvasThumbnailSize, this.canvasThumbnailSize,
        );
    }


    onUmapZoom(transform, update = 'minimal') {

        console.log(update);

        // hovered thumbnail div used only in onCanvasMouseMove
        //this.hoveredThumbnailDiv.style('visibility', 'hidden');

        // clear the visible canvas
        const context = this.canvas.getContext('2d');
        context.save();
        context.clearRect(0, 0, this.canvas.width, this.canvas.height);

        // apply the transform
        context.translate(
            transform.x*this.canvasPixelsPerScreenPixel, 
            transform.y*this.canvasPixelsPerScreenPixel
        );
        context.scale(transform.k, transform.k);

        // re-draw the image (without smoothing, to show the true pixels when zoomed in)
        // context.imageSmoothingEnabled = false;
        context.drawImage(this.shadowCanvas, 0, 0, this.canvas.width, this.canvas.height);
        context.restore();
        
        // update the thumbnail containers
        const scaleX = x => transform.applyX(this.umapScale(x) / this.canvasPixelsPerScreenPixel);
        const scaleY = y => transform.applyY(this.umapScale(y) / this.canvasPixelsPerScreenPixel);
        this.svg.selectAll('.thumbnail-container')
            .attr('transform', d => {
                return `
                    translate(${scaleX(d[this.props.coordType][1])}, ${scaleY(d[this.props.coordType][0])})
                `;
            });
        
        // try to reduce lag when the user is only dragging and not zooming
        // by skipping the scale-dependent properties of the thumbnail circles
        if (transform.k!==this.lastTransform?.k || update==='all') {
            this.updateThumbnailDots(transform);
        }
        this.lastTransform = transform;
    }


    resetZoom() {
        // set the initial transform so that the full UMAP fits and is horizontally centered
        const initialTransform = d3.zoomIdentity.translate(window.innerWidth/4, 20).scale(0.6);
        this.svg.call(this.d3zoom.transform, initialTransform);     
    }


    addCanvasEventHandlers () {

        // // highlight the hovered thumbnail (currently unused)
        // const onCanvasMouseMove = this.onCanvasMouseMove;
        // d3.select(this.canvas)
        //     .on('mousemove', function () { 
        //         onCanvasMouseMove(d3.mouse(this), d3.zoomTransform(this));
        //     })
        //     .on('mouseout', () => this.hoveredThumbnailDiv.style('visibility', 'hidden'));

        // add zooming to the overlaid SVG element
        this.d3zoom = d3.zoom()
            .scaleExtent([0.5, 4])
            .on('zoom', () => this.onUmapZoom(d3.event.transform));
        
        this.svg.call(this.d3zoom);
    }


    onCanvasMouseMove (mousePosition, transform) {
        // Draw a div around the thumbnail the mouse is hovered over
        // NOTE: this is currently unused; mouseover events on the overlaid SVG rects 
        // are used for this purpose instead
        //
        // mousePosition : the current mouse position on the canvas (in client pixel coordinates)
        // transform : the current d3.zoomTransform applied to the canvas

        // thumbnail size in UMAP coordinates
        const umapThumbnailSize = this.umapScale.invert(this.canvasThumbnailSize) - this.umapScale.domain()[0];

        // the mouse position in rendered canvas pixel coordinates 
        // (that is, relative to the 800x800 rendered canvas)
        const mouseRenderedPosition = transform.invert(mousePosition);

        // the mouse position in UMAP coordinates (either a grid cell or the normalized position)
        let mouseUmapPosition = [
            this.umapScale.invert(mouseRenderedPosition[0] * this.canvasPixelsPerScreenPixel), 
            this.umapScale.invert(mouseRenderedPosition[1] * this.canvasPixelsPerScreenPixel)
        ];

        // clamp the mouse position to the grid coordinates
        if (this.props.coordType==='gridded') {
            mouseUmapPosition = mouseUmapPosition.map(val => Math.floor(val));
        }

        // move the mouse position to the top left of the thumbnail,
        // because this (and not the thumbnail center) is what the umap positions correspond to
        if (this.props.coordType==='raw') {
            mouseUmapPosition = mouseUmapPosition.map(val => val - umapThumbnailSize/2);
        }

        const dists = this.positions.map(d => {
            const thumbnailPosition = d[this.props.coordType];
            return (
                (thumbnailPosition[1] - mouseUmapPosition[0])**2 + 
                (thumbnailPosition[0] - mouseUmapPosition[1])**2
            );
        });
        const minDist = d3.min(dists);

        // if the mouse is not over a thumbnail
        if (Math.sqrt(minDist) > (umapThumbnailSize/2)) {
            this.hoveredThumbnailDiv.style('visibility', 'hidden');
            return;
        }

        // the thumbnail the mouse is hovering over
        const thumbnail = this.positions[dists.indexOf(minDist)];

        // the top-left corner of the hovered thumbnail in client pixel coordinates
        const thumbnailPosition = transform.apply([
            this.umapScale(thumbnail[this.props.coordType][1]) / this.canvasPixelsPerScreenPixel,
            this.umapScale(thumbnail[this.props.coordType][0]) / this.canvasPixelsPerScreenPixel,
        ]);

        // update the position of the hover div
        this.hoveredThumbnailDiv
            .style('width', `${this.renderedThumbnailSize * transform.k}px`)
            .style('height', `${this.renderedThumbnailSize * transform.k}px`)
            .style('left', `${thumbnailPosition[0]}px`)
            .style('top', `${thumbnailPosition[1]}px`)
            .style('visibility', 'visible')
            .text(thumbnail?.target_name);
    }


    render() {
        return (
             <div ref={node => this.node = node} style={{position: 'relative'}}/> 
        );
    }
}