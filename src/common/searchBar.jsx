
import * as d3 from 'd3';
import React, { Component } from 'react';
import { Button, MenuItem } from "@blueprintjs/core";
import { Suggest } from "@blueprintjs/select";

import 'tachyons';
import 'react-table/react-table.css';
import "@blueprintjs/core/lib/css/blueprint.css";
import "@blueprintjs/select/lib/css/blueprint-select.css";

import settings from './settings.js';


export default class SearchBar extends Component {

    constructor (props) {
        super(props);

        this.state = {
            loaded: false,
        }

        this.renderItem = this.renderItem.bind(this);
        this.selectItem = this.selectItem.bind(this);
        this.filterItems = this.filterItems.bind(this);
    }

    componentDidMount (props) {
        d3.json(`${settings.apiUrl}/target_names`).then(data => {
            this.items = data;
            this.items.forEach(item => {
                item.target_name = item.target_name.toLowerCase();
                item.protein_name_words = item.protein_name.toLowerCase()
                    .replace(',', '')
                    .replace('-', ' ')
                    .split(' ')
                    .filter(word => word.length > 3);
            });
            this.setState({loaded: true});
        })
    }


    selectItem (item) {
        const items = this.props.selectedItems.concat(item);
        this.props.updateSelectedItems(items);
    }


    renderItem (item, {modifiers, handleClick}) {
        if (!modifiers.matchesPredicate) return null;
        return (
            <li className='pa1 pb2 searchbar-item' key={item.target_name} onClick={handleClick}>
                <div className='b'>{`${item.target_name.toUpperCase()}`}</div>
                <div className='f6 silver' style={{fontWeight: 100}}>{item.protein_name}</div>
            </li>
        );
    };

    filterItems (query, items) {

        query = query.toLowerCase().replace(' ', '');
        const targetNameMatches = items.filter(item => {
            return item.target_name.startsWith(query);
        });
        
        // if there are lots of matching target names, don't search the full protein names
        if (targetNameMatches.length > 25) return targetNameMatches;

        const matchingItems = [];
        items.forEach(item => {
            if (matchingItems.length > 25) return;
            if (item.target_name.startsWith(query)) return;
            if (item.protein_name_words.filter(word => word.startsWith(query)).length) {
                matchingItems.push(item);
            }
        });

        return [...targetNameMatches, ...matchingItems];
    }


    render () {

        return (
            <Suggest
                minimal
                initialContent={'Search for a protein'}
                items={this.state.loaded ? this.items : []}
                itemListPredicate={this.filterItems}
                itemRenderer={this.renderItem}
                inputValueRenderer={item => item.target_name.toUpperCase()}
                onItemSelect={item => this.props.handleGeneNameSearch(item.target_name)}
            />
        );
    }
}