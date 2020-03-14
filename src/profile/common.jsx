import React, { Component } from 'react';
import classNames from 'classnames';


function SectionHeader (props) {
    return (
        <div className="bb b--black-10">
            <div className="f3 section-header">{props.title}</div>
        </div>
    );
}


function MetadataItem(props) {
    return (
        <div className={props.className}>
            <strong className={`f${props.scale}`}>{props.value}</strong>
            <abbr className={`f${props.scale + 1}`} title='units description'>{props.units}</abbr>
            <div className={`f${props.scale + 2} header-metadata-item-label`}>{props.label}</div>
        </div>
    );
}


function MetadataContainer (props) {

    if (!props.data) return null;

    const className = classNames(
        'header-metadata-item',
        {
            'flex-0-0': props.orientation==='row',
            'pt2': props.orientation==='column'
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
        <div className={`flex ${props.className}`} style={{flexDirection: props.orientation}}>
            {metadataItems}
        </div>
    );
}


export {
    SectionHeader,
    MetadataContainer,
};