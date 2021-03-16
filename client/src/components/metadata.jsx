import React, { Component, useState  } from 'react';
import classNames from 'classnames';

import './metadata.css';

function MetadataItem (props) {
    return (
        <div className={props.className}>
            <strong className={`f${props.scale}`}>{props.value || 'NA'}</strong>
            <abbr className={`f${props.scale + 1}`} title='units description'>
                {props.units}
            </abbr>
            <div className={`f${props.scale + 2} metadata-item-label`}>
                {props.label}
            </div>
        </div>
    );
}


function MetadataContainer (props) {

    if (!props.data) return null;

    const className = classNames(
        'metadata-item',
        {
            'pb2 flex-0-0': props.orientation==='row',
            'pt2': props.orientation==='column',
        }
    );

    const metadataItems = props.definitions.map(def => {
        return (
            <MetadataItem
                key={def.id}
                scale={props.scale}
                className={className}
                value={def.accessor(props.data)}
                label={def.Header}
                units={def.units}
            />
        );
    });

    return (
        <div
            className={`flex flex-wrap ${props.className}`} 
            style={{flexDirection: props.orientation}}
        >
            {metadataItems}
        </div>
    );
}


export {
    MetadataItem,
    MetadataContainer,
};