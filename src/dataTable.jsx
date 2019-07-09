
import * as d3 from 'd3';
import React, { Component } from 'react';
import ReactTable from 'react-table';


class DataTable extends Component {

    constructor (props) {
        super(props);
        this.state = {};
    }


    render() {

        const columnDefs = this.props.columnDefs.filter(def => this.props.selectedColumns.includes(def.id));

        if (!this.props.data) return null;
        
        return <ReactTable 
            filterable={true}
            columns={columnDefs} 
            data={this.props.data}/>

    }
}


export default DataTable;