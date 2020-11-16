import React, { useContext } from 'react';
import ReactTable from 'react-table';

import settings from '../common/settings.js';
import {cellLineMetadataDefinitions} from './metadataDefinitions.js';


export default function CellLineTable (props) {
    const modeContext = useContext(settings.ModeContext);

    // append gene_name to metadataDefinitions 
    let columnDefs = [
        {   
            id: 'gene_name',
            Header: 'Gene name',
            accessor: row => row.metadata?.target_name,
        },
        ...cellLineMetadataDefinitions,
    ];

    const hiddenColumnDefIds = ['facs_intensity', 'facs_area', ];
    columnDefs = columnDefs.filter(def => !hiddenColumnDefIds.includes(def.id));

    const publicColumnDefIds = [
        'gene_name', 'protein_name', 'uniprot_id', 'ensg_id',
        'hek_tpm', 'target_terminus', 'protospacer_sequence', 
    ];

    if (modeContext!=='private') {
        columnDefs = columnDefs.filter(def => publicColumnDefIds.includes(def.id));
    }

    return (
        <div className='pt3 table-container'>
        <ReactTable 
            defaultPageSize={props.defaultPageSize || 10}
            showPageSizeOptions={true}
            filterable={true}
            columns={columnDefs}
            data={props.cellLines.sort((a, b) => a.metadata.target_name > b.metadata.target_name ? 1 : -1)}
            getTrProps={(state, rowInfo, column) => {
                const isActive = rowInfo && rowInfo.original.metadata.cell_line_id===props.cellLineId;
                return {
                    onClick: () => props.onCellLineSelect(rowInfo.original.metadata.cell_line_id),
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