
import React, { Component } from 'react';
import chroma from 'chroma-js';

import ButtonGroup from './buttonGroup.jsx';
import MassSpecScatterPlot from './massSpecScatterPlot.jsx';

import 'tachyons';
import './Profile.css';


export default class MassSpecPlotContainer extends Component {

    constructor (props) {
        super(props);
        this.state = {

            // either 'Volcano' or 'Stoichiometry'
            plotMode: 'Volcano',

            // how scatterplot dots are colored: either 'Significance' or 'Function'
            plotColorMode: 'Significance',

            // when to show dot captions: 'Always', 'Never', 'On zoom'
            showPlotCaptions: 'On zoom',

            // whether to reset the plot's zoom/pan transform
            // this is a hack: volcanoPlot just listens for changes to this value
            resetPlotZoom: false,
        };
    }

    render () {
        return (
            <div>
                {/* display controls */}
                <div className="flex pt3 pb2">

                    {/* Top row - scatterplot controls */}
                    <div className='w-100 flex flex-wrap items-end'>
                        <div className='pr2'>
                            <ButtonGroup 
                                label='Plot mode' 
                                values={['Volcano', 'Stoichiometry']}
                                activeValue={this.state.plotMode}
                                onClick={value => this.setState({plotMode: value})}/>
                        </div>
                        <div className='pr2'>
                            <ButtonGroup 
                                label='Show labels' 
                                values={['Always', 'Never', 'On zoom']}
                                activeValue={this.state.showPlotCaptions}
                                onClick={value => this.setState({showPlotCaptions: value})}/>
                        </div>
                        <div 
                            className='f6 simple-button' 
                            onClick={() => this.setState({resetPlotZoom: !this.state.resetPlotZoom})}>
                            {'Reset zoom'}
                        </div>
                    </div>
                </div>

                {/* volcano plot
                the hack-ish absolute margins here are to better align the svg itself*/}
                <div className="w-100 pl4 pr5 scatterplot-container" style={{marginLeft: -20}}>
                    <MassSpecScatterPlot
                        mode={this.state.plotMode}
                        pulldownId={this.props.pulldownId}
                        handleGeneNameSearch={this.props.handleGeneNameSearch}
                        showCaptions={this.state.showPlotCaptions}
                        resetZoom={this.state.resetPlotZoom}
                        colorMode={this.state.plotColorMode}
                    />
                </div>
            </div>

        );

    }

}

