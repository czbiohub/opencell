import urllib.parse
import urllib.request
import sys
import pdb
import collections
import multiprocessing
import itertools
import scipy
import random
import re
import pandas as pd
import numpy as np
import pyseus as pys
from multiprocessing import Queue
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from itertools import repeat
from multiprocessing import Pool
from scipy.spatial.distance import pdist
from scipy.spatial.distance import squareform
from scipy.stats import percentileofscore
from sklearn.metrics.pairwise import cosine_similarity


def hack_remove_significants(imputed_df, thresh, fc_vars2, human_corum):
    """ Calculate enrichment and pvals for each bait, but remove baits that
    show up as significant hits and iterate continuously until
    no more removable baits are found.

    rtype enrichment_df: pd DataFrame
    rtype pval_df: pd DataFrame"""

    imputed_df = imputed_df.copy()

    # iterate through each cluster to generate neg con group
    bait_list = [col[0] for col in list(imputed_df) if col[0] != 'Info']
    bait_list = list(set(bait_list))
    total = len(bait_list)
    baitrange = list(np.arange(total))



    multi_args = zip(bait_list, repeat(imputed_df), baitrange, repeat(total),
        repeat(thresh), repeat(human_corum))

    p = Pool()
    print("First round p-val calculations..")
    neg_dfs = p.starmap(first_round_pval, multi_args)
    p.close()
    p.join()
    master_neg = pd.concat(neg_dfs, axis=1)
    print("First round finished!")

    return_neg = master_neg.copy()
    master_neg.reset_index(inplace=True, drop=True)

    fc_var1, fc_var2 = fc_vars2[0], fc_vars2[1]

    multi_args2 = zip(bait_list, repeat(imputed_df), repeat(master_neg),
        baitrange, repeat(total), repeat(fc_var1), repeat(fc_var2), repeat(human_corum))

    p = Pool()
    outputs = p.starmap(second_round_pval, multi_args2)

    master_df = pd.concat(outputs, axis=1)

    # join gene names to the df
    gene_names = imputed_df[[('Info', 'Protein IDs'), ('Info', 'Gene names')]]
    gene_names.set_index(('Info', 'Protein IDs'), drop=True, inplace=True)
    gene_names.rename(columns={'Info': 'gene_names'}, inplace=True)
    gene_names.rename(columns={'Gene names': 'gene_names'}, inplace=True)


    master_df = pd.concat([master_df, gene_names], axis=1, join='inner')


    return master_df, return_neg


def find_root(bait):
    """regular expression func to find root of genes"""

    # check for RE in genes that have A/B/C endings e.g. CCT6A/CCT6B
    letter_ending = re.search(r'(.+?)\d+[A-Z]+$', bait)
    if letter_ending:
        return letter_ending.groups()[0]

    # regular endings that end in number or just the gene
    return re.search(r'(.+?)\d*$', bait).groups()[0]



def first_round_pval(bait, df, num, total, thresh, human_corum):
    """ A first round of pval calculations to remove any significant hits
    from negative controls """

    # initiate other variables required for the fx
    gene_list = df[('Info', 'Protein IDs')].tolist()

    # construct a negative control
    temporary = df.copy()
    neg_control = df.copy()
    temporary.drop('Info', level='Baits', inplace=True, axis=1)
    neg_control.drop('Info', level='Baits', inplace=True, axis=1)

    # retrieve all gene names in baits
    n_baits = list(set([x[0] for x in list(neg_control)]))

    # n_bait_list composed of (real_col_name, gene_name)
    n_bait_list = [(x, x.split('_')[1]) for x in n_baits]

    # filter every gene that shares the same root
    bait_name = bait.split('_')[1]
    root = find_root(bait_name)

    # identify all the genes that are in a corum set
    corums = corum_genes(bait_name, human_corum)

    same_group = []
    for gene in n_bait_list:
        gene_root = find_root(gene[1])
        if gene_root == root or gene in corums:
            same_group.append(gene[0])

        # Exception hack for POLR and MEDs
        if root == 'MED':
            if gene_root == 'POLR':
                same_group.append(gene[0])
        if root == 'POLR':
            if gene_root == 'MED':
                same_group.append(gene[0])



    # Convert all values in same groups as np.nans
    for gene in same_group:
        neg_control[gene] = neg_control[gene].where(
            neg_control[gene] > 100, np.nan)


    # # calculate the neg con median and stds
    # con_median = neg_control.median(axis=1)
    # con_std = neg_control.std(axis=1)

    # # calculate enrichment
    # enrich_series = (temporary[bait].median(axis=1) - con_median) / con_std
    # enrich_series.index = gene_list
    # enrich_series.name = 'enrichment'

    # calculate the p-values

    # combine values of replicates into one list
    bait_series = temporary[bait].values.tolist()

    # copy a bait series that will be returned with removed hits
    neg_series = temporary[bait].copy()
    neg_series.index = gene_list
    neg_series.columns = pd.MultiIndex.from_product([[bait], neg_series.columns])

    # add an index value to the list for locating neg_control indices
    for i in np.arange(len(bait_series)):
        bait_series[i].append(i)

    # perform the p value calculations, with bagging replacement for np.nans
    pval_series = pd.Series(bait_series, index=gene_list, name='pvals')
    pval_series = pval_series.apply(get_pvals_bagging, args=[neg_control.T])

    pvals, enrichment = pval_series.apply(lambda x: x[0]), pval_series.apply(lambda x: x[1])
    pvals.name = 'pvals'
    enrichment.name = 'enrichment'

    # Find positive hits from enrichment and pval calculations
    pe_df = pd.concat([pvals, enrichment], axis=1)
    pe_df = pe_df[pe_df['enrichment'] > 0]
    pe_df['hits'] = np.where((pe_df['pvals'] > thresh), True, False)

    # Get genes names of all the hits
    hits = set(pe_df[pe_df['hits']].index.tolist())

    # Remove hits from the negative control
    replicates = list(neg_series)

    for rep in replicates:
        for hit in hits:
            neg_series[rep][hit] = np.nan

    if num % 20 == 0:
        print(str(num) + ' / ' + str(total) + ' baits processed')
    # print(str(num) + ' / ' + str(total) + ' baits processed')

    return neg_series


def second_round_pval(bait, df, neg_control, num, total, fc_var1, fc_var2, human_corum):
    """ A first round of pval calculations to remove any significant hits
    from negative controls """

    # initiate other variables required for the fx
    gene_list = df[('Info', 'Protein IDs')].tolist()

    # construct a negative control
    temporary = df.copy()
    neg_control = neg_control.copy()
    temporary.drop('Info', level='Baits', inplace=True, axis=1)

    # retrieve all gene names in baits
    n_baits = list(set([x[0] for x in list(neg_control)]))

    # n_bait_list composed of (real_col_name, gene_name)
    n_bait_list = [(x, x.split('_')[1]) for x in n_baits]

    # filter every gene that shares the same root
    bait_name = bait.split('_')[1]
    root = find_root(bait_name)

    # identify all the genes that are in a corum set
    corums = corum_genes(bait_name, human_corum)

    same_group = []
    for gene in n_bait_list:
        gene_root = find_root(gene[1])
        if gene_root == root or gene in corums:
            same_group.append(gene[0])

        # Exception hack for POLR and MEDs
        if root == 'MED':
            if gene_root == 'POLR':
                same_group.append(gene[0])
        if root == 'POLR':
            if gene_root == 'MED':
                same_group.append(gene[0])

    # Convert all values in same groups as np.nans

    for gene in same_group:
        neg_control[gene] = neg_control[gene].where(
            neg_control[gene] > 100, np.nan)


    # # calculate the neg con median and stds
    # con_median = neg_control.median(axis=1)
    # con_std = neg_control.std(axis=1)

    # # calculate enrichment
    # enrich_series = (temporary[bait].median(axis=1) - con_median) / con_std
    # enrich_series.index = gene_list
    # enrich_series.name = 'enrichment'


    # calculate the p-values

    # combine values of replicates into one list
    bait_series = temporary[bait].values.tolist()

    # add an index value to the list for locating neg_control indices
    for i in np.arange(len(bait_series)):
        bait_series[i].append(i)

    # perform the p value calculations, with bagging replacement for np.nans
    pval_series = pd.Series(bait_series, index=gene_list, name='pvals')
    pval_series = pval_series.apply(get_pvals_bagging, args=[neg_control.T])

    pvals, enrichment = pval_series.apply(lambda x: x[0]), pval_series.apply(lambda x: x[1])
    pvals.name = 'pvals'
    enrichment.name = 'enrichment'

    # Find positive hits from enrichment and pval calculations
    pe_df = pd.concat([pvals, enrichment], axis=1)
    pe_df['thresh'] = pe_df['enrichment'].apply(calc_thresh,
        args=[fc_var1, fc_var2])
    pe_df['hits'] = np.where((pe_df['pvals'] > pe_df['thresh']), True, False)

    output = pd.concat([pe_df[['enrichment', 'pvals', 'hits']]], keys=[bait],
        names=['baits', 'values'], axis=1)
    if num % 20 == 0:
        print(str(num) + ' / ' + str(total) + ' baits processed')
    # print(str(num) + ' / ' + str(total) + ' baits processed')

    return output


def get_pvals(x, control_df):
    """This is an auxillary function to calculate p values
    that is used in enrichment_pval_dfs function

    rtype: pval float"""

    # get the index to access the right set of control intensities
    row = x[-1]
    pval = scipy.stats.ttest_ind(x[:-1], control_df[row].values.tolist(),
    nan_policy='omit')[1]

    # negative log of the pvals
    pval = -1 * np.log10(pval)

    return pval


def get_pvals_bagging(x, control_df):
    """This is an auxillary function to calculate p values
    that is used in enrichment_pval_dfs function

    rtype: pval float"""

    # get the index to access the right set of control intensities
    row = x[-1]
    con = np.array(control_df[row].values.tolist())
    orig_len = len(con)

    # drop all the nans
    con_dropped = tuple(con[~np.isnan(con)])
    neg_con = list(con_dropped)

    # keep bagging from leftover values after nan-drop until
    # original size is met
    if len(neg_con) < 9:
        return [np.random.uniform(0, 0.2), np.random.uniform(-0.1, 0.1)]

    else:
        neg_con = np.random.choice(neg_con, size=orig_len)

        mean = np.mean(neg_con)
        std = np.std(neg_con)


        sample = x[:-1]

        sample = [mean if np.isnan(x) else x for x in sample]


        # calculate pvals
        pval = scipy.stats.ttest_ind(sample, neg_con,
        nan_policy='omit')[1]

        # negative log of the pvals
        pval = -1 * np.log10(pval)

        # calculate enrichment
        enrichment = (np.median(sample) - np.median(neg_con)) / std

        return [pval, enrichment]


def calc_thresh(enrich, fc_var1, fc_var2):
    """simple function to get FCD thresh to recognize hits"""

    if enrich < fc_var2:
        return np.inf

    elif (enrich == 0) & (fc_var2 == 0):
        return np.inf

    else:
        return fc_var1 / (abs(enrich) - fc_var2)


def calc_thresh_negs(enrich, fc_var1, fc_var2):
    """simple function to get FCD thresh to recognize hits"""
    if abs(enrich) < fc_var2:
        return np.inf
    else:
        return fc_var1 / (abs(enrich) - fc_var2)


def corum_genes(gene, human_corum):
    """get a list of all corum interactors"""

    # find all the rows that contains the specific gene
    bait_df = human_corum[human_corum['subunits'].map(lambda x: gene in x)]

    # get a set of all known interactors
    interactors = bait_df['subunits'].to_list()
    interactions = list(itertools.chain.from_iterable(interactors))
    interactions = list(set(interactions))

    return interactions


def penalty_factor(pvals, master_neg, m_imputed):
    """Apply Marco's penalty factors to enrichments"""

    pvals = pvals.copy()
    master_neg = master_neg.copy()
    m_imputed = m_imputed.copy()

    # calculate median of the negative control copy
    neg_medians = master_neg.median(axis=1)

    # calculate median intensity of the m_imputed baits
    medians = pys.median_replicates(m_imputed, save_info=True, col_str='')
    medians.drop(columns=[
        'Protein names',
        'Majority protein IDs',
        'Gene names',
        'Fasta headers'], inplace=True)
    medians.set_index('Protein IDs', inplace=True)

    # calculate penalty factor for each target

    penalties = {}
    for col in list(medians):
        penalties[col] = medians[col].corr(neg_medians)

    penalty_factor = pd.Series(penalties)
    pf_median = penalty_factor.median()

    penalty_factor = penalty_factor.apply(lambda x: (x/pf_median)**2)

    # Apply the penalty factor to
    for col in penalty_factor.index.to_list():
        pvals[(col, 'enrichment')] = pvals[(col, 'enrichment')] * penalty_factor[col]

    return pvals
