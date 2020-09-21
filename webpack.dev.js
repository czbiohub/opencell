
const path = require('path');
const webpack = require('webpack');
const merge = require('webpack-merge');
const common = require('./webpack.common.js');

const config = {

    mode: 'development',

    output: {
        path: path.resolve(__dirname, 'static'),
        filename: '[name].bundle.js',
        publicPath: '/',
    },

    devServer: {
        contentBase: path.resolve(__dirname, 'static'),

        // prevent page reloads
        historyApiFallback: true
    },

    plugins: [
        new webpack.DefinePlugin({API_URL: '`http://localhost:5000`'})
    ]
};

module.exports = merge(common, config);