
const path = require('path');
const webpack = require('webpack');

const CopyPlugin = require('copy-webpack-plugin');
const HtmlWebpackPlugin = require('html-webpack-plugin')
const MiniCssExtractPlugin = require("mini-css-extract-plugin");

const config = {

    entry: {
        home: './src/home/index.jsx',
        dashboard: './src/dashboard/index.jsx',
        demo: './src/demo/index.jsx',
    },

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

        new HtmlWebpackPlugin({
            title: 'Home',
            template: './static/index.html',
            filename: './index.html',
            chunks: ['home']
        }),
        new HtmlWebpackPlugin({
            title: 'Dashboard',
            template: './static/index.html',
            filename: './dashboard/index.html',
            chunks: ['dashboard']
        }),
        new HtmlWebpackPlugin({
            title: 'Demo',
            template: './static/index.html',
            filename: './demo/index.html',
            chunks: ['demo']
        }),
        new MiniCssExtractPlugin({
            filename: '[chunkhash]-bundle.css',
            chunks: ['home'],
        }),
    
        // note that the `to` path is relative to the output path defined above
        new CopyPlugin([{from: 'static/logos', to: 'demo/logos'}]),
        new CopyPlugin([{from: 'static/threejs-textures', to: 'demo/threejs-textures'}])
    ]

};

module.exports = config;