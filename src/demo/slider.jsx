
import * as d3 from 'd3';
import React, { Component } from 'react';

import 'tachyons';
import './Demo.css';


class Slider extends Component {

    constructor (props) {
        super(props);
        this.state = {};
        this.onChange = this.onChange.bind(this);
    }


    onChange(event) {
        this.props.onChange(event.target.value);
    }


    render() {
        return (
            <div className='pr3 pb1'>
                {/* <div className="dib pr2 slider-label">{this.props.label}</div> */}
                <div className="w-100 dib">
                <input 
                    type="range" 
                    className="dib slider" 
                    min={this.props.min} 
                    max={this.props.max}
                    value={this.props.value}
                    onChange={this.onChange}/>
                </div>
            </div>
        );
    }

}

export default Slider;