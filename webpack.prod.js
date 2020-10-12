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
            new webpack.DefinePlugin({API_URL: '`http://${window.location.host}/api`'}),
            new webpack.DefinePlugin({DEFAULT_APP_MODE: JSON.stringify(env.appMode)})
        ]
    };
    return merge(common, config);
}