import React, { Component, useState  } from 'react';
import classNames from 'classnames';
import { H5, Icon, Popover } from "@blueprintjs/core";


function SectionHeader (props) {
    return (
        <div className="flex items-center bb b--black-10">
            <div className="pr2 f3 section-header">{props.title}</div>
            <Popover>
                <Icon icon='info-sign' iconSize={14} color="#aaa"/>
                {props.popoverContent}
            </Popover>
        </div>
    );
}


function Tab (props) {
    return props.component;
}


function Tabs (props) {

    const [activeTabId, setActiveTabId] = useState(props.activeTabId);

    const tabs = props.children.map(child => {
        const className = classNames(
            'f4', 'mr5', 'section-header', {'section-header-active': child.props.id===activeTabId}
        );
        return (
            <div key={child.props.id} className={className} onClick={() => setActiveTabId(child.props.id)}>
                {child.props.title}
            </div>
        );
    });

    const ActiveTab = props.children.filter(child => child.props.id===activeTabId)[0];
    return (
        <div>
            <div className="flex bb b--black-10">
                {tabs}
            </div>
            {ActiveTab}
        </div>
    );
}


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
    Tab,
    Tabs,
    SectionHeader,
    MetadataItem,
    MetadataContainer,
};