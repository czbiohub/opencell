
import * as d3 from 'd3';
import * as THREE from 'three';

import React, { Component } from 'react';

// imports required for volume renderings from three.js examples
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { VolumeRenderShader1 } from 'three/examples/jsm/shaders/VolumeShader.js';

import 'tachyons';
import './Profile.css';


export default class VolumeViewer extends Component {

    constructor (props) {

        super(props);
        this.state = {};

        this.initViewer = this.initViewer.bind(this);
        this.renderVolume = this.renderVolume.bind(this);
        this.updateUniforms = this.updateUniforms.bind(this);

        this.maybeCreateMaterial = this.maybeCreateMaterial.bind(this);
        this.createTexture = this.createTexture.bind(this);

        this.getMinMax = this.getMinMax.bind(this);
        this.getVolume = this.getVolume.bind(this);

    }


    getMinMax() {
        const minMaxs = {
            'DAPI': [this.props.dapiMin, this.props.dapiMax],
            'GFP': [this.props.gfpMin, this.props.gfpMax],
            'Both': [this.props.gfpMin, this.props.gfpMax],
        };
        return minMaxs[this.props.localizationChannel].map(val => val/100);
    }


    getVolume() {
        // WARNING: the channel indicies here must match those found in App.componentDidMount
        const inds = {
            'DAPI': 0,
            'GFP': 1,
            'Both': 1,
        };

        return this.props.volumes[inds[this.props.localizationChannel]];
    }
    

    componentDidMount() {
        // data-independent threejs initialization
        this.initViewer();

        // if the stacks (as PNG tiles) have loaded
        if (this.props.stacksLoaded) {
            this.maybeCreateMaterial();
            this.updateUniforms(['u_data', 'u_clim']);
        }
    }


    componentDidUpdate(prevProps) {

        // HACK: if the app hasn't loaded, the user has changed targets,
        // which means we are waiting for the z-stacks to load,
        // and this method will fire again once they do (and stacksLoaded is set to true)
        // Here, we go around react and use a state-independent flag to remember this fact
        // in order to reload the texture when this method is called again after the stacks have loaded
        if (!this.props.stacksLoaded) {
            this.reloadTexture = true;
            return;
        }

        // only need to create the material once (populates this.material)
        this.maybeCreateMaterial();

        // if the target or channel has changed, re-create the texture
        if (this.reloadTexture || (prevProps.localizationChannel!==this.props.localizationChannel)) {
            this.reloadTexture = false;
            this.updateUniforms(['u_data', 'u_clim']);

        // if channel is unchanged, assume that only the min or max were changed
        } else {
            this.updateUniforms(['u_clim']);
        }
    }

    
    updateUniforms(fields) {

        if (fields.includes('u_data')) {
            this.material_gray.uniforms['u_data'].value = this.createTexture(this.getVolume());
        }
        if (fields.includes('u_clim')) {
            this.material_gray.uniforms['u_clim'].value.set(...this.getMinMax());
        }

        // the blue material for two-color mode
        if (fields.includes('u_data')) {
            this.material_blue.uniforms['u_data'].value = this.createTexture(this.props.volumes[0]);
        }
        if (fields.includes('u_clim')) {
            this.material_blue.uniforms['u_clim'].value.set(this.props.dapiMin/100, this.props.dapiMax/100);
        }

        // only show the blue mesh (DAPI) in two-color mode
        this.mesh_blue.visible = this.props.localizationChannel==='Both';

        this.renderVolume();
    }


    initViewer() {

        // set the height of the canvas to the container's width
        const containerAspect = 1;
        const width = 600; //d3.select(this.node).style('width');
        const height = 600; //width * containerAspect;

        this.scene = new THREE.Scene();
        const canvas = d3.select(this.node)
                         .append('canvas')
                         .style('margin', 'auto')
                         .style('display', 'block')
                         .node();
                        
        const context = canvas.getContext('webgl2');
        this.webGLRenderer = new THREE.WebGLRenderer({canvas, context});
        this.webGLRenderer.setPixelRatio(window.devicePixelRatio);

        // note that this (re)sizes the canvas element
        // TODO: move this up into the d3.select line?
        this.webGLRenderer.setSize(width, height);

        // copied from 'webgl2_materials_texture3d' example
        // TODO: figure out how these coordinates work
        const h = 600; // frustum height

        const aspect = 1/containerAspect; //window.innerWidth / window.innerHeight;
        this.camera = new THREE.OrthographicCamera(-h * aspect/2, h*aspect/2, h/2, -h/2, 1, 1000);

        // hard-coded empirically-selected default position
        // looking directly down in the image
        this.camera.position.set(300, 290, 500);

        // copied from the example - because 'z is up'
        this.camera.up.set(0, 0, 1);

        // copied from the example
        // TODO: set the coordinates in target.set using the dimensions of the data
        const controls = new OrbitControls(this.camera, this.webGLRenderer.domElement);
        controls.addEventListener('change', () => {
            //console.log(this.camera.position);
            this.renderVolume();
        });
        controls.target.set(h/2, h/2, 32);
        controls.minZoom = 0.5;
        controls.maxZoom = 4;
        controls.update();
        
    }


    createTexture (volume) {
        
        const shape = [volume.xLength, volume.yLength, volume.zLength];
        const texture = new THREE.DataTexture3D(volume.data, ...shape);

        // for numpy 'uint8' type
        texture.type = THREE.UnsignedByteType;

        // copied from 'webgl2_materials_texture3d' example
        texture.format = THREE.RedFormat;
        texture.minFilter = texture.magFilter = THREE.LinearFilter;
        texture.unpackAlignment = 1;
        texture.needsUpdate = true;

        // attempt to change scaling in z by using a repeat value
        // of less than one in the z dimension
        // (this is a recommended approach to scaling textures in 2D)
        // this has no effect, possibly because texture.repeat is a 2D vector
        // even for DataTexture3D (which might be a bug)
        //texture.repeat = new THREE.Vector3(1, 1, .5);
        return texture;
    }


    maybeCreateMaterial () {

        // hack-ish way to determine whether this method has already been called once
        if (this.material_gray) return;

        const volume = this.getVolume();

        const shape = [volume.xLength, volume.yLength, volume.zLength];
        const center = shape.map(val => val/2 - .5);

        const colormaps = {
            viridis: new THREE.TextureLoader().load('threejs-textures/cm_viridis.png', this.renderVolume),
            blue: new THREE.TextureLoader().load('threejs-textures/cm_blue_a_v2.png', this.renderVolume),
            gray: new THREE.TextureLoader().load('threejs-textures/cm_gray_a.png', this.renderVolume)
        };

        // copied from the threejs example
        let uniforms = THREE.UniformsUtils.clone(VolumeRenderShader1.uniforms);

        // hard-coded uniforms ('u_data' and 'u_clim' are set/updated separately)
        uniforms['u_size'].value.set(...shape);
        uniforms['u_cmdata'].value = colormaps.gray;

        // 0 for MIP, 1 for ISO
        uniforms['u_renderstyle'].value = 0;

        // hard-coded threshold - only used for ISO mode
        uniforms['u_renderthreshold'].value = 30;
        
        // material for single-channel mode (grayscale colormap)
        this.material_gray = new THREE.ShaderMaterial({
            uniforms: uniforms,
            vertexShader: VolumeRenderShader1.vertexShader,
            fragmentShader: VolumeRenderShader1.fragmentShader,
            side: THREE.BackSide,

            // TODO: think about this: if `transparent` is true here, then the blue material 
            // is completely invisible - need to add alpha channel to the gray colormap?
            transparent: true,
        });

        // semi-transparent blue-colormapped material for two-color mode 
        uniforms = THREE.UniformsUtils.clone(VolumeRenderShader1.uniforms);
        uniforms['u_size'].value.set(...shape);
        uniforms['u_cmdata'].value = colormaps.blue;
        uniforms['u_renderstyle'].value = 0;
        uniforms['u_renderthreshold'].value = 30;
        
        this.material_blue = new THREE.ShaderMaterial({
            uniforms: uniforms,
            vertexShader: VolumeRenderShader1.vertexShader,
            fragmentShader: VolumeRenderShader1.fragmentShader,
            side: THREE.BackSide,

            // this option is required for the alpha values in the colormap
            // to be 'applied' in the rendering
            transparent: true,
        });

        const geometry = new THREE.BoxBufferGeometry(...shape);
        geometry.translate(...center);
        
        // attempt to change scaling in z by changing geometry.scale 
        // this leads to the top slice being repeated in the depth dimension
        // (presumably this is behavior specified by DataTexture3D.wrapR)
        //geometry.scale(1, 1, 2);

        this.mesh_blue = new THREE.Mesh(geometry, this.material_blue);
        this.mesh_gray = new THREE.Mesh(geometry, this.material_gray);

        // attempt to change scaling in z by changing mesh.scale 
        // this also does not work as expected; 
        // the scaling is applied only far away from the camera
        //this.mesh_blue.scale.set(1, 1, 2);
        //this.mesh_gray.scale.set(1, 1, 2);

        const group = new THREE.Group();

        // note: order of addition here doesn't (seem to) matter
        group.add(this.mesh_blue);
        group.add(this.mesh_gray);
        
        // changing group.scale has the same effect as mesh.scale
        //group.scale.set(1, 1, 2);

        this.scene.add(group);

    }


    renderVolume() {
        this.webGLRenderer.render(this.scene, this.camera);
    }


    render() {
        return (
            <div 
                ref={node => this.node = node}
                style={{backgroundColor: 'black'}}
            />
        );
    }
}
