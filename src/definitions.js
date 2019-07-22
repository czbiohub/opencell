import * as d3 from 'd3';
import chroma from 'chroma-js';
import React, { Component } from 'react';

import FACSPlot from './facsPlot.jsx';


// style a scalar react-table cell
// (apply a background color and remove the border)
const scalarCellStyle = (colormapName, colormapDomain, accessor) => {

    // colormap instance
    const colormap = chroma.scale(colormapName).domain(colormapDomain).padding([0, .2])

    // this is the `getProps` function expected by react-table
    return (state, rowInfo, column) => {
        
        if (!rowInfo) return {};

        // this is how we get this cell's value
        let value = column.accessor(rowInfo.original);

        // if a custom accessor was provided
        if (accessor) value = accessor(rowInfo.original);
    
        return {
            style: {
                color: "#333",
                background: chroma(colormap(value)).alpha(.5),
                borderBottom: 'none',
                textAlign: 'center',
            }
        }
    }
}

// chroma colormap name for FACS-related scalar columns
// other options: 'OrRd', 'YlGn'
const facsColormapName = 'OrRd';

export const columnDefs = [
    {
        Header: 'Plate ID',
        accessor: 'plate_design_id',
        width: 50,
    },{
        Header: 'Well ID',
        accessor: 'well_id',
        width: 50,
    },{
        Header: 'Line ID',
        accessor: 'cell_line_id',
        width: 50,
    },{
        Header: 'EP date',
        id: 'electroporation_date',
        accessor: d => {
            // hack-ish way to display the date in the form '%Y-%m-%d'
            const date = new Date(d.electroporation_date); 
            return date.toJSON() ? date.toJSON().slice(0, 10) : 'missing date';
        },
    },{
        Header: 'Gene name',
        accessor: 'target_name',
    },{
        Header: 'Gene family',
        accessor: 'target_family',
    },{
        id: 'target_terminus',
        Header: 'Term',
        accessor: 'target_terminus',
        width: 50,
        accessor: row => row.target_terminus[0],
    },{
        Header: 'ENST ID',
        accessor: 'transcript_id',
        width: 150,
    },{
        Header: 'TPM (HEK293)',
        accessor: 'hek_tpm',
        getProps: scalarCellStyle('OrRd', [0, 2000]),
    },{
        Header: 'Protospacer name',
        accessor: 'protospacer_name',
    },{
        Header: 'Protospacer notes',
        accessor: 'protospacer_notes',
    },{
        Header: 'Protospacer sequence',
        accessor: 'protospacer_sequence',
    },{
        Header: 'Template name',
        accessor: 'template_name',
    },{
        Header: 'Template notes',
        accessor: 'template_notes',
    },{
        Header: 'Template sequence',
        accessor: 'template_sequence',
    },{
        id: 'facs_area',
        Header: 'FACS area',
        accessor: row => row.facs_results ? row.facs_results.area : undefined,
        getProps: scalarCellStyle(facsColormapName, [0, 1]),
    },{
        id: 'facs_rel_median_log',
        Header: 'FACS intensity (median)',
        accessor: row => row.facs_results ? row.facs_results.rel_median_log : undefined,
        getProps: scalarCellStyle(facsColormapName, [0, 2]),
    },{
        id: 'facs_rel_percentile99_log',
        Header: 'FACS intensity (max)',
        accessor: row => row.facs_results ? row.facs_results.rel_percentile99_log : undefined,
        getProps: scalarCellStyle(facsColormapName, [0, 3]),
    },{
        id: 'facs_raw_std',
        Header: 'FACS width',
        accessor: row => row.facs_results ? row.facs_results.raw_std : undefined,
        getProps: scalarCellStyle(facsColormapName, [0, 1500]),
    },{
        id: 'facs_plot',
        Header: 'FACS plot',
        accessor: row => row.cell_line_id,
        Cell: row => {
            // note: the 'raw' row is found in `row.original`
            // note: the `key` prop below is required for the cell to re-render
            // when the table rows change (on, e.g., sorting or paging)
            return <FACSPlot 
                key={row.value} 
                cellLineId={row.value}
                data={row.original.facs_histograms}
                width={100}/>
        },
        // to color the background by the area
        //getProps: styleBackgroundColor('OrRd', [0, 1], row => row.facs ? row.facs.area : null),
    },
];


// copy id from accessor
// *** WARNING: this assumes that columnDefs without an id have a string-valued accessor ***
columnDefs.forEach(def => def.id = def.id ? def.id : def.accessor);

// force width to 100 if no width is specified
columnDefs.forEach(def => def.width = def.width ? def.width : 100);


// default selected columns in react-table mode
export const defaultSelectedColumnIds = [
    'plate_design_id', 
    'well_id', 
    'target_name', 
    'target_family', 
    'target_terminus',
    'hek_tpm',
    'facs_area',
    'facs_rel_median_log',
    'facs_rel_percentile99_log',
];


export const columnGroups = [
    {
        name: 'Metadata',
        ids: [
            'plate_design_id', 
            'well_id', 
            'cell_line_id',
            'electroporation_date',
        ],
    },{
        name: 'Target',
        ids: [
            'target_name', 
            'target_family', 
            'target_terminus', 
            'transcript_id', 
            'hek_tpm'
        ],
    },{
        name: 'Crispr design',
        ids: [
            'protospacer_name', 
            'protospacer_notes', 
            'protospacer_sequence',
            'template_name', 
            'template_notes', 
            'template_sequence',
            ''
        ],
    },{
        name: 'FACS',
        ids: [
            'facs_area',
            'facs_rel_median_log',
            'facs_rel_percentile99_log',
            'facs_raw_std',
            'facs_plot',
        ],
    },{
        name: 'Sequencing',
        ids: [],
    },{
        name: 'Imaging',
        ids: [],
    },{
        name: 'Annotations',
        ids: [],
    }
];


// definitions for filters
export const filterDefs = [
    {
        name: 'Plate ID',
        accessor: 'plate_design_id',
        values: [],
    },{
        name: 'Gene family',
        accessor: 'target_family',
        values: [],
    },{
        name: 'FACS score',
        accessor: 'facs_score',
        values: [],
    }
];

