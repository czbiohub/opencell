
import React, { Component } from 'react';
import chroma from 'chroma-js';

import ButtonGroup from './buttonGroup.jsx';
import MassSpecScatterPlot from './volcanoPlot.jsx';

import 'tachyons';
import './Profile.css';


// const sigModeLegendItems = [
//     {
//         color: chroma(this.sigModeDotColors.bait),
//         text: '● Selected protein',
//     },{
//        color: chroma(this.sigModeDotColors.sigHit).alpha(1),
//        text: '● Significant hits',
//     },{
//        color: chroma(this.sigModeDotColors.notSigHit).alpha(1),
//        text: '● Non-significant hits',
//     },{
//        color: chroma(this.sigModeDotColors.notSigHit).darken(2).alpha(1),
//        text: '- - -  5% FDR curve',
//     }
// ];



export default class VolcanoPlotContainer extends Component {

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
            resetZoom: false,
        };
    }

    render () {
        return (
            <div>
                {/* display controls */}
                <div className="pt3 pb2">

                    {/* Top row - scatterplot controls */}
                    <div className='fl w-100 pb3'>
                        <div className='dib pr4'>
                            <ButtonGroup 
                                label='Plot mode' 
                                values={['Volcano', 'Stoichiometry']}
                                activeValue={this.state.plotMode}
                                onClick={value => this.setState({plotMode: value})}/>
                        </div>
                        <div className='dib pr4'>
                            <ButtonGroup 
                                label='Show labels' 
                                values={['Always', 'Never', 'On zoom']}
                                activeValue={this.state.showPlotCaptions}
                                onClick={value => this.setState({showPlotCaptions: value})}/>
                        </div>

                    </div>
                </div>

                {/* volcano plot
                the hack-ish absolute margins here are to better align the svg itself*/}
                <div className="fl w-100 scatterplot-container" style={{marginLeft: -20, marginTop: 10}}>
                    <MassSpecScatterPlot
                        mode={this.state.plotMode}
                        cellLineId={this.props.cellLineId}
                        changeTarget={this.props.changeTarget}
                        showCaptions={this.state.showPlotCaptions}
                        resetZoom={this.state.resetPlotZoom}
                        colorMode={this.state.plotColorMode}
                    />
                </div>
                <div className='fr dib'>
                    <div 
                        className='f6 simple-button' 
                        onClick={() => this.setState({resetPlotZoom: !this.state.resetPlotZoom})}>
                        {'Reset zoom'}
                    </div>
                </div>
            </div>

        );

    }

}

