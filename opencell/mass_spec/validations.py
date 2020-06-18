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


def get_plate_interactors(pvals, metric='pvals'):
    pvals = pvals.copy()

    pvals.set_index(('gene_names', 'gene_names'), inplace=True)
    pvals.index.name = 'gene_names'
    targets = pvals.columns.get_level_values('baits')
    targets = list(set(targets))

    all_hits = []
    # Get all hits and minor hits along with the metric data
    for target in targets:
        target_pvs = pvals[target]
        hits = target_pvs[target_pvs['hits'] | target_pvs['minor_hits']][['hits', 'minor_hits', metric]]
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


def get_all_interactors(plates, root, date, metric='pvals'):
    pval_plates = []
    for plate in plates:
        df_name = root + plate + '_pval_and_stoich_' + date + '.pkl'
        pvals = pd.read_pickle(df_name)
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

    return 100 * nominator / denom


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


def calculate_coes_coverage(all_hits, coes):
    """
    calculate proportion of coessential edges
    """

    all_hits = all_hits.copy()
    coes = coes['genes']
    all_hits = all_hits[all_hits['target'] != all_hits['prey']]
    coes_num = 0

    target_list = list(set(all_hits['target']))
    target_list.sort()
    for target in target_list:
        target_edges = set(all_hits[all_hits['target'] == target]['prey'].to_list())
        coes_edges = coes[coes.apply(lambda x: True if target in x else False)].to_list()
        coes_edges = set(list(itertools.chain.from_iterable(coes_edges)))
        intersect = target_edges.intersection(coes_edges)
        intersect_num = len(intersect)
        coes_num += intersect_num

    return 100 * coes_num / all_hits.shape[0]


def calculate_clusterone_coverage(all_hits, cone):
    """
    Calculate how many interactions belong in clusterone complex
    """

    a_hits = all_hits.copy()
    clusters = cone['Members'].apply(lambda x: x.split(' ')).to_list()

    for cluster in clusters:
        members = a_hits[(a_hits['target'].isin(cluster))
            & (a_hits['prey'].isin(cluster))]
        a_hits.drop(members.index, inplace=True)

    total = all_hits.shape[0]
    reduced = a_hits.shape[0]

    return 100 * ((total-reduced) / total)
