import { Button } from '@blueprintjs/core';
import * as d3 from 'd3';
import React, { useState, useContext, useEffect } from 'react';
import ReactTable from 'react-table';

import * as utils from '../utils/utils.js';
import './massSpecTableContainer.scss';


const safeLog10 = value => {
    // special method to calculate the log of the abundance and interaction stoichiometries,
    // because these values can be zero or null, and Math.log10(null) yields `-Infinity`
    // (this line below works because Math.log10(undefined) is NaN)
    return Math.log10(value || undefined)
}

const columnDefs = [
    {
        id: 'bait_gene_name',
        Header: 'Bait',
        accessor: row => row.bait_name,
    },{
        id: 'prey_gene_name',
        Header: 'Prey',
        accessor: row => row.prey_name,
    },{
        id: 'pval_minus_log10',
        Header: 'P-value (-log10)',
        accessor: row => parseFloat(row.pval?.toFixed(2)),
    },{
        id: 'relative_enrichment',
        Header: 'Relative enrichment',
        accessor: row => parseFloat(row.enrichment?.toFixed(2)),
    },{
        id: 'abundance_stoich_log10',
        Header: 'Cellular abundance stoichiometry (log10)',
        accessor: row => parseFloat(safeLog10(row.abundance_stoich).toFixed(2)),
    },{
        id: 'interaction_stoich_log10',
        Header: 'Interaction stoichiometry (log10)',
        accessor: row => parseFloat(safeLog10(row.interaction_stoich).toFixed(2)),
    },{
        id: 'cluster_id',
        Header: 'Cluster ID',
        accessor: row => row.cluster_id || 'None',
    },{
        id: 'core_complex_id',
        Header: 'Core complex ID',
        accessor: row => row.subcluster_id || 'None',
    },
];

// wrap accessors to coerce all values to strings
columnDefs.forEach(def => {
    const accessor = def.accessor;
    def.accessor = row => String(accessor(row));
});

const constructTableData = nodes => {
    // create the array of JSON objects for the table of interactors

    let rows = nodes.map(node => node.data);
    const baitName = rows.filter(row => row.type==='bait')[0].uniprot_gene_names[0];

    // set the 'bait' and 'prey' names
    rows.forEach(row => {
        const rowName = row.uniprot_gene_names[0];
        if (row.type==='hit') {
            row.bait_name = baitName
            row.prey_name = rowName;
        }
        if (row.type==='pulldown') {
            row.bait_name = rowName;
            row.prey_name = baitName;
        }
        if (row.type==='bait') {
            row.bait_name = baitName;
            row.prey_name = baitName;
        }
    });
    return rows;
}

const downloadTableAsCSV = (data, props) => {
    // download the interactions table as a CSV
    // data : the data array returned by constructTableData
    // props : the props passed to MassSpecTable

    // construct a timestamp in the form 'YYYY-MM-DD'
    const d = new Date();
    const year = String(d.getFullYear());
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const timestamp = `${year}-${month}-${day}`;

    // if the id is a pulldownId, format it to resemble the ENSG IDs
    const id = props.idType==='pulldown' ? `OCPD${String(props.id).padStart(11, '0')}` : props.id;

    const csvFilename = `opencell-interactions-${id}-${props.geneName}-${timestamp}.csv`;

    // construct an array of sanitized data for the CSV
    // (using the same columnDefs used to display the data in the table)
    const csvData = data.map(row => {
        const csvRow = {};
        columnDefs.forEach(def => csvRow[def.id] = def.accessor(row));
        return csvRow;
    });
    utils.triggerCSVDownload(csvData, csvFilename);
}


export default function MassSpecTable (props) {

    const [data, setData] = useState([]);
    const [loaded, setLoaded] = useState(false);
    const [loadingError, setLoadingError] = useState(false);

    useEffect(() => {  
        setLoaded(false);
        utils.getNetworkElements(
            props.id, 
            props.idType, 
            'core-complexes',
            (parentNodes, nodes, edges) => {
                setData(constructTableData(nodes));
                setLoadingError(false);
                setLoaded(true);
            }, 
            error => {
                setData([]);
                setLoaded(true);
                setLoadingError(true);
                console.log(error);
            }
        );
    }, [props.id]);

    return (
        <div className='relative'>
            {loadingError ? <div className='f2 tc loading-overlay'>No data</div> : (null)}
            {!loaded ? <div className='f2 tc loading-overlay'>Loading...</div> : (null)}

            <div className='pt3 table-container'>
                <ReactTable 
                    defaultPageSize={20}
                    showPageSizeOptions={true}
                    filterable={false}
                    columns={columnDefs}
                    data={data}
                    getTrProps={(state, rowInfo, column) => {
                        const isActive = rowInfo && rowInfo.original.type==='bait';
                        return {
                            onClick: () => props.handleGeneNameSearch(
                                rowInfo.original.uniprot_gene_names[0]
                            ),
                            style: {
                                background: isActive ? '#ddd' : null,
                                fontWeight: isActive ? 'bold' : 'normal'
                            }
                        }
                    }}
                    defaultFilterMethod={(filter, row, column) => {
                        // force default filtering to be case-insensitive
                        const id = filter.pivotId || filter.id;
                        const value = filter.value.toLowerCase();
                        return row[id] !== undefined ? String(row[id]).toLowerCase().startsWith(value) : true
                    }}
                />
            </div>
            
            {/* Button to download the table as a CSV file */}
            <Button
                text={'Export table as CSV'}
                className='ma2 bp3-button'
                onClick={() => downloadTableAsCSV(data, props)}
            />
        </div>
    );
}