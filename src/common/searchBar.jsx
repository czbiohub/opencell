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
            query: undefined,
            selectedItem: null,
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
        if (item.target_name==='placeholder') return null;
        return (
            <li className='pa1 pb2 searchbar-item' key={item.target_name} onClick={handleClick}>
                <div className='b'>{`${item.target_name?.toUpperCase()}`}</div>
                <div className='f6 silver' style={{fontWeight: 100}}>{item.protein_name}</div>
            </li>
        );
    };

    renderItemList (itemListProps) {
        // these are the props passed by blueprint to itemListRenderer
        // activeItem:
        // filteredItems: 
        // items:
        // itemsParentRef: ƒ (ref)
        // query: "a"
        // renderItem: ƒ (item, index)
    }

    filterItems (query, items) {
        let targetNameMatches = items.filter(item => {
            return item.target_name.startsWith(query.toLowerCase());
        });
        // if there were no matches, return a dummy item so that onActiveItemChange 
        // is still called and can be used to detect enter keypresses
        if (!targetNameMatches.length) targetNameMatches = [{target_name: '', protein_name: 'Hit enter to see search results'}];
        return targetNameMatches;
    }


    render () {
        return (
            <Suggest
                fill
                minimal
                initialContent={'Search for a gene'}
                items={this.state.loaded ? this.items : []}
                itemListPredicate={this.filterItems}
                itemRenderer={this.renderItem}
                itemListRenderer={undefined} //{this.renderItemList}
                inputValueRenderer={item => item.target_name.toUpperCase()}
                onItemSelect={(item, event) => {
                    if (event.key==='Enter') {
                        this.props.history.push(`/search/${event.target.value}`);
                        this.setState({selectedItem: null});
                        return;
                    }
                    this.props.handleGeneNameSearch(item.target_name);
                    this.setState({selectedItem: item});
                }}
                onActiveItemChange={item => {
                    if (window.event?.key==='Enter') {
                        this.props.history.push(`/search/${window.event.target.value}`);
                    }
                }}
                selectedItem={this.state.selectedItem}
            />
        );
    }
}