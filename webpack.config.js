const path = require('path');

module.exports = {
  target: 'node',
  entry: './src/extension.ts',
  output: {
    path: path.resolve(__dirname, 'out'),
    filename: 'extension.js',
    libraryTarget: 'commonjs2',
    devtoolModuleFilenameTemplate: '../[resource-path]'
  },
  externals: {
    vscode: 'commonjs vscode',
    // 外部化这些模块以减小打包体积
    axios: 'commonjs axios',
    dotenv: 'commonjs dotenv'
  },
  resolve: {
    extensions: ['.ts', '.js']
  },
  module: {
    rules: [
      {
        test: /\.ts$/,
        exclude: /node_modules/,
        use: [
          {
            loader: 'ts-loader',
            options: {
              compilerOptions: {
                module: 'es6'
              }
            }
          }
        ]
      }
    ]
  },
  optimization: {
    minimize: true
  },
  devtool: 'nosources-source-map',
  mode: 'production'
};