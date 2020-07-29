import pandas as pd
import numpy as np
import random
import re
import itertools
import pval_calculation as pval
from itertools import repeat
from multiprocessing import Pool


def delete_single_edges(network_df, target_col, prey_col):
    network_df = network_df.copy()
    network_df = network_df[network_df[target_col] != network_df[prey_col]]
    single = 1
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
        (all_hits['target'].isin(cluster)) & (all_hits['prey'].isin(cluster))]

    haircut_members = []
    for member in cluster:
        membership = cluster_group[
            (cluster_group['target'] == member) | (cluster_group['prey'] == member)]
        members = set(membership['target'].to_list() + membership['prey'].to_list())
        if len(members) > 2:
            haircut_members.append(member)

    return haircut_members
