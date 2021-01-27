import * as d3 from 'd3';
import React, { useState, useEffect } from 'react';
import ReactTable from 'react-table';
import { Callout } from '@blueprintjs/core';

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
    const [loaded, setLoaded] = useState(false);
    const [queryIsValidGeneName, setQueryIsValidGeneName] = useState(false);

    // load the search results
    useEffect(() => {
        if (!props.match.params.query) return;
        d3.json(`${settings.apiUrl}/fsearch/${props.match.params.query}`).then(data => {
            data.sort((a, b) => {
                if (a.relevance) return a.relevance < b.relevance ? 1 : -1;
                return a.gene_names[0] > b.gene_names[0] ? 1 : -1;
            });
            setData(data); 
            setLoaded(true);
        }, error => setLoaded(true));
    }, [props.match]);

    // if the search results, check to see if the query is a valid gene name, using the mygene API
    useEffect(() => {
        if (data.length || !loaded) return;
        const query = props.match.params.query.toUpperCase();
        d3.json(`http://mygene.info/v3/query?q=${query}&species=human&ensemblonly=true&limit=1`)
            .then(result => {
                setQueryIsValidGeneName(result.hits.length && result.hits[0].symbol===query);
            });
    }, [data, loaded]);

    if (!data.length) {
        return (
            <div className='pl5 pr5 pt4 w-80 flex flex-column justify-center'>
                <Callout 
                    intent='warning'
                    title={`Sorry, no results found for the search term "${props.match.params.query}"`}
                />
                {(queryIsValidGeneName && !data.length) ? (
                    <div className='pt3'>
                        <Callout 
                            intent='primary' 
                            title={`Are you looking for the human gene ${props.match.params.query.toUpperCase()}?`}
                        >
                            Unfortunately, this gene has not yet been tagged as part of the OpenCell library 
                            and is also not found among the interaction partners of any of our existing OpenCell targets.
                            If you feel this may indicate a data quality issue, or if you would like to see us tag this gene, 
                            please <a href='mailto:opencell@czbiohub.org'>get in touch</a>!
                        </Callout>
                    </div>
                ) : null}
            </div>
        );
    }

    return (
        <div className='pl5 pr5 pt3 pb3 w-80'>
            <SectionHeader 
                title={`${data.length} genes found for the search term "${props.match.params.query}"`}
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