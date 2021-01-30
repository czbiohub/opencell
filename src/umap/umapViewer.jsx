
import * as d3 from 'd3';
import d3tip from 'd3-tip';
import chroma from 'chroma-js';
import React, { Component } from 'react';

import 'tachyons';
import './umap.css';
import settings from '../common/settings.js';
import annotationDefs from '../common/annotationDefs.js';
import { zoom } from 'd3';


const colors = {
    green: chroma([102., 194., 165.]).hex(),
    orange: chroma([252., 141.,  98.]).hex(),
    blue: chroma([141., 160., 203.]).hex(),
    pink: chroma([231., 138., 195.]).hex(),
    lime: chroma([166., 216.,  84.]).hex(),
    yellow: chroma([255., 217.,  47.]).hex(),
    tan: chroma([229., 196., 148.]).hex(),
    gray: chroma([179., 179., 179.]).hex(),
};


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

        this.maybeLoadData = this.maybeLoadData.bind(this);
        this.updateDerivedConstants = this.updateDerivedConstants.bind(this);

        this.drawThumbnail = this.drawThumbnail.bind(this);
        this.drawThumbnails = this.drawThumbnails.bind(this);
        this.updateThumbnailRects = this.updateThumbnailRects.bind(this);
        
        this.addCanvasEventHandlers = this.addCanvasEventHandlers.bind(this);
        this.onUmapZoom = this.onUmapZoom.bind(this);
        this.onCanvasMouseMove = this.onCanvasMouseMove.bind(this);
        this.resetZoom = this.resetZoom.bind(this);
        
        this.calcDotColor = this.calcDotColor.bind(this);
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
            .html(d => (`
                <strong>${d.target_name}</strong><br>
                Grade 3: ${d.grade3.join(', ')}<br>
                Grade 2: ${d.grade2.join(', ')}
            `));
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

    }


    componentDidUpdate (prevProps, prevState) {

        // load the JPG image of tiled thumbnails and the JSON array of thumbnail positions
        this.maybeLoadData();
        
        if (this.state.loaded && !prevState.loaded) {

            // copy the positions and normalize the raw positions
            this.positions = [...this.props.positions];
            this.normalizeCoords(this.positions, 'raw');

            this.drawThumbnails();
            this.addCanvasEventHandlers();
            this.resetZoom();

        } else if (this.props.resetZoom!==prevProps.resetZoom) {
            this.resetZoom();

        } else {
            this.drawThumbnails();
        }
        
        // re-apply the last transform
        if (this.lastTransform) this.onUmapZoom(this.lastTransform);
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


    calcDotColor (position) {

        let color = this.getColorFromCategories(position.grade3);
        if (!color) color = this.getColorFromCategories([...position.grade3, ...position.grade2]);
        if (!color) color = '#999';
        return color;
    }

    getColorFromCategories (categories) {

        // a separate color for things that are both cytoplasmic and nucleoplasmic
        if (categories.includes('cytoplasmic') && categories.includes('nucleoplasm')) {
            return chroma.mix(chroma(colors.green).darken(), chroma(colors.blue).brighten());
        }

        if (categories.includes('er')) return colors.pink;
        if (categories.includes('golgi')) return colors.orange;
        if (categories.includes('vesicles')) return colors.yellow;
        if (categories.includes('mitochondria')) return colors.lime;

        if (categories.includes('membrane')) return chroma(colors.yellow).darken(1.5);
        if (categories.includes('nuclear_membrane')) return chroma(colors.tan).darken(1.5);

        // all nucleolus categories in one color
        if (
            categories.includes('nuclear_punctae') ||
            categories.filter(s => s.startsWith('nucleolus')).length
        ) return colors.tan;

        if (categories.includes('chromatin')) return chroma(colors.blue).darken();
        if (categories.includes('nucleoplasm')) return chroma(colors.blue).brighten();
        if (categories.includes('cytoplasmic')) return chroma(colors.green).darken();

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


    drawThumbnails () {

        if (!this.positions) return;

        if (this.props.coordType==='raw') {

            // hard-coded thumbnail size in canvas pixels
            // (in raw coords, this is not constrained by the grid)
            this.canvasThumbnailSize = 100;

            // resize the canvas to avoid downsampling the thumbnails
            this.canvasSize = 4000;
            d3.select(this.canvas).attr('width', this.canvasSize).attr('height', this.canvasSize);
            d3.select(this.shadowCanvas).attr('width', this.canvasSize).attr('height', this.canvasSize);

            // WARNING: assumes the raw coordinates have been normalized to [0, 1]
            this.umapScale = d3.scaleLinear()
                .rangeRound([0, this.canvasSize])
                .domain([-0.01, 1.03]);
        }

        if (this.props.coordType==='gridded') {
            this.umapScale = d3.scaleLinear()
                .rangeRound([0, this.canvasSize])
                .domain([0, this.props.gridSize + 1]);

            // the size of the thumbnail in canvas pixels
            this.canvasThumbnailSize = this.umapScale(1) - this.umapScale(0);
        }

        this.updateDerivedConstants();
        const inDotMode = this.props.markerType!=='thumbnails';

        let context = this.shadowCanvas.getContext('2d');

        // set the background to black
        context.fillStyle = 'black';
        context.fillRect(0, 0, this.canvas.width, this.canvas.height);

        // copy the thumbnail images from the tiled thumbnail canvas to the off-screen umap canvas
        if (!inDotMode) {
            this.props.positions.map(position => this.drawThumbnail(context, position));
        }

        // create the SVG thumbnail containers
        let g = this.svg.selectAll('.thumbnail-container')
            .data(this.positions, d => d.cell_line_id);

        const tip = this.tip;
        g.exit().remove();
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
        
        g.select('circle')
            .style('fill', d => this.calcDotColor(d))
            .style('fill-opacity', inDotMode ? 0.9 : 0)
            .style('stroke', d => inDotMode ? chroma(this.calcDotColor(d)).darken(2) : '#999');

            if (this.props.showCaptions) {
                g.append('text')
                    .attr('class', 'thumbnail-text')
                    .attr('x', this.renderedThumbnailSize*this.lastTransform?.k/2 || 20)
                    .attr('y', 20)
                    .text(d => d.target_name);
            } else {
                this.svg.selectAll('text').remove();
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


    updateThumbnailRects(transform) {

        const inDotMode = this.props.markerType!=='thumbnails';
        const scaleX = x => transform.applyX(this.umapScale(x) / this.canvasPixelsPerScreenPixel);
        const scaleY = y => transform.applyY(this.umapScale(y) / this.canvasPixelsPerScreenPixel);

        this.svg.selectAll('g')
            .attr('transform', d => {
                return `translate(${scaleX(d[this.props.coordType][1])}, ${scaleY(d[this.props.coordType][0])})`;
            });

        // try to reduce lag when the user is only dragging and not zooming
        if (transform.k===this.lastTransform?.k) return;
        
        const zoomedThumbnailSize = this.renderedThumbnailSize*transform.k;
        this.svg.selectAll('.thumbnail-circle')
            .attr('r', inDotMode ? 6 : zoomedThumbnailSize/2)
            .attr('cx', zoomedThumbnailSize/2)
            .attr('cy', zoomedThumbnailSize/2)
            .style('stroke-width', inDotMode ? '1.5px' : `${0.7 + transform.k/4}px`);

        if (this.props.showCaptions) {
            this.svg.selectAll('.thumbnail-text')
                .attr('x', zoomedThumbnailSize/2)
                //.attr('opacity', transform.k < 2 ? 0 : 1 - 2/transform.k);
        }
    }


    onUmapZoom(transform) {

        this.hoveredThumbnailDiv.style('visibility', 'hidden');

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
        
        // update the thumbnail rects
        this.updateThumbnailRects(transform);
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