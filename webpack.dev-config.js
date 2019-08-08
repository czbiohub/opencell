
const path = require('path');
const webpack = require('webpack');
const HtmlWebpackPlugin = require('html-webpack-plugin')
const MiniCssExtractPlugin = require("mini-css-extract-plugin");

const config = {

    entry: {
        app: './src/appIndex.jsx',
        dashboard: './src/dashboardIndex.jsx'
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

    output: {
        path: path.resolve(__dirname, 'dev'),
        filename: '[name].bundle.js',
        publicPath: '/',
    },

    devServer: {
        contentBase: './static',
    },

    plugins: [
        new MiniCssExtractPlugin({
            filename: '[name].bundle.css',
            chunks: ['app'],
        }),

        new HtmlWebpackPlugin({
            title: 'Home',
            template: './static/index.html',
            filename: './dev/index.html',
            chunks: ['app']
        }),
        new HtmlWebpackPlugin({
            title: 'Dashboard',
            template: './static/index.html',
            filename: './dev/dashboard/index.html',
            chunks: ['dashboard']
        })
    ]

};

module.exports = config;