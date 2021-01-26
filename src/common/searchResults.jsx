import * as d3 from 'd3';
import React, { useState, useEffect } from 'react';
import ReactTable from 'react-table';

import 'tachyons';
import 'react-table/react-table.css';
import "@blueprintjs/core/lib/css/blueprint.css";

import { SectionHeader } from '../profile/common.jsx';
import settings from './settings.js';
import * as utils from './utils.js';

import './common.css';

const columnDefs = [
    {   
        id: 'ensg_id',
        accessor: row => row.ensg_id,
        Header: 'ENSG ID',
        width: 150,
    },{   
        id: 'gene_name',
        accessor: row => row.gene_names[0],
        Header: 'Gene name',
        width: 150,
    },{   
        id: 'aliases',
        accessor: row => row.gene_names.slice(1).join(', '),
        Header: 'Aliases',
        width: 150,
    },{   
        id: 'protein_name',
        accessor: row => row.protein_name,
        Header: 'Protein name',
        width: 500,
    },{   
        id: 'status',
        accessor: row => row.crispr_design_id ? 'Target' : 'Interactor',
        Header: 'Status',
        width: 100,
    },
];


export default function SearchResults (props) {

    const maxPageSize = 50;
    const [data, setData] = useState([]);

    // load the search results
    useEffect(() => {
        if (!props.match.params.query) return;
        d3.json(`${settings.apiUrl}/fsearch/${props.match.params.query}`).then(data => {
            data.sort((a, b) => {
                if (a.relevance) return a.relevance < b.relevance ? 1 : -1;
                return a.gene_names[0] > b.gene_names[0] ? 1 : -1;
            });
            setData(data); 
        }, error => setData([]));
    }, [props.match]);

    if (!data.length) {
        return (
            <div className='pl5 pr5 pt4 flex justify-center'>
                <span className='f4'>
                    {`Sorry, no results found for search term "${props.match.params.query}"`}
                </span>
            </div>
        );
    }

    return (
        <div className='pl5 pr5 pt3 pb3'>
            <SectionHeader 
                title={`${data.length} genes found for search term "${props.match.params.query}"`}
            />
            <div className='pt3'/>

            <ReactTable 
                pageSize={Math.min(data.length, maxPageSize)}
                showPagination={data.length > maxPageSize}
                showPageSizeOptions={false}
                filterable={false}
                columns={columnDefs}
                data={data}
                getTrProps={(state, rowInfo, column) => {
                    return {
                        onClick: () => props.handleGeneNameSearch(rowInfo.original.gene_names[0]),
                    }
                }}
                getPaginationProps={(state, rowInfo, column) => ({style: {fontSize: 16}})}
            />
        </div>
    );
}