
const path = require('path');
const webpack = require('webpack');

const CopyPlugin = require('copy-webpack-plugin');
const HtmlWebpackPlugin = require('html-webpack-plugin')
const MiniCssExtractPlugin = require("mini-css-extract-plugin");

const config = {

    entry: [
        './src/index.jsx'
    ],

    module: {
        rules: [
            {
                test: /\.(js|jsx)$/,
                exclude: /node_modules/,
                use: ['babel-loader']
            },{
                test: /\.css$/,
                use: [
                    MiniCssExtractPlugin.loader,
                    'css-loader'
                ]
            }
        ]
    },

    resolve: {
        extensions: ['*', '.js', '.jsx']
    },

    output: {
        path: path.resolve(__dirname, 'prod'),
        filename: '[chunkhash]-bundle.js',
    },

    plugins: [
        new HtmlWebpackPlugin({template: './static/index.html'}),
        new MiniCssExtractPlugin({filename: '[chunkhash]-bundle.css'}),

        // note that the `to` path is relative to the output path defined above
        new CopyPlugin([{ from: 'static/images', to: 'images' }])
    ]

};

module.exports = config;