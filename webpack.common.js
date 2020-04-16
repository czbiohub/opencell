
const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin')
const MiniCssExtractPlugin = require("mini-css-extract-plugin");

const config = {

    entry: {
        home: './src/home/index.jsx',
        dashboard: './src/dashboard/index.jsx',
        profile: './src/profile/index.jsx',
        microscopy: './src/microscopy/index.jsx'
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
            title: 'Profile',
            template: './static/index.html',
            filename: './profile/index.html',
            chunks: ['profile']
        }),
        new HtmlWebpackPlugin({
            title: 'Microscopy',
            template: './static/index.html',
            filename: './microscopy/index.html',
            chunks: ['microscopy']
        })
    ]

};

module.exports = config;