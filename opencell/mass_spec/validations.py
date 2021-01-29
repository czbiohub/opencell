import pandas as pd
import numpy as np
import dynamic_fdr as dfdr
import random
import re
import itertools
import pval_calculation as pval
from itertools import repeat
from multiprocessing import Pool
from node2vec import Node2Vec
import networkx as nx


def create_edg(source_df, target_col, edge_col, save_name):
    """
    creates an .edg file from an interactions df. Used for compression analysis.
    """
    source_df = source_df.copy()
    source_df['edge'] = 'EDGE'

    source_df = source_df[['edge', target_col, edge_col]]

    source_df.to_csv(save_name, header=False, index=False, sep='\t')


def create_null_edg(source_df, target_col, edge_col, save_name):
    """
    creates a null-graph that random shuffles the preys. Used for compression analysis
    """
    source_df = source_df.copy()

    prey_col = source_df[target_col].to_list()
    random_preys = random.sample(prey_col, len(prey_col))
    source_df[target_col] = random_preys
    source_df['edge'] = 'EDGE'

    source_df = source_df[['edge', target_col, edge_col]]
    source_df.to_csv(save_name, header=False, index=False, sep='\t')


def hit_bool_cat(distance):

    if distance == np.inf:
        return 0.2

    elif distance < 0.01:
        return 0.2
    elif distance > 0:
        return 2.2
    else:
        return np.log10(distance) + 2.2


def prep_all_hits_clusterone(all_hits, metric, hit_bools=True):
    """
    prep standard all_hits table for clustering analysis
    """

    all_hits = all_hits.copy()

    # remove plate headers from target
    all_hits['target'] = all_hits['target'].apply(lambda x: x.split('_')[1])

    # Just select target, prey, and metric cols
    all_hits = all_hits[['target', 'prey', metric]]


    # apply hit_bools
    if hit_bools:
        all_hits[metric] = all_hits[metric].apply(hit_bool_cat)

    all_hits = all_hits[all_hits[metric] != 0]
    # Remove duplicates, just save the max value
    all_hits = all_hits.groupby(['target', 'prey'])['interaction_stoi'].max().reset_index()

    return all_hits


def spatial_distance(network, spatial, target_col, prey_col):
    """
    calculate the spatial distance between two interactors
    """
    network = network.copy()
    spatial = spatial.copy()

    # Limit network to genes found in spatial df
    selected = network[
        (network[target_col].isin(spatial['Gene names'])) & (
            network[prey_col].isin(spatial['Gene names']))]

    targets = selected[target_col].to_list()
    preys = selected[prey_col].to_list()
    multi_targets = zip(targets, repeat(spatial))
    multi_preys = zip(preys, repeat(spatial))

    p = Pool()
    target_umap = p.starmap(retrieve_umap, multi_targets)
    p.close()
    p.join()

    p = Pool()
    prey_umap = p.starmap(retrieve_umap, multi_preys)
    p.close()
    p.join()

    dists = []
    for i in range(len(target_umap)):
        dists.append(np.linalg.norm(target_umap[i] - prey_umap[i]))

    return dists


def retrieve_umap(target, spatial):

    spatial = spatial.copy()
    selected = spatial[spatial['Gene names'] == target]
    umap_1 = selected['umap_1'].mean()
    umap_2 = selected['umap_2'].mean()

    return np.array([umap_1, umap_2])



def calculate_coes_coverage(all_hits, coes, target_col, prey_col):
    """
    calculate proportion of coessential edges
    """

    all_hits = all_hits.copy()
    coes = coes['genes']
    all_hits = all_hits[all_hits[target_col] != all_hits[prey_col]]
    coes_num = 0

    target_list = list(set(all_hits[target_col]))
    target_list.sort()
    for target in target_list:
        target_edges = set(all_hits[all_hits[target_col] == target][prey_col].to_list())
        coes_edges = coes[coes.apply(lambda x: True if target in x else False)].to_list()
        coes_edges = set(list(itertools.chain.from_iterable(coes_edges)))
        intersect = target_edges.intersection(coes_edges)
        intersect_num = len(intersect)
        coes_num += intersect_num

    return coes_num, 100 * coes_num / all_hits.shape[0]


def calculate_clusterone_coverage(all_hits, cone, target_col, prey_col):
    """
    Calculate how many interactions belong in clusterone complex
    """

    a_hits = all_hits.copy()
    clusters = cone['Members'].apply(lambda x: x.split(' ')).to_list()

    for cluster in clusters:
        members = a_hits[(a_hits[target_col].isin(cluster))
            & (a_hits[prey_col].isin(cluster))]
        a_hits.drop(members.index, inplace=True)

    total = all_hits.shape[0]
    reduced = a_hits.shape[0]

    return 100 * ((total-reduced) / total)


def return_colocalized_df(source_df, colocal_df, target_col, prey_col):
    """
    merge mnc_classifier from colocal_df
    and return df where target and prey are colocalized
    """
    source_df = source_df[[target_col, prey_col]]
    source_df = source_df[source_df[target_col] != source_df[prey_col]]
    colocal_df = colocal_df.copy()

    colocal_df['mnc_classifier'] = colocal_df['mnc_classifier'].apply(
        lambda x: x.split('/'))

    # make target and prey merges with localization data
    merge1 = source_df.merge(colocal_df.rename(
        columns={'gene_names': target_col, 'mnc_classifier': 'target_localization'}),
        on=target_col, how='inner')
    merge2 = merge1.merge(colocal_df.rename(
        columns={'gene_names': prey_col, 'mnc_classifier': 'prey_localization'}),
        on=prey_col, how='inner')


    intersections = []
    for i, row in merge2.iterrows():
        target = set(row.target_localization)
        prey = set(row.prey_localization)
        if len(target.intersection(prey)) > 0:
            intersections.append(i)
        elif 'B' in target or 'B' in prey:
            intersections.append(i)

    return merge2, merge2.loc[intersections]


def return_hek_colocalized_df(source_df, colocal_df, target_col, prey_col):
    """

    """
    source_df = source_df[[target_col, prey_col]]
    source_df = source_df[source_df[target_col] != source_df[prey_col]]

    # make target and prey merges with localization data
    merge1 = source_df.merge(colocal_df.rename(
        columns={'gene_names': target_col, 'localization': 'target_localization'}),
        on=target_col, how='inner')
    merge2 = merge1.merge(colocal_df.rename(
        columns={'gene_names': prey_col, 'localization': 'prey_localization'}),
        on=prey_col, how='inner')

    intersections = []
    for i, row in merge2.iterrows():
        target = set(row.target_localization)
        prey = set(row.prey_localization)
        if len(target.intersection(prey)) > 0:
            intersections.append(i)
        elif 'B' in target or 'B' in prey:
            intersections.append(i)

    return merge2, merge2.loc[intersections]


def corum_marginals(network_df, corum, target_col, prey_col):
    """
    calculate db's coverage of possible corum interactions
    """

    network_df = network_df[[target_col, prey_col]]
    corum = corum.copy()

    targets = list(set(network_df[target_col].to_list()))

    coverages = []
    for target in targets:
        # get all the corum interactions possible with the targets
        left_corum = corum[corum['prot_1'] == target]
        right_corum = corum[corum['prot_2'] == target]

        network_target = network_df[network_df[target_col] == target]
        network_preys = set(network_target[prey_col].to_list())

        left_corum = left_corum[left_corum['prot_2'].isin(network_preys)]
        right_corum = right_corum[right_corum['prot_1'].isin(network_preys)]

        coverages.append(left_corum.shape[0] + right_corum.shape[0])


    return targets, coverages


def corum_interaction_coverage(
        network_df, corum, target_col, prey_col, directional=False, no_target=False):
    """
    calculate db's coverage of possible corum interactions
    """

    network_df = network_df[[target_col, prey_col]]
    corum = corum.copy()

    # get a list of all unique targets in the ppi network
    targets = set(network_df[target_col].to_list())
    if no_target:
        targets = set(network_df[target_col].to_list() + network_df[prey_col].to_list())

    # get all the corum interactions possible with the targets
    if directional:
        overlap_sum = 0
    else:
        overlap_corum = corum[(corum['prot_1'].isin(targets)) | (corum['prot_2'].isin(targets))]
        overlap_sum = overlap_corum.shape[0]


    coverage_sum = 0
    for target in targets:
        # get all the corum interactions possible with the targets
        left_corum = corum[corum['prot_1'] == target]
        right_corum = corum[corum['prot_2'] == target]

        if directional:
            overlap_sum += left_corum.shape[0] + right_corum.shape[0]

        network_target = network_df[network_df[target_col] == target]
        network_preys = set(network_target[prey_col].to_list())

        left_corum = left_corum[left_corum['prot_2'].isin(network_preys)]
        right_corum = right_corum[right_corum['prot_1'].isin(network_preys)]

        coverage_sum += left_corum.shape[0] + right_corum.shape[0]

        if not directional:
            # delete covered interactions
            left_idxs = left_corum.index.to_list()
            right_idxs = right_corum.index.to_list()
            drop_idxs = left_idxs + right_idxs
            corum.drop(drop_idxs, inplace=True)

    return coverage_sum, overlap_sum


def corum_precision(network, corum, target_col, prey_col):
    """
    Calculates corum precisions by filtering for all interactions
    where both interactors belong to a CORUM list of members
    and calculating precision of those that are actual corum interactors
    """
    network = network[[target_col, prey_col]]
    corum = corum.copy()

    corum_genes = set(corum['prot_1'].to_list() + corum['prot_2'].to_list())

    # Get all the interactions where both interactors are in corum set
    network = network[
        (network[target_col].isin(corum_genes))
        & (network[prey_col].isin(corum_genes))]

    network['precision_genes'] = network.values.tolist()
    network['precision'] = network['precision_genes'].apply(
        aux_corum_precision, args=[corum, ]
    )
    return network



def aux_corum_precision(target_prey, corum):
    """
    Auxillary function to corum_precision, matches whether an interaction
    exists in corum set
    """
    target, prey = target_prey[0], target_prey[1]

    # leftside search
    left_corum = corum[corum['prot_1'] == target]
    if prey in left_corum['prot_2'].to_list():
        return True

    # rightside search
    right_corum = corum[corum['prot_2'] == target]
    if prey in right_corum['prot_1'].to_list():
        return True

    return False


def corum_interaction_coverage_2(network_df, corum, target_col, prey_col,
        distance=True, directional=False):
    """
    calculate db's coverage of possible corum interactions
    """

    network_df = network_df[[target_col, prey_col]]
    corum = corum.copy()

    # get a list of all unique targets in the ppi network
    targets = set(network_df[target_col].to_list())

    # get all the corum interactions possible with the targets
    if directional:
        overlap_sum = 0
    else:
        overlap_corum = corum[(corum['prot_1'].isin(targets)) | (corum['prot_2'].isin(targets))]
        overlap_sum = overlap_corum.shape[0]

    uncovered_dict = {}
    coverage_sum = 0
    for target in targets:
        # get all the corum interactions possible with the targets
        left_corum = corum[corum['prot_1'] == target]
        right_corum = corum[corum['prot_2'] == target]

        if directional:
            overlap_sum += left_corum.shape[0] + right_corum.shape[0]

        network_target = network_df[network_df[target_col] == target]
        network_preys = set(network_target[prey_col].to_list())

        left_covered = left_corum[left_corum['prot_2'].isin(network_preys)]
        right_covered = right_corum[right_corum['prot_1'].isin(network_preys)]

        if distance:
            left_preys = left_covered['prot_2'].to_list()
            right_preys = right_covered['prot_1'].to_list()

            left_targets = targets.intersection(left_preys)
            right_targets = targets.intersection(right_preys)

            new_targets = left_targets.union(right_targets)
            new_targets.add(target)

            expanded_target = network_df[network_df[target_col].isin(new_targets)]
            expanded_preys = set(expanded_target[prey_col].to_list())

            left_covered = left_corum[left_corum['prot_2'].isin(expanded_preys)]
            right_covered = right_corum[right_corum['prot_1'].isin(expanded_preys)]


        left_uncovered = left_corum.drop(left_covered.index.to_list())
        right_uncovered = right_corum.drop(right_covered.index.to_list())

        uncovered = left_uncovered['prot_2'].to_list() + right_uncovered['prot_1'].to_list()
        if len(uncovered) > 0:
            uncovered_dict[target] = uncovered
        coverage_sum += left_covered.shape[0] + right_covered.shape[0]

        if not directional:
            # delete covered interactions
            left_idxs = left_covered.index.to_list()
            right_idxs = right_covered.index.to_list()
            drop_idxs = left_idxs + right_idxs
            corum.drop(drop_idxs, inplace=True)

    return coverage_sum, overlap_sum, uncovered_dict


def groupby_max(interactions, target_col, prey_col, edge_col):
    """
    group by target and prey and return max of edge weight
    """
    interactions = interactions.copy()
    interactions = interactions[[target_col, prey_col, edge_col]]
    interactions = interactions.sort_values(
        edge_col, ascending=False).drop_duplicates([target_col, prey_col])
    interactions.sort_values([target_col, prey_col], inplace=True)
    interactions.reset_index(drop=True, inplace=True)

    return interactions


def convert_to_unique_interactions(dataset, target_col, prey_col, target_match=False,
        get_edge=False, edge='pvals'):
    """
    convert bait/prey interactions to unique, directionless interactions using gene names
    """
    dataset = dataset.copy()

    if not target_match:
        dataset = dataset[dataset[target_col] != dataset[prey_col]]
    original = dataset.copy()

    # combine values from two columns to a list and sort alphabetically
    dataset = dataset[[target_col, prey_col]]
    combined = pd.Series(dataset.values.tolist())

    combined = combined.apply(sorted)

    combined_list = combined.to_list()

    # Unzip the sorted interactions and create them into two lists
    unzipped = list(zip(*combined_list))

    first, second = unzipped[0], unzipped[1]

    # Generate a sorted interaction dataframe and drop duplicates
    interactions = pd.DataFrame()
    interactions['prot_1'] = first
    interactions['prot_2'] = second

    interactions.drop_duplicates(inplace=True)

    if get_edge:
        vals = []
        for i, row in interactions.iterrows():
            prot_1 = row.prot_1
            prot_2 = row.prot_2
            prots = [prot_1, prot_2]
            selection = original[
                (original[target_col].isin(prots)) & original[prey_col].isin(prots)]
            max_edge = selection[edge].max()
            vals.append(max_edge)
        interactions[edge] = vals
    interactions.reset_index(drop=True, inplace=True)

    return interactions


def convert_to_node2vec(interactions, dimensions, target_col, prey_col, edge_col):
    """
    convert df of interactions into featurized nodes using node2vec in DF form
    """
    interactions = interactions.copy()
    interactions = groupby_max(interactions, target_col, prey_col, edge_col)

    # create networkx graph
    graph = nx.convert_matrix.from_pandas_edgelist(
        interactions, target_col, prey_col, edge_attr=edge_col)

    # featurize and convert to node2vec
    node2vec = Node2Vec(
        graph, dimensions=512, walk_length=30, num_walks=200, workers=8, quiet=True)

    model = node2vec.fit(window=10, min_count=1, batch_words=4)

    # convert to pandas (some word2vec terminologies in the code)
    ordered_nodes = [(term, voc.index, voc.count) for term, voc in model.wv.vocab.items()]
    ordered_nodes = sorted(ordered_nodes, key=lambda k: k[2])
    ordered_terms, term_indices, term_counts = zip(*ordered_nodes)

    # featurized df
    node_vectors = pd.DataFrame(model.wv.syn0[term_indices, :], index=ordered_terms)

    return node_vectors


def return_circle_uniques(all_hits, major_circle=0.2, minor_circle=0.05, unique=False):
    """make circle parameters for all hits table for clustering purposes"""

    all_hits = all_hits.copy()
    all_hits['circle'] = (all_hits['abundance_stoi'] > 0.1) & (
        all_hits['abundance_stoi'] < 10) & (
        all_hits['interaction_stoi'] > major_circle)
    all_hits['circle'] = all_hits['circle'].apply(lambda x:
        10 if x else 0)


    all_hits['lg_circle'] = (all_hits['abundance_stoi'] > 0.1) & (
        all_hits['abundance_stoi'] < 10) & (
        all_hits['interaction_stoi'] > 0.05) & (
        all_hits['interaction_stoi'] < 0.2)
    all_hits['lg_circle'] = all_hits['lg_circle'].apply(lambda x:
        4 if x else 0)


    all_hits['circle_stoi'] = all_hits['circle'] + all_hits['lg_circle']
    all_hits['circle_stoi'] = all_hits['circle_stoi'].apply(
        lambda x: 0.2 if x == 0 else x)

    all_hits['target'] = all_hits['target'].astype(str)
    all_hits['prey'] = all_hits['prey'].astype(str)


    if unique:
        circle = convert_to_unique_interactions(all_hits, 'target', 'prey', get_edge=True,
            edge='circle_stoi')

        return circle
    else:
        return all_hits
