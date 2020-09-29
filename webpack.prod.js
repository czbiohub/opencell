const path = require('path');
const webpack = require('webpack');
const merge = require('webpack-merge');
const common = require('./webpack.common.js');

const config = {
    mode: 'production',
    output: {
        path: path.resolve(__dirname, 'dist'),
        filename: '[chunkhash]-bundle.js',
        publicPath: '/',
    },
    plugins: [
        new webpack.DefinePlugin({API_URL: '`http://${window.location.host}/api`'})
    ]
};

module.exports = merge(common, config);