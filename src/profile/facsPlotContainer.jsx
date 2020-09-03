
import React, { Component } from 'react';
import ButtonGroup from './buttonGroup.jsx';
import FACSPlot from '../common/facsPlot.jsx';

import 'tachyons';
import './Profile.css';


export default class FacsPlotContainer extends Component {


    constructor (props) {

        super(props);
        this.state = {
    
            // whether to plot the GFP-positive population
            facsShowGFP: 'On',

            // whether to show the annotations (median/max intensity etc)
            facsShowAnnotations: 'On',

        };
    }

    render () {

        return (
            <div>

                {/* FACS plot controls */}
                <div className='fl w-100 pt3'>
                    <div className='dib pr4'>
                        <ButtonGroup 
                            label='GFP-positive population' 
                            values={['On', 'Off']}
                            activeValue={this.state.facsShowGFP}
                            onClick={value => this.setState({facsShowGFP: value})}/>
                    </div>
                    {/* <div className='dib pr4'>
                        <ButtonGroup 
                            label='Annotations' 
                            values={['On', 'Off']}
                            activeValue={this.state.facsShowAnnotations}
                            onClick={value => this.setState({facsShowAnnotations: value})}/>
                    </div> */}
                </div>

                {/* FACS plot itself*/}
                <div 
                    className="fl w-100 facs-plot-container">
                    <FACSPlot 
                        width={400}
                        height={300}
                        isSparkline={false}
                        cellLineId={this.props.cellLineId}
                        showGFP={this.state.facsShowGFP==='On'}/>
                </div>
            </div>
        );
    }
}
