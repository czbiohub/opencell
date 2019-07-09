import * as d3 from 'd3';
import React, { Component } from 'react';

import * as constants from './constants.js';
import { columnDefs, columnGroups, filterDefs, defaultSelectedColumns} from './definitions.js';

import { Button, Radio, RadioGroup, MenuItem } from "@blueprintjs/core";
import { Select } from "@blueprintjs/select";

import DataTable from './dataTable.jsx';
import PlateTable from './plateTable.jsx';

import DisplayControls from './displayControls.jsx';
import ColumnControls from './columnControls.jsx';
import FilterControls from './filterControls.jsx';

import 'react-table/react-table.css';
import 'tachyons';

import "@blueprintjs/core/lib/css/blueprint.css";
// import "blueprintjs/select/lib/css/blueprint-select.css";


import './App.css';

// debugging
let _APP = {d3};


class App extends Component {

    constructor (props) {
        super(props);

        const filterValues = {};
        filterDefs.forEach(def => filterValues[def.accessor] = 'all');

        this.state = {
            data: null,               // cell line data tobe loaded
            mainPanelMode: 'table',   // 'table' or 'plate'
            filterValues,
            filterDefs,
            selectedColumns: defaultSelectedColumns,
        };

        this.toggleColumn = this.toggleColumn.bind(this);
        this.setMainPanelMode = this.setMainPanelMode.bind(this);
        this.updateCategoricalFilter = this.updateCategoricalFilter.bind(this);

    }

    componentDidMount() {
        fetch('http://localhost:5000/polyclonallines')
            .then(result => result.json())
            .then(data => {
                this.setState({data});
                this.calcCategoricalFilterValues(data);
            }, 
            error => console.log(error));
    }

    calcCategoricalFilterValues(data) {
        // calculate unique values for each categorical filter
        // (called only once, after cell line data loads)
        // HACK: we directly mutate the filterDefs object
        const filterDefs = this.state.filterDefs;
        filterDefs.forEach(def => {
            def.values = [...new Set(data.map(d => d[def.accessor]))].sort();
            def.values.push('all');
        });
        this.setState({filterDefs});
    }

    toggleColumn(columnId) {
        // add or remove the column from the list of selected columns
        const selectedColumns = this.state.selectedColumns;
        if (selectedColumns.includes(columnId)) {
            selectedColumns.splice(selectedColumns.indexOf(columnId), 1);
        } else {
            selectedColumns.push(columnId);
        }
        this.setState({selectedColumns});
    }

    setMainPanelMode(event) {
        // change the main panel mode (either 'table' or 'plate')
        this.setState({mainPanelMode: event.currentTarget.value});
    }

    updateCategoricalFilter(def, value) {
        // update a categorical filter
        const filterValues = this.state.filterValues;
        filterValues[def.accessor] = value;
        this.setState({filterValues});

    }



    render() {

        function renderItem (item, {handleClick, modifiers}) {
            //if (!modifiers.matchesPredicate) return null;
            return (
                <MenuItem
                    active={modifiers.active}
                    key={item}
                    label={item}
                    text={item}
                    onClick={handleClick}
                />
            );
        };

        function filterItem(query, item) {
            // filter function for blueprint Select components
            return String(item).toLowerCase().indexOf(query.toLowerCase()) >= 0;
        }

        let mainPanel;
        if (this.state.mainPanelMode==="table") {
            mainPanel = <DataTable 
                data={this.state.data}
                columnDefs={columnDefs} 
                columnGroups={columnGroups} 
                selectedColumns={this.state.selectedColumns}/>
        } else {
            mainPanel = <PlateTable {...this.state}/>
        }

        return (
            // main container
            <div className="fl w-100 pl3 pt3">

                {/* header */}
                <div className="bb b--black-20">
                    <div className="f3 b">Pipeline dashboard</div>
                </div> 

                {/* top menu bar
                    - buttons and sliders to filter cell lines by various variables, including
                      categorical: plate_id (one-hot only), gene family, annotated localization
                      continuous: FACS intensity/score, HDR frequency, expression level
                    - 
                */}
                <div className="fl w-100 pt2">

                    <div className="dib"> 
                        <RadioGroup
                            label="Display mode:" 
                            name="mode-group"
                            inline={true}
                            onChange={this.setMainPanelMode} 
                            selectedValue={this.state.mainPanelMode}>
                            <Radio value="table" label="Table"/>
                            <Radio value="plate" label="Plate"/>
                        </RadioGroup>
                    </div>

                    {filterDefs.map((def, index) => (
                        <div className="dib pr3">
                            <span>{def.name}: </span>
                            <Select 
                                key={index} 
                                items={def.values} 
                                itemRenderer={renderItem} 
                                itemPredicate={filterItem}
                                onItemSelect={(value) => this.updateCategoricalFilter(def, value)}
                            >
                                <Button 
                                    className="bp3-button-custom"
                                    text={this.state.filterValues[def.accessor]}
                                    rightIcon="double-caret-vertical"/>
                            </Select>
                        </div>
                    ))}
                        
                </div>


                {/* side bar includes:
                    - toggle-able list of table columns to show in the main panel;
                      in plate mode, must be modified so that the entire list is one-hot, 
                      and columns that aren't displayable are grayed out (e.g., guide/repair sequences)
                    - above or below the column list, a small table of common metadata (master cell line, ep date)
                */}
                <div className="fl w-20">
                    <ColumnControls 
                        columnDefs={columnDefs}
                        columnGroups={columnGroups} 
                        selectedColumns={this.state.selectedColumns}
                        toggleColumn={this.toggleColumn}/>
                </div>
    
                {/* main panel - cell-line data as either a react-table or a plate-like layout 
                    in table mode, we can display an arbitrary subset of primitive columns (i.e., directly from the database)
                    and derived/summary columns (a FACS plot, a repair-type bar chart, image thumbnail, etc).
                    However, in plate mode, some primitive columns (e.g. sequences) do not make sense to display,
                    and we will need to toggle (in the left sidebar) between the more succinct representations
                    of subsets of the data - e.g., the FACS plots, thumbnail FOVs, existence of monoclonal lines, etc.
                */}
                <div className="fl w-75">{mainPanel}</div>
            </div>  

        );
    }
}


export default App;


