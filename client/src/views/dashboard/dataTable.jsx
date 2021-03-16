
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
        const columnDefs = this.props.columnDefs.filter(def => this.props.selectedColumnIds.includes(def.id));
        
        // filter data
        let data = [...this.props.data];
        for (const [accessor, value] of Object.entries(this.props.filterValues)) {
            if (value==='all') continue;
            data = data.filter(d => d[accessor]===value);
        }

        // the getTdProps is required to vertically center cell text
        // all other approaches to vertically centering introduce a margin,
        // which leaves white sprace if the cells have a non-white background color
        return (
            <ReactTable 
                className='dashboard-table'
                data={data}
                filterable={true}
                columns={columnDefs}
                getTdProps={() => ({
                    style: {
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'center',
                        borderBottom: '1px solid #ddd',
                    }
                })}
            />
        );
    }
}


export default DataTable;