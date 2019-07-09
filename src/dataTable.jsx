
import * as d3 from 'd3';
import React, { Component } from 'react';
import ReactTable from 'react-table';


class DataTable extends Component {

    constructor (props) {
        super(props);
        this.state = {};
    }


    render() {

        return <ReactTable 
            filterable={true}
            columns={this.props.columnDefs} 
            data={this.props.data}/>

    }
}


export default DataTable;