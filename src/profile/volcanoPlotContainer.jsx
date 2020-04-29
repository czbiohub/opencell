
import React, { Component } from 'react';
import ButtonGroup from './buttonGroup.jsx';
import VolcanoPlot from './volcanoPlot.jsx';

import 'tachyons';
import './Profile.css';


export default class VolcanoPlotContainer extends Component {


    constructor (props) {

        super(props);
        this.state = {

            // how volcano plot dots are colored: 'Significance' or 'Function'
            labelColor: 'Significance',

            // when to show labels: 'Always', 'Never', 'On zoom'
            showLabels: 'On zoom',

            // whether to reset the zoom 
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
                                label='Label color' 
                                values={['Significance', 'Function']}
                                activeValue={this.state.labelColor}
                                onClick={value => this.setState({labelColor: value})}/>
                        </div>
                        <div className='dib pr4'>
                            <ButtonGroup 
                                label='Show labels' 
                                values={['Always', 'Never', 'On zoom']}
                                activeValue={this.state.showLabels}
                                onClick={value => this.setState({showLabels: value})}/>
                        </div>

                    </div>
                </div>

                {/* volcano plot
                the hack-ish absolute margins here are to better align the svg itself*/}
                <div className="fl w-100 scatterplot-container" style={{marginLeft: -20, marginTop: 10}}>
                    <VolcanoPlot
                        enrichmentAccessor={row => parseFloat(row.enrichment)}
                        pvalueAccessor={row => parseFloat(row.pval)}
                        cellLineId={this.props.cellLineId}
                        changeTarget={this.props.changeTarget}
                        showLabels={this.state.showLabels}
                        resetZoom={this.state.resetZoom}
                        labelColor={this.state.labelColor}
                    />
                </div>
                <div className='fr dib'>
                    <div 
                        className='f6 simple-button' 
                        onClick={() => this.setState({resetZoom: !this.state.resetZoom})}>
                        {'Reset zoom'}
                    </div>
                </div>

            </div>

        );

    }

}

