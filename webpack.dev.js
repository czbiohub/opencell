
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
        new webpack.DefinePlugin({API_URL: JSON.stringify('http://localhost:5000')}),
        new webpack.DefinePlugin({DEFAULT_APP_MODE: JSON.stringify('private')})
    ]
};

module.exports = merge(common, config);