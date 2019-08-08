
const path = require('path');
const webpack = require('webpack');
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
            chunks: ['home'],
        }),

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
        })
    ]

};

module.exports = config;