
import * as d3 from 'd3';
import React, { Component } from 'react';

import 'tachyons';
import './umap.css';


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
        this.canvasRenderedSize = 800;

        // the native size of each thumbnail (in the JPG of tiled thumbnails)
        this.nativeThumbnailSize = 100;

        // HACK: hard-coded paths to the tiled thumbnails JPG and the thumbnail UMAP positions
        this.thumbnailTileUrl = '/assets/images/2020-12-28_all-thumbnails-100px.jpg';
        this.thumbnailMetadataUrl = '/assets/images/2020-12-28_thumbnail-positions.json';

        this.getCoordName = this.getCoordName.bind(this);
        this.maybeLoadData = this.maybeLoadData.bind(this);
        this.drawThumbnails = this.drawThumbnails.bind(this);
        this.addCanvasEventHandlers = this.addCanvasEventHandlers.bind(this);
        this.onZoom = this.onZoom.bind(this);
        this.onCanvasMouseMove = this.onCanvasMouseMove.bind(this);
    }


    componentDidMount() {

        const container = d3.select(this.node);

        this.canvasRenderedSize = d3.max([window.innerHeight, window.innerWidth]) - 0;

        // the visible canvas
        const canvas = d3.select(this.node)
            .append('canvas')
            .attr('class', 'umap-canvas')
            .attr('width', this.canvasSize)
            .attr('height', this.canvasSize)
            .style('width', `${this.canvasRenderedSize}px`)
            .style('height', `${this.canvasRenderedSize}px`);

        this.canvas = canvas.node();

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

        // load the JPG image of tiled thumbnails and the JSON array of thumbnail positions
        this.maybeLoadData();
    }


    componentDidUpdate (prevProps) {
        this.drawThumbnails();
        this.addCanvasEventHandlers();
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

            // HACK: here we load the JSON thumbnail positions within the img onload callback
            d3.json(this.thumbnailMetadataUrl).then(data => {
                this.thumbnailMetadata = data;
                this.normalizeCoords(data, 'umap_pos');
                this.setState({loaded: true});
            });

        }
        img.src = this.thumbnailTileUrl;
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


    getCoordName () {
        if (this.props.coordType==='raw') return 'umap_pos';
        if (this.props.coordType==='grid') return 'umap_grid_pos';
    }


    drawThumbnails () {

        if (this.props.coordType==='raw') {

            // hard-coded thumbnail size (since in raw coords, it is not constrained by the grid)
            this.canvasThumbnailSize = 100;

            // resize the canvas to avoid downsampling the thumbnails
            this.canvasSize = 4000;
            d3.select(this.canvas).attr('width', this.canvasSize).attr('height', this.canvasSize);
            d3.select(this.shadowCanvas).attr('width', this.canvasSize).attr('height', this.canvasSize);

            // WARNING: assumes the raw coordinates have been normalized to [0, 1]
            this.umapScale = d3.scaleLinear().rangeRound([0, this.canvasSize]).domain([-0.01, 1.03]);
        }

        if (this.props.coordType==='grid') {
            this.umapScale = d3.scaleLinear()
                .rangeRound([0, this.canvasSize])
                .domain([0, d3.max(this.thumbnailMetadata, d => d3.max(d[this.getCoordName()])) + 1]);
            this.canvasThumbnailSize = this.umapScale(1) - this.umapScale(0);
        }

        const context = this.shadowCanvas.getContext('2d');

        // set the background to black
        context.fillStyle = 'black';
        context.fillRect(0, 0, this.canvas.width, this.canvas.height);

        this.thumbnailMetadata.map(thumbnail => {
            context.drawImage(
                this.tiledThumbnailCanvas,
                
                // source x, y (note the col, row order is reversed)
                thumbnail.tile_pos[1] * this.nativeThumbnailSize, 
                thumbnail.tile_pos[0] * this.nativeThumbnailSize,
                
                // source width, height 
                this.nativeThumbnailSize, this.nativeThumbnailSize,
                
                // destination x, y
                this.umapScale(thumbnail[this.getCoordName()][1]), 
                this.umapScale(thumbnail[this.getCoordName()][0]), 

                // destination width, height
                this.canvasThumbnailSize, this.canvasThumbnailSize,
            );
        });
    }


    addCanvasEventHandlers () {

        // highlight the hovered thumbnail
        const onCanvasMouseMove = this.onCanvasMouseMove;
        d3.select(this.canvas)
            .on('mousemove', function () { 
                onCanvasMouseMove(d3.mouse(this), d3.zoomTransform(this));
            })
            .on('mouseout', () => this.hoveredThumbnailDiv.style('visibility', 'hidden'));

        // add zooming to the canvas
        const zoom = d3.zoom()
            .scaleExtent([0.5, 4])
            .on('zoom', () => this.onZoom(d3.event.transform));
        d3.select(this.canvas).call(zoom);

        // set the initial transform so that the full UMAP fits and is horizontally centered
        const initialTransform = d3.zoomIdentity.translate(window.innerWidth/4, 20).scale(0.6);
        d3.select(this.canvas).call(zoom.transform, initialTransform);

    }


    onCanvasMouseMove (mousePosition, transform) {
        // Draw a div around the thumbnail the mouse is hovered over
        //
        // mousePosition : the current mouse position on the canvas (in client pixel coordinates)
        // transform : the current d3.zoomTransform applied to the canvas

        const canvasPixelsPerScreenPixel = this.canvasSize/this.canvasRenderedSize;

        // thumbnail size in UMAP coordinates
        const umapThumbnailSize = this.umapScale.invert(this.canvasThumbnailSize) - this.umapScale.domain()[0];

        // thumbnail size in client screen pixels
        const renderedThumbnailSize = this.canvasThumbnailSize/canvasPixelsPerScreenPixel;

        // the mouse position in rendered canvas pixel coordinates 
        // (that is, relative to the 800x800 rendered canvas)
        const mouseRenderedPosition = transform.invert(mousePosition);

        // the mouse position in UMAP coordinates (either a grid cell or the normalized position)
        let mouseUmapPosition = [
            this.umapScale.invert(mouseRenderedPosition[0] * canvasPixelsPerScreenPixel), 
            this.umapScale.invert(mouseRenderedPosition[1] * canvasPixelsPerScreenPixel)
        ];

        // clamp the mouse position to the grid coordinates
        if (this.props.coordType==='grid') {
            mouseUmapPosition = mouseUmapPosition.map(val => Math.floor(val));
        }

        // move the mouse position to the top left of the thumbnail,
        // because this (and not the thumbnail center) is what the umap positions correspond to
        if (this.props.coordType==='raw') {
            mouseUmapPosition = mouseUmapPosition.map(val => val - umapThumbnailSize/2);
        }

        const coordName = this.getCoordName();
        const dists = this.thumbnailMetadata.map(
            d => (d[coordName][1] - mouseUmapPosition[0])**2 + (d[coordName][0] - mouseUmapPosition[1])**2
        );
        const minDist = d3.min(dists);

        // if the mouse is not over a thumbnail
        if (Math.sqrt(minDist) > (umapThumbnailSize/2)) {
            this.hoveredThumbnailDiv.style('visibility', 'hidden');
            return;
        }

        // the thumbnail the mouse is hovering over
        const thumbnail = this.thumbnailMetadata[dists.indexOf(minDist)];

        // the top-left corner of the hovered thumbnail in client pixel coordinates
        const thumbnailPosition = transform.apply([
            this.umapScale(thumbnail[coordName][1]) / canvasPixelsPerScreenPixel,
            this.umapScale(thumbnail[coordName][0]) / canvasPixelsPerScreenPixel,
        ]);

        // update the position of the hover div
        this.hoveredThumbnailDiv
            .style('width', `${renderedThumbnailSize * transform.k}px`)
            .style('height', `${renderedThumbnailSize * transform.k}px`)
            .style('left', `${thumbnailPosition[0]}px`)
            .style('top', `${thumbnailPosition[1]}px`)
            .style('visibility', 'visible')
            .text(thumbnail?.target_name);
    }


    onZoom(transform) {

        this.hoveredThumbnailDiv.style('visibility', 'hidden');

        // the ratio of canvas pixels to screen pixels
        // (this is needed because the transform coordinates are in screen pixels, 
        // but the canvas translation is done in canvas pixels)
        const canvasPixelsPerScreenPixel = this.canvasSize/this.canvasRenderedSize;

        // clear the visible canvas
        const context = this.canvas.getContext('2d');
        context.save();
        context.clearRect(0, 0, this.canvas.width, this.canvas.height);

        // apply the transform
        context.translate(
            transform.x*canvasPixelsPerScreenPixel, transform.y*canvasPixelsPerScreenPixel
        );
        context.scale(transform.k, transform.k);

        // re-draw the image (without smoothing, to show the true pixels when zoomed in)
        // context.imageSmoothingEnabled = false;
        context.drawImage(this.shadowCanvas, 0, 0, this.canvas.width, this.canvas.height);
        context.restore();

        this.transform = transform;
    }


    render() {
        return (
             <div ref={node => this.node = node} style={{position: 'relative'}}/> 
        );
    }
}