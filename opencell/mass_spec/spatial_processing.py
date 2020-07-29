import pyseus as pys
import urllib.parse
import urllib.request
import sys
import pdb
import collections
import multiprocessing
import scipy
import re
import pandas as pd
import numpy as np
from itertools import repeat
from multiprocessing import Pool
from multiprocessing import Queue
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
from scipy.spatial.distance import pdist
from scipy.spatial.distance import squareform
from scipy.stats import percentileofscore


def spatial_raw_file(file_name, identity=True, filter_rows=True, find_gene_names=True, verbose=True):
    """ Reads the raw data file, remove unnecessary columns,
    filter rows that have been flagged as questionable,
    merge duplicate bait columns using max function
    and return a streamlined data frame
    rtype: pd DataFrame"""

    # convert raw file to a DataFrame
    if verbose:
        print('Reading ' + file_name + '...')
    ms_df = pd.read_csv(file_name, sep='\t', header=0, low_memory=False)

    # retrieve column names from the df
    col_names = list(ms_df)

    # filter rows that do not meet the QC
    if filter_rows:
        pre_filter = ms_df.shape[0]

        # remove rows with potential contaminants
        ms_df = ms_df[ms_df['Potential contaminant'].isna()]

        # remove rows only identified by site
        ms_df = ms_df[ms_df['Only identified by site'].isna()]

        # remove rows that are reverse seq
        ms_df = ms_df[ms_df['Reverse'].isna()]

        filtered = pre_filter - ms_df.shape[0]
        if verbose:
            print("Filtered " + str(filtered) + ' of '
                  + str(pre_filter) + ' rows. Now '
                  + str(ms_df.shape[0]) + ' rows.')

    # start a new list of cols that will be included in the new df

    selected_cols = ['Protein IDs', 'Majority protein IDs', 'Protein names',
        'Gene names', 'Fasta headers']

    # select intensity_cols
    intensity_cols = pys.select_intensity_cols(col_names, 'intensity')
    if identity:
        identity_cols = pys.select_intensity_cols(col_names, 'identification type')
        selected_cols = selected_cols + intensity_cols + identity_cols
    else:
        selected_cols = selected_cols + intensity_cols

    # filter unwanted columns from the df
    ms_df.drop(columns=['Intensity'], inplace=True)
    ms_df = ms_df[selected_cols]


    # Fill in missing gene names
    if find_gene_names:
        ms_df = pys.find_missing_names(ms_df, verbose=verbose)

    return ms_df


def total_intensity_normalization(spatial_df):
    """
    normalize every intensity column, with assumption that total intensity
    should be same, as MS input are identical
    """

    spatial_df = spatial_df.copy()
    intensity_cols = [x for x in list(spatial_df) if 'Intensity' in x]
    norm_df = spatial_df[intensity_cols]

    norms = norm_df.sum()
    norms = norms / norms.min()

    for col in intensity_cols:
        spatial_df[col] = norms[col] * spatial_df[col]

    return spatial_df


def yield_normalization(spatial_df, yield_df):
    """
    Multiply each column by yield fraction
    """

    spatial_df = spatial_df.copy()
    yield_df = yield_df.T
    intensity_cols = [x for x in list(spatial_df) if 'Intensity' in x]
    for col in intensity_cols:
        spatial_df[col] = spatial_df[col] * yield_df[col].item()

    return spatial_df


def convert_noc(spatial_df, num_reps):
    """
    convert columns to nuclear, organellar, cytoplasmic from spatial_df
    """
    spatial_df = spatial_df.copy()

    intensity_cols = [x for x in list(spatial_df) if 'Intensity' in x]
    nuc_cols = [x for x in intensity_cols if '01K' in x]
    cyto_cols = [x for x in intensity_cols if 'Cyt' in x]

    nuc_rename = {}
    cyt_rename = {}

    # new dict for new nuclear cols
    for col in nuc_cols:
        rep = re.search(r'.*(Rep\d).*', col).groups()[0]
        new_col = rep + '_nuclear'
        nuc_rename[col] = new_col

    # new dict for new cytosol cols
    for col in cyto_cols:
        rep = re.search(r'.*(Rep\d).*', col).groups()[0]
        new_col = rep + '_cyto'
        cyt_rename[col] = new_col

    spatial_df.rename(columns=nuc_rename, inplace=True)
    spatial_df.rename(columns=cyt_rename, inplace=True)

    # get organellar cols
    org_cols = set(intensity_cols) - set(nuc_cols)
    org_cols = org_cols - set(cyto_cols)
    org_cols = list(org_cols)

    # sum organellar cols into one col and replace in spatial_df
    for i in np.arange(1, num_reps+1):
        rep = 'Rep' + str(i)
        rep_cols = [x for x in org_cols if rep in x]
        org_df = spatial_df[rep_cols]
        org_intensities = org_df.sum(axis=1)
        spatial_df.drop(columns=rep_cols, inplace=True)
        spatial_df[rep + '_organellar'] = org_intensities

    spatial_df.sort_index(axis=1, inplace=True)
    return spatial_df


def group_replicates(noc_df, rep_re=r'(Rep\d)_(.*)'):
    """Group the replicates of intensities into replicate groups
    rtype df: pd dataframe"""

    noc_df = noc_df.copy()
    # get col names
    col_names = list(noc_df)

    # using a dictionary, group col names into replicate groups
    group_dict = {}
    rename = {}
    for col in col_names:
        # search REs of the replicate ID, and get the group names

        # search if the col is for intensity values
        intensity_search = re.search(rep_re, col,
            flags=re.IGNORECASE)

        # if so, get the group name and add to the group dict
        # use groups from re.search to customize group names
        if intensity_search:
            group_name = intensity_search.groups()[0]
            fraction = intensity_search.groups()[1]
            group_dict[col] = group_name
            rename[col] = fraction

        # if not, group into 'Info'
        else:
            group_dict[col] = 'Info'


    # pd function to add the replicate group to the columns
    grouped = pd.concat(dict((*noc_df.groupby(group_dict, 1),)), axis=1)

    grouped.columns = grouped.columns.rename("replicates", level=0)
    grouped.columns = grouped.columns.rename("fraction", level=1)

    # remove rep info from fractions
    grouped.rename(columns=rename, level='fraction', inplace=True)

    return grouped


def fraction_proportion(noc_grouped):
    """
    Convert replicate intensities to proportions
    """
    noc_grouped = noc_grouped.copy()

    # Get all the Reps
    reps = noc_grouped.columns.get_level_values('replicates').to_list()
    reps = [x for x in reps if x != 'Info']
    reps = list(set(reps))
    reps.sort()

    for rep in reps:
        noc_rep = noc_grouped[rep]
        rep_proportion = noc_rep.divide(noc_rep.sum(axis=1), axis='rows').fillna(0)
        noc_grouped[rep] = rep_proportion

    return noc_grouped


def integrate_proportions(noc_prop):
    noc_prop = noc_prop.copy()
    # Get all the Reps
    reps = noc_prop.columns.get_level_values('replicates').to_list()
    reps = [x for x in reps if x != 'Info']
    reps = list(set(reps))
    reps.sort()

    base = pd.DataFrame()
    # integrate cyto, nuc, organelle proportions into a list for each rep
    for rep in reps:
        base[rep] = noc_prop[rep].values.tolist()


    base_idxs = base.index.to_list()
    multi_args = zip(repeat(base), base_idxs)

    p = Pool()
    results = p.starmap(pool_proportion_median, multi_args)
    p.close()
    p.join()

    # unwrapping listed results
    unwrap_results = list(zip(*results))
    median_nocs, qualities = unwrap_results[0], unwrap_results[1]

    final_noc = noc_prop['Info']
    final_noc['NOC_quality'] = qualities
    med_nocs = list(zip(*median_nocs))
    cyto, nuc, org = med_nocs[0], med_nocs[1], med_nocs[2]
    final_noc['nuclear'] = nuc
    final_noc['organellar'] = org
    final_noc['cyto'] = cyto

    return final_noc


def pool_proportion_median(base, idx):
    """
    sub-function of integrate_proportions used for multiprocessing
    """
    row = pd.DataFrame(base.loc[idx])
    rep_lists = row[idx].to_list()

    # correlation matrix
    corrs = np.corrcoef(rep_lists)

    # list of each rep's count on how many correlations > 0.9
    relevance = np.array([sum(x > 0.9 for x in y)-1 for y in corrs])

    # Find replicates where corr < 0.9 for at least three other replicates
    drop_idxs = np.where(relevance < 3)[0]
    quality = 6 - len(drop_idxs)

    if quality == 0:
        return [[0, 0, 0], 0]

    # drop poorly correlating replicates
    elif quality < 6:
        drop_idxs = sorted(drop_idxs, reverse=True)
        for idx in drop_idxs:
            del rep_lists[idx]

    # zip and find median for each proportion
    zipped_noc = list(zip(*rep_lists))
    median_noc = [np.median(x) for x in zipped_noc]

    return [median_noc, quality]


def classify_nocs(final_noc):
    final_noc = final_noc.copy()
    noc_df = final_noc[['Protein IDs', 'nuclear', 'organellar', 'cyto']]
    noc_df['noc'] = noc_df[['nuclear', 'organellar', 'cyto']].values.tolist()
    noc_df['localization'] = noc_df['noc'].apply(noc_classifer)
    noc_df = noc_df[['Protein IDs', 'localization']]
    classified_noc = final_noc.merge(noc_df, how='left', on='Protein IDs')
    return classified_noc


def noc_classifer(noc):
    if noc[0] >= 0.85:
        return 'N'
    elif noc[2] >= 0.85:
        return 'C'
    elif (noc[1] > 0.3) & (noc[2] < 0.15):
        return 'O'
    elif (noc[0] < 0.4) & (noc[1] > 0.15) & (noc[2] > 0.15):
        return 'O/C'
    elif (noc[0] > 0.15) & (noc[1] < 0.1) & (noc[2] >= 0.15):
        return 'N/C'
    elif sum(noc) == 0:
        return 'I'
    else:
        return 'B'
