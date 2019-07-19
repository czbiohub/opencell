
import * as d3 from 'd3';
import React, { Component } from 'react';
import ReactDOM from 'react-dom';

import FACSPlot from './facsPlot.jsx';


const measureElement = element => {
    const DOMNode = ReactDOM.findDOMNode(element);
    return {
        width: DOMNode.offsetWidth,
        height: DOMNode.offsetHeight,
    };
}


function renderWell(row) {

    const data = row.column.accessor(row.original).data;
    if (!data) return null;
    return (
        <FACSPlot 
            key={data.cell_line_id} 
            cellLineId={data.cell_line_id}
            width={60}/>
    );

}




class PlateTable extends Component {

    constructor (props) {

        super(props);
        this.state = {};

        const rowIds = "ABCDEFGH".split("");
        const colIds = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map(d => String(d).padStart(2, '0'));

        // construct as platemap of the form
        // {rowId: 'A', wells: [{wellId: 'A01'}, {wellId: 'A02'}, ...]}
        // {rowId: 'B', wells: [{wellId: 'B01'}, {wellId: 'B02'}, ...]}}
        this.platemap = rowIds.map(rowId => {
            const wells = colIds.map(colId => {
                return ({'wellId': `${rowId}${colId}`});
            });
            return {rowId, wells};
        });
    }


    componentDidMount () {}


    render() {

        if (!this.props.data) return null;

        // selected columnDef
        const columnDef = this.props.columnDefs.filter(def => def.id===this.props.selectedColumnIds[0])[0];
        
        // filter data
        let data = [...this.props.data];
        for (const [accessor, value] of Object.entries(this.props.filterValues)) {
            if (value==='all') continue;
            data = data.filter(d => d[accessor]===value);
        }

        // copy the data for each well into the platemap
        this.platemap.forEach(row => {
            row.wells.forEach(well => {
                let wellData = data.filter(d => d.well_id===well.wellId);
                well['data'] = wellData ? wellData[0] : null;
            });
        });

        return (

            <div id='plate-table-container' className=''>
                {this.platemap.map(row => (
                    <PlateRow key={row.rowId} wells={row.wells} columnDef={columnDef}/>
                ))}
            </div>

        );
    }
}


class PlateRow extends Component {

    constructor (props) {
        super(props);
        this.state = {};
    }

    render () {
        return (
            <div className='plate-table-row'>
                {this.props.wells.map(well => (<PlateWell key={well.wellId} data={well.data} {...this.props}/>))}
            </div>
        );
    }
}


class PlateWell extends Component {

    constructor (props) {
        super(props);

        this.state = {
            height: 0,
        };

        this.wellSize = 70;
    }

    componentDidMount () {
        // set the height to the width so that the wells are square
        this.container && this.setState({height: measureElement(this.container).width});
    }

    render () {

        // the accessor can be a string (a key) or a user-defined function
        const fnOrKey = this.props.columnDef.accessor;
        const accessor = typeof fnOrKey === 'string' ? d => d[fnOrKey] : fnOrKey;
        
        // wrap the accessor with a check that the data exists
        const safeAccessor = data => data ? accessor(data) : undefined;

        let value = this.props.columnDef.Cell ? this.props.columnDef.Cell({value}) : safeAccessor(this.props.data);

        let cellStyle = {background: ''};
        if (this.props.columnDef.getProps) {
            // execute getProps, designed for react-table, by mocking the arguments passed by react-table
            cellStyle = this.props.columnDef.getProps(
                {}, {original: this.props.data}, {accessor: safeAccessor}).style;
        }

        return (
            <div 
                className='plate-table-well' 
                ref={ref => this.container = ref}
                style={{height: this.state.height, background: cellStyle.background}}>
                {value ? value : 'ND'}
            </div>
        );
    }
}

export default PlateTable;