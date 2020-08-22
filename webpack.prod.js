const path = require('path');
const webpack = require('webpack');
const merge = require('webpack-merge');
const common = require('./webpack.common.js');

const config = {
    output: {
        path: path.resolve(__dirname, 'dist'),
        filename: '[chunkhash]-bundle.js',
        publicPath: '/',
    },
};

module.exports = merge(common, config);