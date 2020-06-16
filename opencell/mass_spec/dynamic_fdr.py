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
import pval_calculation as pval
import hack_pvals as hp
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



def get_fdrs(pvals):
    """get dynamic FDR values and recompute new hits"""

    pvals = pvals.copy()

    baits = pvals.columns.get_level_values('baits')
    baits = list(set(baits))
    baits = [bait for bait in baits if bait != 'gene_names']
    selects = []
    for bait in baits:
        selects.append(pvals[bait])
    p = Pool()
    fdr1_seeds = p.map(get_fdr1_seed, selects)
    p.close()
    p.join()

    fdr1_full = [[3, seed] for seed in fdr1_seeds]

    fdr5_args = zip(selects, fdr1_seeds)

    p = Pool()
    fdr5_seeds = p.starmap(get_fdr5_seed, fdr5_args)
    p.close()
    p.join()

    fdr5_full = [[3, seed] for seed in fdr5_seeds]

    fdr_df = pd.DataFrame()
    fdr_df['bait'] = baits
    fdr_df['fdr1'] = fdr1_full
    fdr_df['fdr5'] = fdr5_full
    fdr_df.set_index('bait', inplace=True)

    # Find hits for FDR1 and FDR2
    for bait in baits:
        fdr1 = fdr_df.loc[bait]['fdr1']
        fdr5 = fdr_df.loc[bait]['fdr5']

        bait_pval = pvals[bait]['pvals']
        enrichment = pvals[bait]['enrichment']

        # 1% thresh
        first_thresh = enrichment.apply(hp.calc_thresh,
            args=[fdr1[0], fdr1[1]])

        # 5% thresh
        second_thresh = enrichment.apply(hp.calc_thresh,
            args=[fdr5[0], fdr5[1]])

        pvals[(bait, 'hits')] = np.where(
            (bait_pval > first_thresh), True, False)

        pvals[(bait, 'minor_hits')] = np.where(
            ((bait_pval < first_thresh) & (bait_pval > second_thresh)), True, False)



    pvals.sort_index(axis=1, inplace=True)

    return fdr_df, pvals



def get_fdr1_seed(select):
    neg_select = select[select['enrichment'] < 0]
    # neg_select = neg_select[neg_select['pvals'] < 15]
    # neg_select = neg_select[neg_select['enrichment'] > -4.5]
    seed = 2.5

    hit = hit_count(neg_select, 3, seed)

    if hit > 0:
        # while hit > 0 and seed < 4.4:
        while hit > 0:
            seed += 0.1
            hit = hit_count(neg_select, 3, seed)

    else:
        while hit == 0:
            seed -= 0.1
            hit = hit_count(neg_select, 3, seed)
        seed += 0.1
    return round(seed, 2)


def get_fdr5_seed(select, fdr1_seed):
    neg_select = select[select['enrichment'] < 0]
    # neg_select = neg_select[neg_select['pvals'] < 15]
    # neg_select = neg_select[neg_select['enrichment'] > -4.5]

    pos_select = select[select['enrichment'] > 0]


    seed = fdr1_seed

    neg_hit = hit_count(neg_select, 3, seed)
    pos_hit = hit_count(pos_select, 3, seed)

    pos_perc = 100 * neg_hit / pos_hit

    while (neg_hit < 2 or pos_perc < 10) and seed > 0.1:
        seed -= 0.1
        neg_hit = hit_count(neg_select, 3, seed)
        pos_hit = hit_count(pos_select, 3, seed)
        pos_perc = 100 * neg_hit / pos_hit

    if pos_perc > 10:
        seed += 0.1

    return round(seed, 2)



def hit_count(bait_series, fdr1, fdr2):
    bait_series = bait_series.copy()
    thresh = bait_series['enrichment'].apply(hp.calc_thresh_negs, args=[fdr1, fdr2])
    hit = np.where(bait_series['pvals'] > thresh, True, False)

    return hit.sum()
