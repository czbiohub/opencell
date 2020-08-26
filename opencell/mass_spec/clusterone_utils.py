import sys
import pandas as pd
import numpy as np
import random
import re

import itertools
import markov_clustering as mc
import networkx as nx
import pval_calculation as pval
from itertools import repeat
import cluster_heatmap as ch
from multiprocessing import Pool


from opencell.database import ms_utils
from opencell.database import ms_operations as ms_ops
from opencell.database import models, utils

import sqlalchemy
from sqlalchemy import inspect
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Numeric
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import desc


def retrieve_cluster_df(network_df, cluster, target_col='target', prey_col='prey'):
    """
    From a  list of cluster members from clusterone results, retrieve
    corresponding cluster from the network_df
    """

    network_df = network_df.copy()
    network_df = network_df[network_df[target_col] != network_df[prey_col]]

    return network_df[
        (network_df[target_col].
        isin(cluster)) & (network_df[prey_col].isin(cluster))]


def delete_single_edges(network_df, target_col, prey_col):
    """
    delete all the single edges from a network_df, and also prune
    self-prey interactions
    """
    network_df = network_df.copy()

    # remove target-prey matching interactions
    network_df = network_df[network_df[target_col] != network_df[prey_col]]
    single = 1

    # remove single edges, pruning newly made single edges too until there are no single edges
    while single > 0:
        bait_counts = network_df[target_col].value_counts()
        bait_singles = bait_counts[bait_counts < 2].index.to_list()
        prey_counts = network_df[prey_col].value_counts()
        prey_singles = prey_counts[prey_counts < 2].index.to_list()

        single = len(bait_singles) + len(prey_singles)
        print(single)
        network_df = network_df[~network_df[target_col].isin(bait_singles)]
        network_df = network_df[~network_df[prey_col].isin(prey_singles)]
    return network_df


def clusterone_haircut(clusterone, all_hits, target_col, prey_col):
    """
    Haircut clusterone members (removing single edge interactors)
    """
    all_hits = all_hits.copy()
    clusterone = clusterone.copy()
    members = clusterone['Members'].apply(lambda x: x.split(' '))

    multi_args = zip(members, repeat(all_hits), repeat(target_col), repeat(prey_col))

    # multi processing
    p = Pool()
    haircuts = p.starmap(recursive_haircut, multi_args)
    p.close()
    p.join()

    clusterone['Members_haircut'] = haircuts

    return clusterone


def recursive_haircut(cluster, all_hits, target_col, prey_col):
    """
    Continue haircuts until there are no more single edges left
    """

    orig_len = len(cluster)
    new_len = 0
    clipped = cluster

    while orig_len - new_len > 0:
        orig_len = len(clipped)
        clipped = haircut(clipped, all_hits, target_col, prey_col)
        new_len = len(clipped)

    return clipped


def haircut(cluster, all_hits, target_col, prey_col):
    """
    child function of clusterone_haircut
    """
    cluster_group = all_hits[
        (all_hits[target_col].isin(cluster)) & (all_hits[prey_col].isin(cluster))]

    haircut_members = []
    for member in cluster:
        membership = cluster_group[
            (cluster_group[target_col] == member) | (cluster_group[prey_col] == member)]

        # validation that a cluster member is involved in at least two interactions
        members = set(membership[target_col].to_list() + membership[prey_col].to_list())
        if len(members) > 2:
            haircut_members.append(member)

    return haircut_members


def clusterone_mcl(
        clusterone, network_df, target_col, prey_col, clusterone_thresh,
        mcl_thresh, mcl_inflation, mcl_haircut=False):
    """
    Performs secondary clustering from clusterone results generating a new
    """
    network_df = network_df.copy()
    clusterone = clusterone.copy()

    clusters = clusterone['Members'].apply(lambda x: x.split(' ')).to_list()

    # Clusterone cluster id
    c_clusters = []
    # Boolean for whether the cluster went thru second clustering
    mcl = []
    # New MCL cluster
    m_clusters = []
    for idx, cluster in enumerate(clusters):
        # original clusterone cluster number
        idx += 1

        # If the clusterone cluster does not exceed minimum size for second clustering
        # Return cluster with a haircut
        if len(cluster) < clusterone_thresh:
            clipped = recursive_haircut(cluster, network_df, target_col, prey_col)
            if clipped:
                c_clusters.append(idx)
                mcl.append(False)
                m_clusters.append(clipped)

        # go thru the MCL second cluster
        else:
            cluster_network = retrieve_cluster_df(
                network_df, cluster, target_col, prey_col)

            # NetworkX transformation of pandas interactions to sparse matrix
            c_graph = nx.convert_matrix.from_pandas_edgelist(
                cluster_network, 'target', 'prey', edge_attr='pvals')
            nodes = list(c_graph.nodes)
            c_mat = nx.to_scipy_sparse_matrix(c_graph)

            # Run MCL with a given inflation parameter
            result = mc.run_mcl(c_mat, inflation=mcl_inflation)
            mcl_clusters = mc.get_clusters(result)
            for mcl_cluster in mcl_clusters:
                if len(mcl_cluster) >= mcl_thresh:
                    mcl_nodes = [nodes[x] for x in mcl_cluster]
                    c_clusters.append(idx)
                    mcl.append(True)
                    m_clusters.append(mcl_nodes)
    mcl_df = pd.DataFrame()
    mcl_df['clusterone_id'] = c_clusters
    mcl_df['second_clustering'] = mcl
    mcl_df['MCL_cluster'] = m_clusters
    if mcl_haircut:
        mcl_df['MCL_cluster'] = mcl_df['MCL_cluster'].apply(
            recursive_haircut, args=[network_df, target_col, prey_col])
        mcl_df = mcl_df[mcl_df['MCL_cluster'].map(lambda x: len(x) > 0)]
        mcl_df.reset_index(drop=True, inplace=True)

    return mcl_df


def explode_cluster_groups(mcl_cluster):
    """
    convert cluster grouping into cluster annotation by proteingroup.
    Useful for merges and database uploads
    """

    explode = mcl_cluster.copy()
    explode.reset_index(inplace=True)
    explode.rename(columns={'index': 'mcl_cluster', 'MCL_cluster': 'gene_names'}, inplace=True)
    explode.drop(columns=['clusterone_id', 'second_clustering'], inplace=True)

    explode = explode.explode('gene_names')
    exploded = pd.DataFrame(explode.groupby('gene_names')['mcl_cluster'].apply(list))
    exploded.reset_index(inplace=True)

    return exploded


def annotate_mcl_clusters(umap_df, mcl_df, gene_col, first_clust=True):
    """
    Append MCL-cluster annotations to umap dfs
    """
    umap_df = umap_df.copy()
    mcl_df = mcl_df.copy()

    mcl_df.rename(columns={'gene_names': gene_col}, inplace=True)
    if first_clust:
        mcl_df['mcl_cluster'] = mcl_df['mcl_cluster'].apply(lambda x: x[0])

    umap_df = umap_df.merge(mcl_df, on=gene_col, how='left')

    return umap_df


def cluster_matrix_to_sql_table(mcl, network, method='single', metric='cosine', edge='stoich'):
    mcl = mcl.copy()
    network = network.copy()

    mcl_explode = mcl.explode('mcl_cluster')
    cluster_list = mcl_explode['mcl_cluster'].unique()
    cluster_list.sort()


    # lists to populate, will become dataframe columns
    cluster_col = []
    cols_col = []
    rows_col = []
    targets_col = []
    preys_col = []
    pull_plate_col = []

    for cluster in cluster_list:
        # get cluster sub-matrix and network selection
        _, selected_network, cluster_matrix = ch.generate_mpl_matrix(
            network, mcl, clusters=[cluster], metric=edge)

        # Get the hierarchical order of targets and preys
        bait_leaves = ch.bait_leaves(cluster_matrix, method=method, metric=metric)
        prey_leaves = ch.prey_leaves(cluster_matrix, method=method, metric=metric)

        # go thru each bait leaf and prey leaf and populate the list
        for col, bait in enumerate(bait_leaves):
            for row, prey in enumerate(prey_leaves):
                selection = selected_network[
                    (selected_network['target'] == bait) & (selected_network['prey'] == prey)]
                # if there is an interaction, add an entry
                if selection.shape[0] > 0:
                    cluster_col.append(cluster)
                    cols_col.append(col)
                    rows_col.append(row)
                    targets_col.append(bait)
                    preys_col.append(prey)
                    pull_plate_col.append(selection.plate.item())
    sql = pd.DataFrame()
    sql['cluster'] = cluster_col
    sql['target_name'] = targets_col
    sql['prey'] = preys_col
    sql['col_index'] = cols_col
    sql['row_index'] = rows_col
    sql['pulldown_plate_id'] = pull_plate_col
    return sql


def sql_table_add_hit_id(sql_table, pulldowns, url):
    """
    from the cluster sql table, start a query to access proper hit
    IDs for finalizing the table

    """

    sql_table = sql_table.copy()
    pulldowns = pulldowns.copy()

    sql_table['pulldown_plate_id'] = sql_table['pulldown_plate_id'].apply(
        ms_utils.format_ms_plate)

    # merge Crispr design and well ids from pulldowns table
    sql_table = sql_table.merge(
        pulldowns, on=['pulldown_plate_id', 'target_name'], how='left')

    # sort by design id and well id for faster queries
    sort_table = sql_table.sort_values(['design_id', 'well_id'])
    sort_table.reset_index(drop=True, inplace=True)


    # start a sequel session
    # initiate and connect engine
    engine = sqlalchemy.create_engine(url)
    engine.connect()

    session_factory = sessionmaker(bind=engine)
    session = scoped_session(session_factory)


    hit_ids = []
    pwell_id = ''
    pdesign_id = ''
    # iterate through each row of sql_table and query the Hit ID


    for i, row in sort_table.iterrows():
        # progress notation
        if i % 100 == 0:
            status = str(i) + '/' + str(sort_table.shape[0])
            sys.stdout.write("\r{}".format(status))


        well_id = row.well_id
        design_id = row.design_id
        plate_id = row.pulldown_plate_id
        preys = row.prey
        preys = preys.split(';')

        # get the cellline_id, skip if preceding row had the same query
        if not (well_id == pwell_id) & (design_id == pdesign_id):
            pull_cls = ms_ops.MassSpecPolyclonalOperations.from_plate_well(session, design_id, well_id)
            cell_line_id = pull_cls.line.id

        query_hit = False
        # iterate through each gene name in protein group and query for the hit id
        for prey in preys:
            prey = '%' + prey + '%'
            hit_query = (
                session.query(models.MassSpecHit)
                .join(models.MassSpecPulldown)
                .join(models.MassSpecProteinGroup)
                .filter(or_(models.MassSpecHit.is_significant_hit,
                    models.MassSpecHit.is_minor_hit))
                .filter(models.MassSpecPulldown.cell_line_id == cell_line_id)
                .filter(models.MassSpecPulldown.pulldown_plate_id == plate_id)
                .filter(func.array_to_string(
                    models.MassSpecProteinGroup.gene_names, ' ').like(prey))
                .order_by(desc(models.MassSpecHit.pval))
                .limit(1)
                .one_or_none())
            # if there is a matching hit, add the hit id and break loop
            if hit_query:
                hit_ids.append(hit_query.id)
                query_hit = True
                break
        # if there was no hit, append a null value
        if not query_hit:
            hit_ids.append(None)

        # save well id and design id for next iteration
        pwell_id = well_id
        pdesign_id = design_id

    sort_table['hit_id'] = hit_ids
    sort_table = sort_table.sort_values(['cluster', 'col_index', 'row_index'])

    return sort_table
