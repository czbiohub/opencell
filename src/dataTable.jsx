
import * as d3 from 'd3';
import React, { Component } from 'react';
import ReactTable from 'react-table';


class DataTable extends Component {

    constructor (props) {
        super(props);
        this.state = {};
    }


    render() {
        if (!this.props.data) return null;

        // columnDefs of selected columns
        const columnDefs = this.props.columnDefs.filter(def => this.props.selectedColumns.includes(def.id));
        
        // filter data
        let data = [...this.props.data];
        for (const [accessor, value] of Object.entries(this.props.filterValues)) {
            if (value==='all') continue;
            data = data.filter(d => d[accessor]===value);
        }

        return <ReactTable 
            data={data}
            filterable={true}
            columns={columnDefs}
        />
    }
}


export default DataTable;