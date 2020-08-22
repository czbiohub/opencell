
const path = require('path');
const CopyPlugin = require('copy-webpack-plugin');
const HtmlWebpackPlugin = require('html-webpack-plugin')
const MiniCssExtractPlugin = require("mini-css-extract-plugin");

const config = {

    entry: {
        home: './src/index.jsx',
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
                    'css-loader' // why is this here?
                ]
            }
        ]
    },

    resolve: {
        extensions: ['*', '.js', '.jsx']
    },

    plugins: [
        new MiniCssExtractPlugin({
            filename: '[name]-bundle.css',
            chunks: ['home'],
        }),

        new HtmlWebpackPlugin({
            title: 'Home',
            template: './static/index.html',
            filename: './index.html',
            chunks: ['home']
        }),
    
        // note that the `to` path is relative to the output path defined in the prod config
        new CopyPlugin([{from: 'static/logos', to: 'profile/logos'}]),
        new CopyPlugin([{from: 'static/threejs-textures', to: 'profile/threejs-textures'}]),
        new CopyPlugin([{from: 'static/threejs-textures', to: 'gallery/threejs-textures'}])
    ]

};

module.exports = config;