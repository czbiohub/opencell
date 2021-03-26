const path = require('path');
const webpack = require('webpack');
const merge = require('webpack-merge');
const common = require('./webpack.common.js');

module.exports = env => {
    const config = {
        mode: 'production',
        output: {
            path: path.resolve(__dirname, 'dist'),
            filename: '[chunkhash]-bundle.js',
            publicPath: '/',
        },
        plugins: [
            new webpack.DefinePlugin({APP_MODE: JSON.stringify(env.appMode)}),
            new webpack.DefinePlugin({APP_SERVER: JSON.stringify(env.appServer)}),
            new webpack.DefinePlugin({API_URL: '`${window.location.host}/api`'}),
            new webpack.DefinePlugin({GA_TRACKING_ID: JSON.stringify('UA-181046024-1')}),
        ]
    };
    return merge(common, config);
}
