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
from cdlib import algorithms

# sys.path.append('../../../')
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


def mcl_haircut(first_mcl, all_hits, target_col, prey_col, edge='', edge_thresh=0):
    """
    Haircut clusterone members (removing single edge interactors)
    """
    all_hits = all_hits.copy()
    first_mcl = first_mcl.copy()
    members = first_mcl['gene_name']

    multi_args = zip(members, repeat(all_hits), repeat(target_col), repeat(prey_col),
        repeat(edge), repeat(edge_thresh))

    # multi processing
    p = Pool()
    haircuts = p.starmap(recursive_haircut, multi_args)
    p.close()
    p.join()

    first_mcl['haircut_members'] = haircuts

    return first_mcl


def recursive_haircut(cluster, all_hits, target_col, prey_col, edge='', edge_thresh=0):
    """
    Continue haircuts until there are no more single edges left
    """

    orig_len = len(cluster)
    new_len = 0
    clipped = cluster

    while orig_len - new_len > 0:
        orig_len = len(clipped)
        clipped = haircut(clipped, all_hits, target_col, prey_col, edge, edge_thresh)
        new_len = len(clipped)

    return clipped


def clean_up_first_mcl(mcl_stoi, grouped=False):
    mcl_stoi = mcl_stoi.copy()
    mcl_stoi.drop(columns=['selected', 'shared name'], inplace=True)
    mcl_stoi.reset_index(drop=True, inplace=True)
    mcl_stoi.rename(columns={'__mclCluster': 'mcl_cluster', 'name': 'gene_name'}, inplace=True)
    mcl_stoi.sort_values(['mcl_cluster', 'gene_name'], inplace=True)
    mcl_stoi = mcl_stoi[mcl_stoi['mcl_cluster'].apply(lambda x: np.isfinite(x))]

    count = mcl_stoi.groupby('mcl_cluster').count()
    clusters = count[count['gene_name'] > 2].index.to_list()
    mcl_stoi = mcl_stoi[mcl_stoi['mcl_cluster'].isin(clusters)]
    mcl_stoi.reset_index(drop=True, inplace=True)
    if grouped:
        mcl_stoi = pd.DataFrame(
            mcl_stoi.groupby('mcl_cluster')['gene_name'].apply(list)).reset_index()
    return mcl_stoi


def haircut(cluster, all_hits, target_col, prey_col, edge, edge_thresh):
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
        elif edge:
            if membership[edge].max() > edge_thresh:
                haircut_members.append(member)

    return haircut_members


def mcl_mcl(first_mcl, network_df, target_col, prey_col, first_thresh, mcl_thresh, mcl_inflation,
        edge=''):
    """
    Performs secondary clustering from clusterone results generating a new
    """
    network_df = network_df.copy()
    first_mcl = first_mcl.copy()

    clusters = first_mcl['gene_name']

    # fist clustering id
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
        if len(cluster) < first_thresh:
            c_clusters.append(idx)
            mcl.append(False)
            m_clusters.append(cluster)

        # go thru the MCL second cluster
        else:
            cluster_network = retrieve_cluster_df(
                network_df, cluster, target_col, prey_col)
            if not edge:
                edge = None
            # NetworkX transformation of pandas interactions to sparse matrix
            c_graph = nx.convert_matrix.from_pandas_edgelist(
                cluster_network, target_col, prey_col, edge_attr=edge)
            nodes = list(c_graph.nodes)
            c_mat = nx.to_scipy_sparse_matrix(c_graph)

            # Run MCL with a given inflation parameter
            result = mc.run_mcl(c_mat, inflation=mcl_inflation)
            mcl_clusters = mc.get_clusters(result, keep_overlap=False)

            for mcl_cluster in mcl_clusters:
                if len(mcl_cluster) >= mcl_thresh:
                    mcl_nodes = [nodes[x] for x in mcl_cluster]
                    c_clusters.append(idx)
                    mcl.append(True)
                    m_clusters.append(mcl_nodes)
    mcl_df = pd.DataFrame()
    mcl_df['super_cluster'] = c_clusters
    mcl_df['second_clustering'] = mcl
    mcl_df['gene_names'] = m_clusters

    return mcl_df


def mcl_newman(first_mcl, network_df, target_col, prey_col, first_thresh):
    """
    Performs secondary clustering from clusterone results generating a new
    """
    network_df = network_df.copy()
    first_mcl = first_mcl.copy()

    clusters = first_mcl['gene_name']

    # first clustering id
    c_clusters = []
    # Boolean for whether the cluster went thru second clustering
    newman = []
    # New newman cluster
    m_clusters = []
    for idx, cluster in enumerate(clusters):
        # original clusterone cluster number
        idx += 1
        cluster_network = retrieve_cluster_df(
            network_df, cluster, target_col, prey_col)

        # If the clusterone cluster does not exceed minimum size for second clustering
        # Return cluster with a haircut
        if (len(cluster) < first_thresh) or (cluster_network.shape[0] < 3):
            c_clusters.append(idx)
            newman.append(False)
            m_clusters.append(cluster)

        # go thru the MCL second cluster
        else:
            cluster_network = retrieve_cluster_df(
                network_df, cluster, target_col, prey_col)


            # NetworkX transformation of pandas interactions to sparse matrix
            c_graph = nx.convert_matrix.from_pandas_edgelist(
                cluster_network, target_col, prey_col, edge_attr=None)

            # Run MCL with a given inflation parameter
            result = algorithms.eigenvector(c_graph)
            newman_clusters = result.communities
            for newman_cluster in newman_clusters:
                c_clusters.append(idx)
                newman.append(True)
                m_clusters.append(newman_cluster)
    newman_df = pd.DataFrame()
    newman_df['super_cluster'] = c_clusters
    newman_df['second_clustering'] = newman
    newman_df['gene_names'] = m_clusters

    return newman_df



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


def explode_clusterone_groups(clusterone):
    explode = clusterone.copy()
    # explode.reset_index(inplace=True)
    explode = explode[explode['Members_haircut'].apply(len) > 0]
    explode.rename(columns={'Members_haircut': 'gene_names', 'Cluster': 'Clusterone_id'}, inplace=True)
    explode = explode[['Clusterone_id', 'gene_names']]
    explode = explode.explode('gene_names')

    exploded = pd.DataFrame(
        explode.groupby('gene_names')['Clusterone_id'].apply(list)).reset_index()
    # exploded_clusterone = pd.DataFrame(
    #     explode.groupby('gene_names')['clusterone_id'].apply(list)).reset_index()

    # exploded = exploded.merge(exploded_clusterone, on='gene_names', how='left')

    return exploded


def explode_mcl_groups(mcl_cluster):
    """
    convert cluster grouping into cluster annotation by proteingroup.
    Useful for merges and database uploads
    """

    explode = mcl_cluster.copy()
    explode.reset_index(inplace=True)
    explode.rename(columns={'index': 'mcl_cluster', 'MCL_cluster': 'gene_names'}, inplace=True)
    explode.drop(columns=['second_clustering'], inplace=True)
    explode = explode.explode('gene_names')

    exploded = pd.DataFrame(
        explode.groupby('gene_names')['mcl_cluster'].apply(list)).reset_index()
    # exploded_clusterone = pd.DataFrame(
    #     explode.groupby('gene_names')['clusterone_id'].apply(list)).reset_index()

    # exploded = exploded.merge(exploded_clusterone, on='gene_names', how='left')

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


def cluster_matrix_to_sql_table(mcl, network, method='single', metric='cosine', edge='stoich',
        clustering='mcl_cluster', subcluster='subcluster', corecluster='core_cluster'):
    """
    Transform the cluster output from MCL clustering into a sparse
    hierarchical matrix of interactions, and format into a SQL table
    for use in DB front-end
    """
    mcl = mcl.copy()
    network = network.copy()

    # mcl_explode = mcl.explode('mcl_cluster')
    cluster_list = mcl[clustering].unique()
    cluster_list.sort()


    # lists to populate, will become dataframe columns
    cluster_col = []
    subcluster_col = []
    corecluster_col = []
    cols_col = []
    rows_col = []
    targets_col = []
    preys_col = []
    pull_plate_col = []
    pg_id_col = []

    for cluster in cluster_list:
        # get cluster sub-matrix and network selection
        _, _, cluster_matrix = ch.generate_mpl_matrix(
            network, mcl, clusters=[cluster], cluster_col=clustering, metric=edge, sparse=True)


        # Get the hierarchical order of targets and preys
        bait_leaves = ch.bait_leaves(cluster_matrix, method=method, metric=metric)
        prey_leaves = ch.prey_leaves(cluster_matrix, method=method, metric=metric)

        # go thru each bait leaf and prey leaf and populate the list
        for col, bait in enumerate(bait_leaves):
            for row, prey in enumerate(prey_leaves):
                selection = network[
                    (network['target'] == bait) & (network['prey'] == prey)].sort_values(
                    edge, ascending=False)
                # if there is an interaction, add an entry
                if selection.shape[0] > 0:
                    # identify subcluster
                    sub_bait = mcl[mcl['gene_names'] == bait][subcluster].item()
                    sub_prey = mcl[mcl['gene_names'] == prey][subcluster].item()

                    # subcluster_entry
                    if sub_bait == sub_prey:
                        subcluster_col.append(sub_bait)
                    else:
                        subcluster_col.append(None)
                    # identify core complex
                    core_bait = mcl[mcl['gene_names'] == bait][corecluster].item()
                    core_prey = mcl[mcl['gene_names'] == prey][corecluster].item()
                    # subcluster_entry
                    if core_bait == core_prey:
                        corecluster_col.append(core_bait)
                    else:
                        corecluster_col.append(None)

                    # add proteingroup_id
                    cluster_col.append(cluster)
                    cols_col.append(col)
                    rows_col.append(row)
                    targets_col.append(bait)
                    preys_col.append(prey)
                    pg_id_col.append(selection.protein_ids.iloc[0])
                    pull_plate_col.append(selection.plate.iloc[0])
    sql = pd.DataFrame()
    sql['cluster_id'] = cluster_col
    sql['subcluster_id'] = subcluster_col
    sql['target_name'] = targets_col
    sql['prey'] = preys_col
    sql['col_index'] = cols_col
    sql['row_index'] = rows_col
    sql['pulldown_plate_id'] = pull_plate_col
    sql['protein_ids'] = pg_id_col
    sql['core_complex_id'] = corecluster_col

    # sql['subcluster_id'] = sql['subcluster_id'].astype('Int64')
    return sql


def sql_table_add_hit_id(sql_table, pulldowns, url):
    """
    from the cluster sql table, start a query to access proper hit
    IDs for finalizing the table

    """

    sql_table = sql_table.copy()
    pulldowns = pulldowns.copy()
    sql_table['target_name'] = sql_table['target_name'].apply(lambda x: x.upper())
    pulldowns['target_name'] = pulldowns['target_name'].apply(lambda x: x.upper())

    sql_table['pulldown_plate_id'] = sql_table[
        'pulldown_plate_id'].apply(ms_utils.format_ms_plate)

    # merge Crispr design and well ids from pulldowns table
    sql_table = sql_table.merge(
        pulldowns, on=['pulldown_plate_id', 'target_name'], how='left')

    # sort by design id and well id for faster queries
    sort_table = sql_table.sort_values(['design_id', 'well_id'])

    sort_table.dropna(subset=['design_id', 'well_id'], inplace=True)
    sort_table.reset_index(drop=True, inplace=True)


    # start a sequel session
    # initiate and connect engine
    engine = sqlalchemy.create_engine(url)
    engine.connect()

    session_factory = sessionmaker(bind=engine)
    session = scoped_session(session_factory)


    hit_ids = []
    # also append hit's gene names for fast validation
    hit_gene_names = []
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
        sort_count = row.sort_count
        pg_id = row.protein_ids

        pg_id = ms_utils.create_protein_group_id(pg_id)[0]

        # get the cellline_id, skip if preceding row had the same query
        if not (well_id == pwell_id) & (design_id == pdesign_id):
            try:
                pull_cls = ms_ops.MassSpecPolyclonalOperations.from_plate_well(
                    session, design_id, well_id, sort_count=sort_count)
            except Exception:
                print(design_id)
                print(well_id)
                print(sort_count)
                raise
            cell_line_id = pull_cls.line.id

        # iterate through each gene name in protein group and query for the hit id
        # return all hits that contain part of the gene name
        try:
            hit = (
                session.query(models.MassSpecHit)
                .join(models.MassSpecPulldown)
                .join(models.MassSpecProteinGroup)
                .filter(or_(models.MassSpecHit.is_significant_hit,
                    models.MassSpecHit.is_minor_hit))
                .filter(models.MassSpecPulldown.cell_line_id == cell_line_id)
                .filter(models.MassSpecPulldown.pulldown_plate_id == plate_id)
                .filter(models.MassSpecProteinGroup.id == pg_id)
                .order_by(desc(models.MassSpecHit.pval))
                .limit(1)
                .one())
        except Exception:
            hit = None
        # if there is a matching hit, append hit id and gene names
        if hit:
            hit_ids.append(hit.id)
            hit_gene_names.append(hit.protein_group.gene_names)
        # if there was no hit, append a null value
        else:
            hit_ids.append(None)
            hit_gene_names.append(None)
            print(row.target_name + ' ' + row.prey)

        # save well id and design id for next iteration
        pwell_id = well_id
        pdesign_id = design_id

    sort_table['hit_id'] = hit_ids
    # sort_table['hit_id'] = sort_table['hit_id'].astype('Int64')
    sort_table['hit_gene_names'] = hit_gene_names
    sort_table = sort_table.sort_values(['cluster_id', 'col_index', 'row_index'])

    return sort_table


def poor_annotation_preys(network, annot, annot_score, target_col, prey_col):
    """
    Using a network of unique interactions, include preys that are poorly annotated
    """

    annot = annot[annot['Annotation'] >= annot_score]
    network = network.copy()

    network_genes = set(network[target_col].to_list() + network[prey_col].to_list())
    annot['OC_prey'] = annot['Gene names'].apply(
        lambda x: list(set(x).intersection(network_genes))
    )
    annot['OC_prey'] = annot['OC_prey'].apply(lambda x: ' '.join(x) if x else None)
    annot = annot.sort_values(['OC_prey', 'Annotation'])

    annot = annot[annot['OC_prey'].apply(lambda x: True if x else False)]

    return annot


def poor_annotation_prey_cluster(clusters, annot):
    """
    Use output from explode_cluster_group to append cluster information
    """

    clusters = clusters.copy()
    annot = annot.copy()

    annot.merge(clusters.rename(columns={'gene_names': 'OC_prey'}), how='left')

    return annot


def poor_annotation_prey_interactors(annot, network, target_col, prey_col):
    """
    Append a list of all interactors by the poorly annotated preys
    """
    annot = annot.copy()
    network = network.copy()

    annot['OC_prey_interactors'] = annot['OC_prey'].apply(
        aux_poor_interactors, args=[network, target_col, prey_col])

    annot['interactor_count'] = annot['OC_prey_interactors'].apply(len)

    return annot


def aux_poor_interactors(prey, network, target_col, prey_col):
    """
    aux function for poor_annotation_prey_interactors
    """
    network = network.copy()
    interactors = []

    # left side
    left = network[network[target_col] == prey]
    if left.shape[0] > 0:
        interactors += left[prey_col].to_list()

    # right side
    right = network[network[prey_col] == prey]

    if right.shape[0] > 0:
        interactors += right[target_col].to_list()

    return interactors


def split_mcl(summary, network_df, target_col, prey_col, mcl_thresh, mcl_inflation,
        edge='', raw_return=False):
    """
    If MCL cluster has two core clusters, try to split it into two
    """
    network_df = network_df.copy()
    summary = summary.copy()

    clusters = summary.groupby(
        'super_cluster')['gene_name'].apply(list).to_list()

    num_cores = pd.DataFrame(summary.groupby(
        'super_cluster')['core_cluster'].nunique()).reset_index()
    change_list = num_cores[num_cores[
        'core_cluster'] >= 2]['super_cluster'].to_list()

    # first clustering id
    c_clusters = []

    # New MCL cluster
    m_clusters = []
    for idx, cluster in enumerate(clusters):

        # original clusterone cluster number
        idx += 1
        if idx not in change_list:
            m_clusters.append(cluster)
            c_clusters.append(idx)
            continue

        # go thru the MCL second cluster
        else:
            cluster_network = retrieve_cluster_df(
                network_df, cluster, target_col, prey_col)
            if not edge:
                edge = None
            # NetworkX transformation of pandas interactions to sparse matrix
            c_graph = nx.convert_matrix.from_pandas_edgelist(
                cluster_network, target_col, prey_col, edge_attr=edge)
            nodes = list(c_graph.nodes)
            c_mat = nx.to_scipy_sparse_matrix(c_graph)

            # Run MCL with a given inflation parameter
            result = mc.run_mcl(c_mat, inflation=mcl_inflation)
            mcl_clusters = mc.get_clusters(result, keep_overlap=False)

            for mcl_cluster in mcl_clusters:
                if len(mcl_cluster) >= mcl_thresh:
                    mcl_nodes = [nodes[x] for x in mcl_cluster]
                    c_clusters.append(idx)
                    m_clusters.append(mcl_nodes)
    mcl_df = pd.DataFrame()
    mcl_df['super_cluster'] = c_clusters
    mcl_df['gene_name'] = m_clusters

    if raw_return:
        return mcl_df

    new = mcl_df.explode('gene_name').reset_index().rename(
        columns={'index': 'renewed_super_cluster'})
    new['renewed_super_cluster'] = new['renewed_super_cluster'].apply(lambda x: x+1)
    masters = summary.merge(new, on=['super_cluster', 'gene_name'], how='left')
    masters = masters.sort_values(
        ['renewed_super_cluster', 'core_cluster', 'gene_name']).reset_index(drop=True)
    return masters
