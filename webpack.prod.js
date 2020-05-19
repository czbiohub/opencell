const path = require('path');
const webpack = require('webpack');
const merge = require('webpack-merge');
const common = require('./webpack.common.js');
const CopyPlugin = require('copy-webpack-plugin');

const config = {

    output: {
        path: path.resolve(__dirname, 'dist'),
        filename: '[chunkhash]-bundle.js',
    },

    plugins: [
        // note that the `to` path is relative to the output path defined above
        new CopyPlugin([{from: 'static/logos', to: 'profile/logos'}]),
        new CopyPlugin([{from: 'static/threejs-textures', to: 'profile/threejs-textures'}]),
        new CopyPlugin([{from: 'static/threejs-textures', to: 'gallery/threejs-textures'}]),
    ]
};

module.exports = merge(common, config);