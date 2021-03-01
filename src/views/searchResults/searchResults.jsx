import * as d3 from 'd3';
import React, { useState, useEffect } from 'react';
import ReactTable from 'react-table';
import { Callout } from '@blueprintjs/core';

import 'tachyons';
import 'react-table/react-table.css';
import "@blueprintjs/core/lib/css/blueprint.css";

import { SectionHeader } from '../../components/common.jsx';
import settings from '../../settings/settings.js';
import * as utils from '../../utils/utils.js';

import '../../components/common.css';

const columnDefs = [
    {   
        id: 'ensg_id',
        accessor: row => row.ensg_id,
        Header: 'ENSG ID',
        width: 180,
    },{   
        id: 'gene_name',
        accessor: row => row.gene_names[0],
        Header: 'Gene name',
        width: 150,
    },{   
        id: 'protein_name',
        accessor: row => row.protein_name,
        Header: 'Gene description',
        width: 450,
    },{   
        id: 'status',
        accessor: row => row.status,
        Header: 'Status',
        width: 80,
    },
];


function NoExactMatchCallout (props) {
    return (
        <div className='pt3 pb3'>
            <Callout 
                intent='primary' 
                title={`Are you looking for the human gene ${props.geneName.toUpperCase()}?`}
            >
                Unfortunately, this gene has not yet been tagged as part of the OpenCell library 
                and is also not found among the interaction partners of any of our existing OpenCell targets.
                If you feel this may indicate a data quality issue, or if you would like to see us tag this gene, 
                please <a href='mailto:opencell@czbiohub.org'>get in touch</a>!
            </Callout>
        </div>
    );
}
    

export default function SearchResults (props) {

    const maxPageSize = 50;
    const [data, setData] = useState(undefined);
    const [loaded, setLoaded] = useState(false);

    // load the search results
    useEffect(() => {
        if (!props.match.params.query) return;
        d3.json(`${settings.apiUrl}/fsearch/${props.match.params.query}`).then(data => {
            setData(data); 
            setLoaded(true);
        }, error => setLoaded(true));
    }, [props.match]);

    if (!data) return null;

    const showNoExactMatchCallout = (
        !data.exact_match_found && (data.is_valid_gene_name || data.is_legacy_gene_name)
    );

    if (!data.hits.length) {
        return (
            <div className='pl5 pr5 pt4 w-80 flex flex-column justify-center'>
                <Callout 
                    intent='warning'
                    title={`Sorry, no results found for the search term "${props.match.params.query}"`}
                />
                {showNoExactMatchCallout ? <NoExactMatchCallout geneName={data.approved_gene_name}/> : null}
            </div>
        );
    }

    return (
        <div className='pl5 pr5 pt3 pb3 w-90'>
            {showNoExactMatchCallout ? <NoExactMatchCallout geneName={data.approved_gene_name}/> : null}
            <Callout 
                intent='info'
                title={`${data.hits.length} ${data.hits.length===1 ? 'gene' : 'genes'} found for the search term "${props.match.params.query}"`}
            />
            <div className='pt3'/>
            
            <ReactTable 
                pageSize={Math.min(data.hits.length, maxPageSize)}
                showPagination={data.hits.length > maxPageSize}
                showPageSizeOptions={false}
                filterable={false}
                columns={columnDefs}
                data={data.hits}
                getTrProps={(state, rowInfo, column) => {
                    return {
                        onClick: () => {
                            if (rowInfo.original.published_cell_line_id) {
                                props.setCellLineId(rowInfo.original.published_cell_line_id);
                            } else {
                                props.handleGeneNameSearch(rowInfo.original.gene_names[0]);
                            }
                        }
                    }
                }}
                getPaginationProps={(state, rowInfo, column) => ({style: {fontSize: 16}})}
            />
        </div>
    );
}