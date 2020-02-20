
const path = require('path');
const webpack = require('webpack');
const merge = require('webpack-merge');
const common = require('./webpack.common.js');

const config = {

    mode: 'development',

    output: {
        path: path.resolve(__dirname, 'dev'),
        filename: '[name].bundle.js',
        publicPath: '/',
    },

    devServer: {
        contentBase: './static',
    }
};

module.exports = merge(common, config);