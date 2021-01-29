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


def pval_enrichment(imputed_df, manual_exclusion, std_enrich=True, mean=False):
    """ Calculate enrichment and pvals for each bait, no automatic removal

    rtype enrichment_df: pd DataFrame
    rtype pval_df: pd DataFrame"""

    imputed_df = imputed_df.copy()

    # iterate through each cluster to generate neg con group
    bait_list = [col[0] for col in list(imputed_df) if col[0] != 'Info']
    bait_list = list(set(bait_list))
    total = len(bait_list)
    baitrange = list(np.arange(total))



    multi_args = zip(bait_list, repeat(imputed_df), baitrange, repeat(total),
        repeat(manual_exclusion), repeat(std_enrich), repeat(mean))

    p = Pool()
    print("P-val calculations..")
    outputs = p.starmap(first_round_pval, multi_args)
    p.close()
    p.join()
    print("Finished!")

    master_df = pd.concat(outputs, axis=1)

    # join gene names to the df
    gene_names = imputed_df[[('Info', 'Protein IDs'), ('Info', 'Gene names')]]
    gene_names.set_index(('Info', 'Protein IDs'), drop=True, inplace=True)
    gene_names.rename(columns={'Info': 'gene_names'}, inplace=True)
    gene_names.rename(columns={'Gene names': 'gene_names'}, inplace=True)


    master_df = pd.concat([master_df, gene_names], axis=1, join='inner')


    return master_df



def first_round_pval(bait, df, num, total, manual_exclusion, std_enrich=True, mean=False):
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
    n_bait_list = [(x, x.split('_', 1)[1]) for x in n_baits]

    # filter every gene that shares the same root
    bait_name = bait.split('_', 1)[1]

    # identify all the genes that are in a corum set
    corums = corum_genes(bait_name, manual_exclusion)

    same_group = []
    same_group.append(bait)
    for gene in n_bait_list:
        if gene[1] in corums:
            same_group.append(gene[0])


    # Convert all values in same groups as np.nans
    for gene in same_group:
        neg_control[gene] = neg_control[gene].where(
            neg_control[gene] > 100, np.nan)

    # calculate the p-values

    # combine values of replicates into one list
    bait_series = temporary[bait].values.tolist()

    # add an index value to the list for locating neg_control indices
    for i in np.arange(len(bait_series)):
        bait_series[i].append(i)

    # perform the p value calculations, with bagging replacement for np.nans
    pval_series = pd.Series(bait_series, index=gene_list, name='pvals')

    pval_series = pval_series.apply(get_pvals, args=[neg_control.T, std_enrich, mean])

    pvals, enrichment = pval_series.apply(lambda x: x[0]), pval_series.apply(lambda x: x[1])
    pvals.name = 'pvals'
    enrichment.name = 'enrichment'

    # Find positive hits from enrichment and pval calculations
    pe_df = pd.concat([pvals, enrichment], axis=1)

    output = pd.concat([pe_df[['enrichment', 'pvals']]], keys=[bait],
        names=['baits', 'values'], axis=1)

    if num % 20 == 0:
        print(str(num) + ' / ' + str(total) + ' baits processed')

    return output



def get_pvals(x, control_df, std_enrich, mean=False):
    """This is an auxillary function to calculate p values
    that is used in enrichment_pval_dfs function

    rtype: pval float"""

    # get the index to access the right set of control intensities
    row = x[-1]
    neg_con = control_df[row].values.tolist()
    pval = scipy.stats.ttest_ind(x[:-1], control_df[row].values.tolist(),
    nan_policy='omit')[1]

    # negative log of the pvals
    pval = -1 * np.log10(pval)


    # calculate enrichment
    if std_enrich:
        std = np.nanstd(neg_con)
        if mean:
            enrichment = (np.nanmean(x[:-1]) - np.nanmean(neg_con)) / std
        else:
            enrichment = (np.nanmedian(x[:-1]) - np.nanmedian(neg_con)) / std


    else:
        if mean:
            enrichment = (np.nanmean(x[:-1]) - np.nanmean(neg_con))
        else:
            enrichment = (np.nanmedian(x[:-1]) - np.nanmedian(neg_con))

    return [pval, enrichment]



def get_pvals_bagging(x, control_df, std_enrich):
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
        if std_enrich:
            enrichment = (np.median(sample) - np.median(neg_con)) / std

        else:
            enrichment = (np.median(sample) - np.median(neg_con))

        return [pval, enrichment]


def corum_genes(gene, human_corum):
    """get a list of all corum interactors"""

    # find all the rows that contains the specific gene
    bait_df = human_corum[human_corum['subunits'].map(lambda x: gene in x)]

    # get a set of all known interactors
    interactors = bait_df['subunits'].to_list()
    interactions = list(itertools.chain.from_iterable(interactors))
    interactions = list(set(interactions))

    return interactions
