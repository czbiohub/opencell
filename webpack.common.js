
const path = require('path');
const CopyPlugin = require('copy-webpack-plugin');
const HtmlWebpackPlugin = require('html-webpack-plugin')
const MiniCssExtractPlugin = require("mini-css-extract-plugin");

const config = {

    entry: {
        index: './src/index.jsx',
    },

    module: {
        rules: [
            {
                test: /\.(js|jsx)$/,
                exclude: /node_modules/,
                use: ['babel-loader']
            },{
                test: /\.(scss|css)$/,
                use: [
                    MiniCssExtractPlugin.loader,
                    'css-loader',
                    'sass-loader',
                ]
            }
        ]
    },

    resolve: {
        extensions: ['*', '.js', '.jsx']
    },

    plugins: [
        new MiniCssExtractPlugin({
            filename: '[chunkhash]-bundle.css',
            chunks: ['index'],
        }),

        new HtmlWebpackPlugin({
            title: 'OpenCell',
            template: './static/index.html',
            filename: './index.html',
            chunks: ['index']
        }),
    
        // note that the `to` path is relative to the output path defined in the prod config
        new CopyPlugin({
            patterns: [
                {from: 'static/images', to: 'assets/images'},
                {from: 'static/favicons', to: 'assets/favicons'},
                {from: 'static/threejs-textures', to: 'assets/threejs-textures'},
            ]
        })
    ]
};

module.exports = config;