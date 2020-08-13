
const path = require('path');
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
        })
    ]

};

module.exports = config;