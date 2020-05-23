import io
import os
import re
import enum
import json
import requests
import numpy as np
import pandas as pd
import sqlalchemy as db

from opencell.database import models, utils


def get_uniprot_metadata(gene_name, enst_id=None):
    '''
    Retrieve the top Uniprot search result given a gene_name and maybe an ENST ID
    '''

    # first try querying with the ENST ID, if one was provided
    metadata = None
    if enst_id is not None:
        metadata = query_uniprotkb(query=enst_id, limit=1)

    # if there was no ENST ID, or no metadata was found,
    # fall back to querying with the gene name (which we assume is not none)
    if enst_id is None or metadata is None:
        print("Warning: querying UniprotKB by gene name and not by ENST ID for '%s'" % gene_name)
        metadata = query_uniprotkb(query=gene_name, limit=1)
        if metadata is None:
            print("Warning: no UniprotKB results for '%s'" % gene_name)
            return None

    metadata = metadata.iloc[0]
    return metadata


def query_uniprotkb(query, limit=1):
    '''
    Search UniprotKB for a given query and return some useful metadata

    Parameters
    ----------
    query : one of many identifiers, including a protein or gene name,
        a uniprot_id, or an ENST ID.
    limit : how many results (sorted by 'relevance') to return

    Returns
    -------
    A dataframe of metadata (for column descriptions, see below)

    Aside
    -----
    These are additional query columns containing various specific gene name synonyms;
    as far as I can tell, these all also appear in the 'genes' column:
    'genes(PREFERRED)'
    'genes(ALTERNATIVE)'
    'genes(OLN)'
    'genes(ORF)'

    '''

    url = 'https://www.uniprot.org/uniprot'

    # Define the UniprotKB columns to include in the search result.
    # These were selected by hand in the 'customize columns' page,
    # then the query names were extracted from the 'Share your results' URL,
    # and finally the query names were matched with the output names.
    # (Note that the output names are used to rename columns in the dataframe of search results
    # when a final_name is specified, otherwise they are included below just for reference)
    column_defs = [

        # the uniprot_id
        {
            'query_name': 'id',
            'output_name': 'Entry',
            'final_name': 'uniprot_id',
        },

        # a primary descriptive protein name,
        # followed by one or more synonymous descriptive protein names in parentheses
        {
            'query_name': 'protein names',
            'output_name': 'Protein names',
        },

        # comma-separed list of descriptive protein families
        {
            'query_name': 'families',
            'output_name': 'Protein families',
        },

        # space-separated list of all gene name synonyms for the gene encoding the protein
        {
            'query_name': 'genes',
            'output_name': 'Gene names',
        },

        # paragraph-like description of the protein's function
        {
            'query_name': 'comment(FUNCTION)',
            'output_name': 'Function [CC]',
            'final_name': 'annotation'
        },
    ]

    params = {
        'sort': 'score',
        'format': 'tab',
        'limit': str(limit),
        'query': f'reviewed:yes+AND+organism:9606+AND+${query}',
        'columns': ','.join([column_def['query_name'] for column_def in column_defs]),
    }

    try:
        response = requests.get(url, params)
    except ConnectionError:
        print('Connection error while querying for %s' % query)
        return None

    if not response.text:
        print("No UniprotKB results found for query '%s'" % query)
        return None

    df = pd.read_csv(io.StringIO(response.text), sep='\t')

    # rename columns
    final_column_names = {
        column_def['output_name']: column_def['final_name']
        for column_def in column_defs if column_def.get('final_name')
    }
    df.rename(columns=final_column_names, inplace=True)

    # clean up all remaining column names
    columns = {
        column: (
            column
            .replace('(', '')
            .replace(' )', '')
            .replace('  ', ' ')
            .replace(' ', '_')
            .lower()
        ) for column in df.columns
    }
    df.rename(columns=columns, inplace=True)
    return df


def uniprot_id_mapper(input_ids, input_type, output_type):
    '''
    Map a list of ids from one type to another using Uniprot's ID mapping API

    Parameters
    ----------
    input_type, output_type : str, the types of the input and output ids,
        according to the abbrevations defined by uniprot here:
        https://www.uniprot.org/help/api_idmapping

    Returns
    -------
    dataframe with two columns named `input_type` and `output_type`

    Example
    -------
    To map ENST ID to uniprot ID:
    map_uniprot_ids(enst_ids, input_type='ENSEMBL_TRS_ID', output_type='ACC')

    '''
    api_url = 'https://www.uniprot.org/uploadlists'

    params = {
        'from': input_type,
        'to': output_type,
        'format': 'tab',
        'query': '',
    }

    # the number of times to try making each request
    # (the API seems to be unreliable and occasionally times out)
    max_num_tries = 3

    # the number of ids to query in each API request
    batch_size = 100

    dfs = []
    for ind in range(0, len(input_ids), batch_size):

        # the API excepts a space-separated list of ids
        params['query'] = ' '.join(input_ids[ind:(ind + batch_size)])

        df = None
        num_tries = 0
        while num_tries <= max_num_tries:
            num_tries += 1
            response = requests.get(api_url, params=params)
            if response.status_code == 200:
                df = pd.read_csv(io.StringIO(response.text), sep='\t')
                break

        if df is not None:
            dfs.append(df)
        else:
            raise Exception('Uniprot API timed out at batch %s' % ind)

    ids = pd.concat(dfs, axis=0)
    ids.rename(columns={'From': input_type, 'To': output_type}, inplace=True)
    return ids
