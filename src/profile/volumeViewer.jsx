
import * as d3 from 'd3';
import * as THREE from 'three';

import React, { Component } from 'react';

import settings from '../common/settings.js';

// imports required for volume renderings from three.js examples
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { VolumeRenderShader1 } from './VolumeShader.js';

import 'tachyons';
import './Profile.css';


export default class VolumeViewer extends Component {

    constructor (props) {
        super(props);
        this.state = {};

        this.reloadTexture = true;
        this.userHasMovedCamera = false;

        this.initViewer = this.initViewer.bind(this);
        this.renderVolume = this.renderVolume.bind(this);
        this.updateUniforms = this.updateUniforms.bind(this);
        this.updateCameraPosition = this.updateCameraPosition.bind(this);
        this.maybeCreateMaterial = this.maybeCreateMaterial.bind(this);
        this.createTexture = this.createTexture.bind(this);

        this.getMinMax = this.getMinMax.bind(this);
        this.getVolume = this.getVolume.bind(this);
    }


    getMinMax(channel) {

        // the keys here must match the labels of the 'channel' buttons in viewerContainer
        const minMaxs = {
            '405': [this.props.min405/100, this.props.max405/100, this.props.gamma405],
            '488': [this.props.min488/100, this.props.max488/100, this.props.gamma488],
        };
        minMaxs['Both'] = minMaxs['488'];
        return minMaxs[channel];
    }


    getVolume(channel) {
        const inds = {
            '405': 0,
            '488': 1,
            'Both': 1,
        };
        return this.props.volumes[inds[channel]];
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

        if (this.props.shouldResetZoom) {
            this.userHasMovedCamera = false;
            this.props.didResetZoom();
        }

        // only need to create the material once (populates this.material)
        this.maybeCreateMaterial();

        // if the target or channel has changed, re-create the texture
        if (this.reloadTexture || (prevProps.channel!==this.props.channel)) {
            this.reloadTexture = false;
            this.updateUniforms(['u_data', 'u_clim']);

        // if channel is unchanged, assume that only the min or max were changed
        } else {
            this.updateUniforms(['u_clim']);
        }

        // another hack - we keep track of whether the user has moved the camera
        // with a piece of react-independent state to prevent resetting the camera position
        // whenever the component updates (.e.g, when channel or display settings are changed)
        if (!this.userHasMovedCamera) this.updateCameraPosition();

    }

    componentWillUnmount() {
        this.props.setCameraPosition({
            x: this.controls.target.x, 
            y: this.controls.target.y
        });
        this.props.setCameraZoom(this.camera.zoom);
    }

    
    updateUniforms(fields) {

        if (fields.includes('u_data')) {
            this.material_gray.uniforms['u_data'].value = this.createTexture(
                this.getVolume(this.props.channel)
            );
            this.material_blue.uniforms['u_data'].value = this.createTexture(
                this.getVolume('405')
            );
        }

        if (fields.includes('u_clim')) {
            this.material_gray.uniforms['u_clim'].value.set(...this.getMinMax(this.props.channel));
            this.material_blue.uniforms['u_clim'].value.set(...this.getMinMax('405'));
        }

        // the blue mesh (with the 405 channel) is hidden except in two-color mode
        this.mesh_blue.visible = this.props.channel==='Both';
        this.renderVolume();
    }


    updateCameraPosition() {
        // update the xy position and zoom of the camera
        this.camera.rotation.set(0, 0, 0);
        this.camera.position.set(this.props.cameraPosition.x, this.props.cameraPosition.y, 500);
        this.camera.zoom = this.props.cameraZoom;
        this.camera.updateProjectionMatrix();

        // the controls must orbit around the current position of the camera
        this.controls.target.set(this.camera.position.x, this.camera.position.y, 32);
        this.controls.update();        
    }


    initViewer() {

        // hard-coded canvas size
        const width = 600;
        const height = 600;
        const aspect = width/height;

        this.scene = new THREE.Scene();
        const canvas = d3.select(this.node)
            .append('canvas')
            .style('margin', 'auto')
            .style('display', 'block')
            .node();
    
        const context = canvas.getContext('webgl2');
        this.webGLRenderer = new THREE.WebGLRenderer({canvas, context});
        this.webGLRenderer.setPixelRatio(window.devicePixelRatio);

        // note that this resizes the canvas element
        this.webGLRenderer.setSize(width, height);

        // copied from the 'webgl2_materials_texture3d' example
        const camera = new THREE.OrthographicCamera(
            -height*aspect/2, height*aspect/2, height/2, -height/2, 1, 1000
        );

        // copied from the example ('because z is up')
        camera.up.set(0, 0, 1);

        // set the initial camera position to looking straight down on the volume
        camera.rotation.set(0, 0, 0);
        camera.position.set(width/2, height/2, 500);
        camera.updateProjectionMatrix();

        const controls = new OrbitControls(camera, this.webGLRenderer.domElement);
        controls.target.set(width/2, height/2, 32);
        controls.minZoom = 0.5;
        controls.maxZoom = 8;
        controls.update();

        controls.addEventListener('change', () => {
            this.userHasMovedCamera = true;
            this.renderVolume();
        });

        this.camera = camera;
        this.controls = controls;
    }


    createTexture (volume) {
        
        const shape = [volume.xLength, volume.yLength, volume.zLength];
        const texture = new THREE.DataTexture3D(volume.data, ...shape);

        // for numpy 'uint8' type
        texture.type = THREE.UnsignedByteType;

        // copied from the 'webgl2_materials_texture3d' example
        texture.format = THREE.RedFormat;
        texture.minFilter = texture.magFilter = THREE.LinearFilter;
        texture.unpackAlignment = 1;
        texture.needsUpdate = true;
        return texture;
    }


    maybeCreateMaterial () {

        // hack-ish way to determine whether this method has already been called once
        if (this.material_gray) return;

        const volume = this.getVolume(this.props.channel);

        const shape = [volume.xLength, volume.yLength, volume.zLength];
        const center = shape.map(val => val/2 - .5);

        const colormaps = {
            viridis: new THREE.TextureLoader().load(
                'threejs-textures/cm_viridis.png', this.renderVolume
            ),
            blue: new THREE.TextureLoader().load(
                'threejs-textures/cm_blue_a_v2.png', this.renderVolume
            ),
            gray: new THREE.TextureLoader().load(
                'threejs-textures/cm_gray_a.png', this.renderVolume
            )
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
        
        // grayscale material for single-channel mode
        this.material_gray = new THREE.ShaderMaterial({
            uniforms: uniforms,
            vertexShader: VolumeRenderShader1.vertexShader,
            fragmentShader: VolumeRenderShader1.fragmentShader,
            side: THREE.BackSide,
            transparent: true,
        });

        // semi-transparent blue-colored material for two-color mode 
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

            // setting transparent to true is required for the alpha values in the colormap
            // to be applied in the rendering
            transparent: true,
        });

        const geometry = new THREE.BoxBufferGeometry(...shape);
        geometry.translate(...center);

        this.mesh_blue = new THREE.Mesh(geometry, this.material_blue);
        this.mesh_gray = new THREE.Mesh(geometry, this.material_gray);

        // note: order of addition here doesn't seem to matter
        const group = new THREE.Group();
        group.add(this.mesh_blue);
        group.add(this.mesh_gray);
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
