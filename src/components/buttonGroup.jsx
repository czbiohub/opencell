
import * as d3 from 'd3';
import React, { Component } from 'react';
import classNames from 'classnames';
import { H5, Icon, Popover } from "@blueprintjs/core";

import 'tachyons';
import './buttonGroup.css';

function SimpleButton(props) {
    const className = classNames(
        'pr2',
        'simple-button', 
        {'simple-button-active': props.active}
    );
    return <div className={className} onClick={props.onClick}>{props.text}</div>;
}


export default function ButtonGroup (props) {

    const buttons = props.values.map((value, ind) => {
        const label = props.labels ? props.labels[ind] : value;
        return (
            <SimpleButton 
                active={props.activeValue===value} 
                onClick={d => props.disabled ? null : props.onClick(value)} 
                text={label}
                key={value}
            />
        );
    });

    // class names for the top-level button group container
    const className = classNames(props.className, 'pr2', {'o-50': props.disabled});

    return (
        <div className={className}>
            <div className='flex items-center'>
                <div className='pr1 button-group-label'>{props.label}</div>
                    {props.popoverContent ? (
                    <div>
                        <Popover>
                            <Icon icon='info-sign' iconSize={12} color="#bbb"/>
                            {props.popoverContent}
                        </Popover>
                    </div>
                ) : null }
            </div>
            <div className='flex'>{buttons}</div>
        </div>
    );
}