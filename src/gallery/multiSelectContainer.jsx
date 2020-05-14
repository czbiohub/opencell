
import * as d3 from 'd3';
import React, { Component } from 'react';

import { Button, Radio, RadioGroup, MenuItem, Menu } from "@blueprintjs/core";
import { Select, MultiSelect } from "@blueprintjs/select";

import 'tachyons';
import 'react-table/react-table.css';
import "@blueprintjs/core/lib/css/blueprint.css";




export default class MultiSelectContainer extends Component {

    constructor (props) {
        super(props);

        this.state = {
        }

        this.renderItem = this.renderItem.bind(this);
        this.selectItem = this.selectItem.bind(this);
        this.deselectItem = this.deselectItem.bind(this);
        this.getSelectedItemIndex = this.getSelectedItemIndex.bind(this);
        this.handleItemSelect = this.handleItemSelect.bind(this);
    }

    getSelectedItemIndex(item) {
        return this.props.selectedItems.map(_item => _item.name).indexOf(item.name);
    }

    selectItem (item) {
        const items = this.props.selectedItems.concat(item);
        this.props.updateSelectedItems(items);
    }

    deselectItem (itemIndex) {
        const items = this.props.selectedItems.filter((_, ind) => ind !== itemIndex);
        this.props.updateSelectedItems(items);
    }

    handleItemSelect (item) {
        const index = this.getSelectedItemIndex(item);
        if (index !== -1) {
            this.deselectItem(index);
        } else {
            this.selectItem(item);
        }
    }


    renderItem (item, {modifiers, handleClick}) {
        if (!modifiers.matchesPredicate) return null;
        return (
            <MenuItem
                active={false}
                icon={this.getSelectedItemIndex(item) === -1 ? "blank" : "tick"}
                key={item.name}
                label={null}
                onClick={handleClick}
                text={`${item.name} (${item.num})`}
                shouldDismissPopover={false}
            />
        );
    };


    render () {

        const clearButton = (
            <Button icon="cross" minimal={true} onClick={() => this.props.updateSelectedItems([])}/>
        );

        return (
            <MultiSelect
                fill={true}
                placeholder={''}
                items={this.props.items}
                itemRenderer={this.renderItem}
                onItemSelect={this.handleItemSelect}
                selectedItems={this.props.selectedItems}
                itemPredicate={(query, item) => {
                    return item.name && item.name.toLowerCase().startsWith(query.toLowerCase());
                }}
                tagRenderer={item => <span className="f5">{item.name}</span>}
                tagInputProps={{
                    tagProps: {minimal: true},
                    rightElement: clearButton,
                    onRemove: (tag, index) => {
                        this.deselectItem(index);
                        d3.event.stopPropagation();
                    }
                }}
            />
        );
    }
}