import React, { Component } from 'react';
import ReactTable from 'react-table';

import {cellLineMetadataDefinitions} from './metadataDefinitions.js';

// append gene_name to metadataDefinitions 
const columnDefs = [
    {   
        id: 'gene_name',
        Header: 'Gene name',
        accessor: row => row.metadata?.target_name,
    },
    ...cellLineMetadataDefinitions,
];


export default class CellLineTable extends Component {

    constructor (props) {
        super(props);
        this.state = {};
    }

    render () {
        return (
            <div className='pt3 table-container'>
            <ReactTable 
                defaultPageSize={10}
                showPageSizeOptions={true}
                filterable={true}
                columns={columnDefs}
                data={this.props.cellLines.map(line => {
                    return {...line, isActive: this.props.cellLineId===line.metadata.cell_line_id};
                })}
                getTrProps={(state, rowInfo, column) => {
                    const isActive = rowInfo ? rowInfo.original.isActive : false;
                    return {
                        onClick: () => this.props.onCellLineSelect(rowInfo.original.metadata.cell_line_id),
                        style: {
                            background: isActive ? '#ddd' : null,
                            fontWeight: isActive ? 'bold' : 'normal'
                        }
                    }
                }}
                getPaginationProps={(state, rowInfo, column) => {
                    return {style: {fontSize: 16}}
                }}
                defaultFilterMethod={(filter, row, column) => {
                    // force default filtering to be case-insensitive
                    const id = filter.pivotId || filter.id;
                    const value = filter.value.toLowerCase();
                    return row[id] !== undefined ? String(row[id]).toLowerCase().startsWith(value) : true
                }}
            />
            </div>
        );
    }
}