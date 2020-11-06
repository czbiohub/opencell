
import * as d3 from 'd3';
import React, { Component } from 'react';
import classNames from 'classnames';

import 'tachyons';
import './Profile.css';


class ButtonGroup extends Component {

    constructor (props) {
        super(props);
    }

    render() {

        const buttons = this.props.values.map((value, ind) => {
            const label = this.props.labels ? this.props.labels[ind] : value;
            return (
                <SimpleButton 
                    active={this.props.activeValue===value} 
                    onClick={d => this.props.disabled ? null : this.props.onClick(value)} 
                    text={label}
                    key={value}/>
            );
        });

        // class names for the button group container
        const className = classNames(
            'simple-button-group', this.props.className, {'o-50': this.props.disabled}
        );

        return (
            <div className={className}>
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
        {'simple-button-active': props.active}
    );

    return <div className={className} onClick={props.onClick}>{props.text}</div>;
}


export default ButtonGroup;