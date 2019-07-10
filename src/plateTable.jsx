
import * as d3 from 'd3';
import React, { Component } from 'react';
import ReactTable from 'react-table';
import { ReactTableDefaults } from 'react-table';


const rows = "abcdefgh".split("");
const cols = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map(d => String(d));


function renderCell(row) {
    return (
        <div
            style={{
            width: '50px',
            height: '50px',
            backgroundColor: '#dadada',
            borderRadius: '2px'
            }}
        >{row.value}</div>
    );
}


class PlateTable extends Component {

    constructor (props) {
        super(props);
        this.state = {};

        this.columnDefs = cols.map(col => {
            return {
                Header: col,
                accessor: col,
                Cell: renderCell,
            }
        });

        this.data = rows.map(row => {
            const d = {}
            cols.map(col => d[col] = `${row.toUpperCase()}${col.padStart(2, '0')}`);
            return d;
        });
    }

    componentDidMount () {

    }

    render() {
        return (
            <ReactTable
                data={this.data}
                columns={this.columnDefs}
                column={{...ReactTableDefaults.column, minWidth: 20}}
                showPagination={false}
                defaultPageSize={8}
                sortable={false}
                style={{textAlign: 'center'}}
            />
        );
    }
}


export default PlateTable;