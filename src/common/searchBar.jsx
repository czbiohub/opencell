
import * as d3 from 'd3';
import React, { Component } from 'react';
import { Button, MenuItem } from "@blueprintjs/core";
import { Suggest } from "@blueprintjs/select";

import 'tachyons';
import 'react-table/react-table.css';
import "@blueprintjs/core/lib/css/blueprint.css";

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
        this.handleItemSelect = this.handleItemSelect.bind(this);
    }

    componentDidMount (props) {
        d3.json(`${settings.apiUrl}/target_names`).then(data => {
            this.items = data;
            this.items.forEach(item => {
                item.target_name = item.target_name.toLowerCase();
                item.protein_name_words = item.protein_name.toLowerCase()
                    .replace(',', '')
                    .replace('-', ' ')
                    .split(' ');
            });
            this.setState({loaded: true});
        })
    }


    selectItem (item) {
        const items = this.props.selectedItems.concat(item);
        this.props.updateSelectedItems(items);
    }


    handleItemSelect (item) {
        console.log(item);
    }


    renderItem (item, {modifiers, handleClick}) {
        if (!modifiers.matchesPredicate) return null;
        return (
            <div className='pa1 pb2 searchbar-item' key={item.target_name} onClick={handleClick}>
                <div className='b'>{`${item.target_name.toUpperCase()}`}</div>
                <div className='f6 silver' style={{fontWeight: 100}}>{item.protein_name}</div>
            </div>
        );
    };

    filterItems (query, items) {

        query = query.toLowerCase().replace(' ', '');
        const targetNameMatches = items.filter(item => {
            return item.target_name.startsWith(query);
        });
        if (targetNameMatches.length > 10) return targetNameMatches.slice(0, 10);

        const matchingItems = [];
        items.forEach(item => {
            if (matchingItems.length > 10) return;
            if (item.protein_name_words.indexOf(query) > -1) matchingItems.push(item);
        });

        return [...targetNameMatches, ...matchingItems.slice(0, 10)];
    }


    render () {

        return (
            <Suggest
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