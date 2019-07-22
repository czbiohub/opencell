
import * as d3 from 'd3';
import React, { Component } from 'react';
import ReactDOM from 'react-dom';

import FACSPlot from './facsPlot.jsx';


const measureElement = element => {

    if (!element) return undefined;

    const node = ReactDOM.findDOMNode(element);
    return {
        width: node.offsetWidth,
        height: node.offsetHeight,
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
        const colIds = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map(
            d => String(d).padStart(2, '0'));

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
        const columnDef = this.props.columnDefs.filter(
            def => def.id===this.props.selectedColumnId)[0];
        
        // apply the active categorical filters
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
                {this.props.wells.map(well => (
                    <PlateWell 
                        key={well.wellId} 
                        wellId={well.wellId} 
                        data={well.data} 
                        {...this.props}/>
                ))}
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

        this.hardCodedWidth = 70;
    }

    componentDidMount () {

        // set the height to the width so that the well divs are rendered as squares
        const renderedWidth = measureElement(this.container).width;
        const width = this.hardCodedWidth;

        this.container && this.setState({
            width,
            height: width,
        });
    }

    render () {

        // the accessor can be a string (a key) or a user-defined function
        const functionOrString = this.props.columnDef.accessor;
        const accessor = typeof functionOrString === 'string' ? d => d[functionOrString] : functionOrString;
        
        // wrap the accessor with a check that the data exists
        const safeAccessor = data => data ? accessor(data) : undefined;
        const value = safeAccessor(this.props.data);

        // HACK-ish: if it exists, execute getProps, designed for react-table, 
        // by mocking the arguments passed to it by react-table
        let cellStyle = {background: ''};
        if (this.props.columnDef.getProps) {
            cellStyle = this.props.columnDef.getProps(
                {}, {original: this.props.data}, {accessor: safeAccessor}
            ).style;
        }

        let content;

        // HACK: hard-coded exception for facs_plot
        if (this.props.columnDef.id==='facs_plot') {
            content = this.props.data && (
                <div style={{paddingTop: 10}}>
                    <FACSPlot 
                        width={this.state.width}
                        data={this.props.data.facs_histograms}/>
                </div>
            );

        // assume scalar content
        } else {
            content = (
                <div className='plate-table-well-content'>
                    {value ? value : 'ND'}
                </div>
            );
            
        }

        return (
            <div 
                className='plate-table-well' 
                ref={ref => this.container = ref}
                style={{
                    // height: this.state.height, 
                    // width: this.state.width, 
                    ...cellStyle,
                }}
            >
                <div className='w-100 plate-table-well-header'>
                    {`${this.props.data ? this.props.data.target_name : 'ND'}`}
                </div>
                {content}
            </div>
        );
    }
}

export default PlateTable;