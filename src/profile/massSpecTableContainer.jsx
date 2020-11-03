import * as d3 from 'd3';
import React, { useState, useContext, useEffect } from 'react';
import ReactTable from 'react-table';

import settings from '../common/settings.js';
import * as utils from '../common/utils.js';

const columnDefs = [
    {
        id: 'gene_name',
        Header: 'Gene name',
        accessor: row => row.uniprot_gene_names[0],
    },{
        id: 'type',
        Header: 'Interactor type',
        accessor: row => row.type,
    },{
        id: 'ensg_ids',
        Header: 'ENSG ID(s)',
        accessor: row => row.ensg_ids?.length===1 ? row.ensg_ids[0] : row.ensg_ids?.join(', ')
    },{
        id: 'uniprot_ids',
        Header: 'Uniprot ID(s)',
        accessor: row => row.uniprot_ids?.length===1 ? row.uniprot_ids[0] : row.uniprot_ids?.join(', ')
    },{
        id: 'cluster_id',
        Header: 'Cluster ID',
        accessor: row => String(row.cluster_id || 'None'),
    },{
        id: 'subcluster_id',
        Header: 'Core complex ID',
        accessor: row => String(row.subcluster_id || 'None'),
    }
];


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
                setData(nodes.map(node => node.data));
                setLoadingError(false);
                setLoaded(true);
            }, 
            error => {
                setData([]);
                setLoaded(true);
                setLoadingError(true);
            }
        );
    }, [props.url]);

    return (
        <div className='relative'>
            {loadingError ? <div className='f2 tc loading-overlay'>No data</div> : (null)}
            {!loaded ? <div className='f2 tc loading-overlay'>Loading...</div> : (null)}

            <div className='pt3 table-container'>
                <ReactTable 
                    defaultPageSize={20}
                    showPageSizeOptions={true}
                    filterable={true}
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
        </div>
    );
}