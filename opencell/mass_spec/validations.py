import pandas as pd
import numpy as np
import random
import re
import itertools
import pval_calculation as pval
from itertools import repeat
from multiprocessing import Pool


def create_edg(source_df, target_col, edge_col, save_name):
    """
    creates an .edg file from an interactions df
    """
    source_df = source_df.copy()
    source_df['edge'] = 'EDGE'

    source_df = source_df[['edge', target_col, edge_col]]

    source_df.to_csv(save_name, header=False, index=False, sep='\t')


def create_null_edg(source_df, target_col, edge_col, save_name):
    """
    creates a null-graph that random shuffles the preys
    """
    source_df = source_df.copy()

    prey_col = source_df[target_col].to_list()
    random_preys = random.sample(prey_col, len(prey_col))
    source_df[target_col] = random_preys
    source_df['edge'] = 'EDGE'

    source_df = source_df[['edge', target_col, edge_col]]
    source_df.to_csv(save_name, header=False, index=False, sep='\t')


def get_plate_interactors(pvals, metrics=['pvals'], just_hits=False):
    pvals = pvals.copy()

    pvals.set_index(('gene_names', 'gene_names'), inplace=True)
    pvals.index.name = 'gene_names'
    targets = pvals.columns.get_level_values('baits')
    targets = list(set(targets))

    all_hits = []
    # Get all hits and minor hits along with the metric data
    for target in targets:
        target_pvs = pvals[target]
        if just_hits:
            hits = target_pvs
            hits.reset_index(inplace=True)
        else:
            selection = ['hits', 'minor_hits'] + metrics
            hits = target_pvs[target_pvs['hits'] | target_pvs['minor_hits']][selection]
            hits.reset_index(inplace=True)


        # expand where there are multiple entries in gene names
        multiples = hits[hits['gene_names'].map(lambda x: ';' in x)]
        multiples_idxs = multiples.index.to_list()

        for multiple in multiples_idxs:
            copy_row = hits.iloc[multiple]
            genes = copy_row['gene_names'].split(';')
            for gene in genes:
                add_row = copy_row.copy()
                add_row['gene_names'] = gene
                hits = hits.append(add_row, ignore_index=True)
            hits.drop(multiple, inplace=True)
        hits['target'] = target.upper()
        hits.rename(columns={'gene_names': 'prey'}, inplace=True)
        hits.reset_index(drop=True, inplace=True)
        all_hits.append(hits)

    all_hits = pd.concat(all_hits, axis=0)
    return all_hits


def get_all_interactors(plates, root, date, metrics=['pvals'], name='_pval_and_stoich_',
        just_hits=False):
    pval_plates = []
    for plate in plates:
        df_name = root + plate + name + date + '.pkl'
        pvals = pd.read_pickle(df_name)
        pval_plates.append(pvals)

    multi_args = zip(pval_plates, repeat(metrics), repeat(just_hits))

    # multi processing
    p = Pool()
    plate_hits = p.starmap(get_plate_interactors, multi_args)
    p.close()
    p.join()

    all_hits = pd.concat(plate_hits, axis=0)
    all_hits.reset_index(drop=True, inplace=True)
    if just_hits:
        selection = ['target', 'prey'] + metrics
        all_hits = all_hits[selection]
    else:
        selection = ['target', 'prey', 'hits', 'minor_hits'] + metrics
        all_hits = all_hits[selection]
    all_hits = all_hits.dropna()
    all_hits = all_hits.sort_values(by='target')
    all_hits['plate'] = all_hits['target'].apply(lambda x: x.split('_')[0])
    all_hits['target'] = all_hits['target'].apply(lambda x: x.split('_')[1])

    return all_hits


def fdr_all_interactors(plates, root, date, fdr1, fdr5, metric='pvals'):
    pval_plates = []
    for plate in plates:
        df_name = root + plate + '_pval_and_stoich_' + date + '.pkl'
        pvals = pd.read_pickle(df_name)
        pvals = pval.two_fdrs(pvals, fdr1, fdr5)
        pval_plates.append(pvals)

    multi_args = zip(pval_plates, repeat(metric))

    # multi processing
    p = Pool()
    plate_hits = p.starmap(get_plate_interactors, multi_args)
    p.close()
    p.join()

    all_hits = pd.concat(plate_hits, axis=0)
    all_hits.reset_index(drop=True, inplace=True)
    all_hits = all_hits[['target', 'prey', metric, 'hits', 'minor_hits']]
    all_hits = all_hits.sort_values(by='target')
    return all_hits


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


def calculate_corum_coverage(all_hits, corum):
    """
    Calculate % of total possible corum coverage
    """
    all_hits = all_hits.copy()
    all_hits = all_hits[all_hits['target'] != all_hits['prey']]
    corum = corum.copy()

    targets = set(all_hits['target'].to_list())

    # only select complex in corum if target exists in corum subunits
    corum['in_gene'] = corum['subunits'].apply(check_in_list, args=[targets])
    subcorum = corum[corum['in_gene'].map(lambda x: len(x) > 0)]

    subcorum = subcorum[['ComplexName', 'subunits']]

    subcorum['coverage'] = subcorum['subunits'].apply(find_subunits, args=[all_hits])

    nominator = subcorum['coverage'].apply(lambda x: len(x)).sum()
    denom = subcorum['subunits'].apply(lambda x: len(x)).sum()

    return nominator, denom, 100 * nominator / denom


def check_in_list(x, intersect_genes):
    genes = []
    for gene in x:
        if gene in intersect_genes:
            genes.append(gene)
    return genes


def find_subunits(sub_list, interactions):

    targets = interactions[interactions['target'].isin(sub_list)]
    prey_list = targets['prey'].to_list()

    return list(set(sub_list).intersection(set(prey_list)))


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


def corum_interaction_coverage(network_df, corum, target_col, prey_col, directional=False):
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


def convert_to_unique_interactions(dataset, target_col, prey_col):
    """
    convert bait/prey interactions to unique, directionless interactions using gene names
    """
    dataset = dataset.copy()

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
    interactions.reset_index(drop=True, inplace=True)

    return interactions
