
import * as d3 from 'd3';
import React, { Component } from 'react';
import classNames from 'classnames';

import 'tachyons';
import './Profile.css';


class ButtonGroup extends Component {

    constructor (props) {
        super(props);
        this.state = {};
    }

    
    render() {

        const buttons = this.props.values.map(value => {
            return (
                <SimpleButton 
                    active={this.props.activeValue===value} 
                    onClick={d => this.props.onClick(value)} 
                    text={value}
                    key={value}/>
            );
        });

        return (
            <div className='simple-button-group'>
                <div className='simple-button-group-label'>{this.props.label}</div>
                {buttons}
            </div>
        );
    }
}
    

function SimpleButton(props) {

    const className = classNames(
        'pr2',
        'simple-button', 
        {'simple-button-active': props.active});

    return <div className={className} onClick={props.onClick}>{props.text}</div>;
}


export default ButtonGroup;