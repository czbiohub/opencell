
import React, { Component } from 'react';
import chroma from 'chroma-js';

import ButtonGroup from '../buttonGroup.jsx';
import MassSpecHeatmap from './massSpecHeatmap.jsx';

import 'tachyons';
import '../Profile.css';


export default class MassSpecHeatmapContainer extends Component {

    constructor (props) {
        super(props);
        this.state = {

            // the hit property used to color the heatmap: pvals, enrichment, or interaction stoich
            plotColorMode: 'pval',
            
            // whether to reset the heatmap pan/zoom state (currently unused)
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
                                label='Color by' 
                                values={['pval', 'enrichment', 'interaction_stoich', 'abundance_stoich']}
                                labels={['P-values', 'Enrichment', 'Interaction stoich', 'Abundance stoich']}
                                activeValue={this.state.plotColorMode}
                                onClick={value => this.setState({plotColorMode: value})}/>
                        </div>
                        <div 
                            className='f6 simple-button' 
                            onClick={() => this.setState({resetPlotZoom: !this.state.resetPlotZoom})}>
                            {'Reset zoom'}
                        </div>
                    </div>
                </div>

                <div className="w-100 cluster-heatmap-container">
                    <MassSpecHeatmap
                        cellLineId={this.props.cellLineId}
                        handleGeneNameSearch={this.props.handleGeneNameSearch}
                        resetZoom={this.state.resetPlotZoom}
                        colorMode={this.state.plotColorMode}
                    />
                </div>
            </div>

        );

    }

}

