import * as d3 from 'd3';
import React, { Component } from 'react';

import * as constants from './constants.js';
import { columnDefs, filterDefs } from './definitions.js';

import { Radio, RadioGroup, Tab, Tabs } from "@blueprintjs/core";

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

        this.state = {
            columnDefs,     // (each with a .selected key that's toggled by the sidebar)
            filterDefs,     // (the same for both main panel modes)
            filters: [],    // list of active filters
            data: [],       // cell line data to load
            mainPanelMode: 'table', // 'table' or 'plate'
        };

        this.toggleColumn = this.toggleColumn.bind(this);
        this.setMainPanelMode = this.setMainPanelMode.bind(this);
        this.updateFilter = this.updateFilter.bind(this);

    }

    componentDidMount() {
        fetch('http://localhost:5000/polyclonallines')
            .then(result => result.json())
            .then(d => this.setState({data: d}), error => console.log(error));
    }

    toggleColumn(columnId) {
        // toggle the column on/off
    }

    setMainPanelMode(event) {
        // change the main panel mode (either 'table' or 'plate')
        this.setState({mainPanelMode: event.currentTarget.value});
    }

    updateFilter(filterId) {
        // update (or remove) a filter
    }


    render() {

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

                    <div className="w-30"> 
                        <RadioGroup
                            label="Display mode:" 
                            name="mode-group"
                            inline={true}
                            onChange={this.setMainPanelMode} 
                            selectedValue={this.state.mainPanelMode}>
                            <Radio {...this.state} value="table" label="Table"/>
                            <Radio {...this.state} value="plate" label="Plate"/>
                        </RadioGroup>
                    </div>

                    <FilterControls updateFilter={this.updateFilter} filterDefs={this.state.filterDefs}/>
                </div>

                {/* side bar includes:
                    - toggle-able list of table columns to show in the main panel;
                      in plate mode, must be modified so that the entire list is one-hot, 
                      and columns that aren't displayable are grayed out (e.g., guide/repair sequences)
                    - above or below the column list, a small table of common metadata (master cell line, ep date)
                */}
                <div className="fl w-25">
                    <ColumnControls columnDefs={this.state.columnDefs} toggleColumn={this.toggleColumn}/>
                </div>
    
                {/* main panel - cell-line data as either a react-table or a plate-like layout 
                    in table mode, we can display an arbitrary subset of primitive columns (i.e., directly from the database)
                    and derived/summary columns (a FACS plot, a repair-type bar chart, image thumbnail, etc).
                    However, in plate mode, some primitive columns (e.g. sequences) do not make sense to display,
                    and we will need to toggle (in the left sidebar) between the more succinct representations
                    of subsets of the data - e.g., the FACS plots, thumbnail FOVs, existence of monoclonal lines, etc.
                */}
                <div className="fl w-75">
                {this.state.mainPanelMode==="table" ? <DataTable {...this.state}/> : <PlateTable {...this.state}/>}
                </div>
            </div>  

        );
    }
}


export default App;


