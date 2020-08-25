import pandas as pd
import numpy as np
import random
import re
import itertools
import markov_clustering as mc
import networkx as nx
import pval_calculation as pval
from itertools import repeat
from multiprocessing import Pool


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
