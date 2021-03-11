import React from 'react';
import { Button, MenuItem, Popover, Icon } from '@blueprintjs/core';
import { Select } from '@blueprintjs/select';
import classNames from 'classnames';


export default function SimpleSelect (props) {

    const items = props.values.map((value, ind) => {
        const label = props.labels ? props.labels[ind] : value;
        return {value, label};
    });

    const activeItem = items.filter(item => item.value===props.activeValue)[0];

    const select = (
        <Select
            filterable={false}
            disabled={props.disabled}
            items={items} 
            activeItem={activeItem}
            onItemSelect={item => props.onClick(item.value)}
            itemRenderer={(item, {modifiers, handleClick}) => {
                return (
                    <MenuItem
                        key={item.value}
                        text={item.label}
                        active={modifiers.active}
                        onClick={handleClick}
                    />
                );
            }}
        >
            <Button 
                className="bp3-button-custom"
                rightIcon="caret-down"
                text={`${activeItem.label}`}
            />
        </Select>
    );

    // class names for the top-level button group container
    const className = classNames(props.className, 'pr2', {'o-50': props.disabled});

    const popover = props.popoverContent ? (
            <Popover>
                <Icon icon='info-sign' iconSize={12} color="#bbb"/>
                {props.popoverContent}
            </Popover>
        ) : null;

    return (
        <div className={className}>
            <div className='flex items-center'>
                <div className='pr1 button-group-label'>{props.label}</div>
                {popover}
            </div>
            {select}
        </div>
    );
}
