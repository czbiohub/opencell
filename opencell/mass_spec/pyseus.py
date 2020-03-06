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




def process_raw_file(file_name, filter_rows=True, fix_col_names=True,
        remove_dup_baits=True, find_gene_names=True, verbose=True):
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

    selected_cols = ['Protein IDs', 'Protein names', 'Gene names',
                    'Fasta headers']
    # select all intensity columns
    lfq_intensity_cols = select_intensity_cols(col_names, 'LFQ intensity')
    intensity_cols = select_intensity_cols(col_names, 'intensity')
    intensity_cols = intensity_cols + lfq_intensity_cols

    selected_cols = selected_cols + intensity_cols

    # filter unwanted columns from the df
    ms_df = ms_df[selected_cols]


    # fix col_names
    if fix_col_names:
        fixed_intensity_cols = fix_cols(intensity_cols)
        rename = {i: j for i, j in zip(intensity_cols, fixed_intensity_cols)}
        ms_df.rename(columns=rename, inplace=True)

    # if there are duplicate columns, get max values between the columns
    if remove_dup_baits:
        new_cols = list(ms_df)
        # generate a list of duplicate columns
        dups = [item for item, count in collections.Counter(new_cols).items()
            if count > 1]

        # iterate through the duplicate columns and replace duplicates with max vals
        for dup in dups:
            replacement = ms_df[dup].max(axis=1)
            ms_df.drop(columns=[dup], inplace=True)
            ms_df[dup] = replacement

    # Fill in missing gene names
    if find_gene_names:
        ms_df = find_missing_names(ms_df, verbose=verbose)

    return ms_df


def transform_intensities(orig_df, intensity_type='LFQ intensity', func=np.log2):
    """transform intensity values in the dataframe to a given function

    rtype ms_df: pd dataframe"""

    transformed = orig_df.copy()

    # obtain a list of intensity column names
    intensity_cols = select_intensity_cols(list(orig_df), intensity_type)
    selected_cols = ['Protein IDs', 'Protein names', 'Gene names',
                    'Fasta headers']
    selected_cols = selected_cols + intensity_cols
    transformed = transformed[selected_cols]

    # for each intensity column, transform the values
    for int_col in intensity_cols:
        # if transformation is log2, convert 0s to nans
        # (faster in one apply step than 2)
        if func == np.log2:
            transformed[int_col] = transformed[int_col].apply(lambda x: np.nan
                if x == 0 else func(x))
        else:
            transformed[int_col] = transformed[int_col].apply(func)
            # Replace neg inf values is np.nan
            transformed[int_col] = transformed[int_col].apply(
                lambda x: np.nan if np.isneginf(x) else x)
    return transformed


def group_replicates(transformed_df, intensity_re=r'LFQ (\d){8}_',
                     reg_exp=r'_0\d($|_)'):
    """Group the replicates of intensities into replicate groups
    rtype df: pd dataframe"""

    # get col names
    col_names = list(transformed_df)

    # using a dictionary, group col names into replicate groups
    group_dict = {}
    for col in col_names:
        # search REs of the replicate ID, and get the group names

        # search if the col is for intensity values
        intensity_search = re.search(intensity_re, col.lower(),
            flags=re.IGNORECASE)

        # if so, get the group name and add to the group dict
        if intensity_search:
            name_start = intensity_search.end()
            name_end = re.search(reg_exp, col).start()
            group_name = col[name_start:name_end]
            group_dict[col] = group_name
        # if not, group into 'Info'
        else:
            group_dict[col] = 'Info'


    # pd function to add the replicate group to the columns
    grouped = pd.concat(dict((*transformed_df.groupby(group_dict, 1),)), axis=1)

    grouped.columns = grouped.columns.rename("Baits", level=0)
    grouped.columns = grouped.columns.rename("Replicates", level=1)


    return grouped


def filter_valids(grouped_df, verbose=True):
    """Remove rows that do not have at least one group that has values
    in all triplicates"""

    # reset index
    grouped_df = grouped_df.reset_index(drop=True).copy()
    unfiltered = grouped_df.shape[0]

    # Get a list of all groups in the df
    group_list = list(set([col[0] for col in list(grouped_df) if col[0] != 'Info']))




    # booleans for if there is a valid value
    filtered = grouped_df[group_list].apply(np.isnan)
    # loop through each group, and filter rows that have valid values
    for group in group_list:
        # filter all rows that qualify as all triplicates having values
        filtered = filtered[filtered[group].any(axis=1)]

    # a list containing all the rows to delete
    del_list = list(filtered.index)

    # create a new df, dropping rows with invalid data
    filtered_df = grouped_df.drop(del_list)
    filtered_df.reset_index(drop=True, inplace=True)
    filtered = filtered_df.shape[0]

    if verbose:
        print("Removed invalid values. " + str(filtered) + " from "
              + str(unfiltered) + " rows remaining.")

    return filtered_df


def impute_nans(filtered_df, distance=1.8, width=0.3):
    """To test for enrichment, preys with that were undetected in some baits
    need to be assigned some baseline values. This function imputes
    a value from a normal distribution of the left-tail of a bait's
    capture distribution for the undetected preys.

    rtype imputed: pd dataframe"""

    imputed = filtered_df.copy()

    # Retrieve all col names that are not classified as Info
    bait_names = [col[0] for col in list(filtered_df) if col[0] != 'Info']
    bait_names = list(set(bait_names))

    # Loop through each bait, find each bait's mean and std,
    # impute Nan values given the distribution inputs
    for bait in bait_names:
        all_vals = filtered_df[bait].stack()
        mean = all_vals.mean()
        stdev = all_vals.std()

        # get imputation distribution mean and stdev
        imp_mean = mean - distance * stdev
        imp_stdev = stdev * width

        # copy a df of the group to impute values
        bait_df = filtered_df[bait].copy()

        # loop through each column in the group
        for col in list(bait_df):
            bait_df[col] = bait_df[col].apply(random_imputation_val,
                                   args=[imp_mean, imp_stdev])
        imputed[bait] = bait_df

    return imputed


def median_replicates(imputed_df, mean=False, save_info=True, col_str='median '):
    """For each bait group, calculate the median of the replicates
    and returns a df of median values

    rtype: median_df pd dataframe"""

    # retrieve bait names
    bait_names = [col[0] for col in list(imputed_df) if col[0] != 'Info']
    bait_names = list(set(bait_names))
    # initiate a new df for medians
    median_df = pd.DataFrame()

    # for each bait calculate medain across replicates and add
    # to the new df
    for bait in bait_names:
        if mean:
            bait_median = imputed_df[bait].mean(axis=1)
        else:
            bait_median = imputed_df[bait].median(axis=1)
        new_col_name = col_str + bait
        median_df[new_col_name] = bait_median

    if save_info:
        # get info columns into the new df
        info = imputed_df['Info']
        info_cols = list(info)

        for col in info_cols:
            median_df[col] = info[col]

    return median_df


def enrichment_pvals_dfs(imputed_df, cluster_df):
    """using the clusters obtained from PCA-KMeans,
    construct the negative control set and calculate
    enrichment and p values of two-sided Welch's test

    rtype enrichment_df: pd DataFrame
    rtype pval_df: pd DataFrame"""


    # join the df with cluster_df
    num_clusters = cluster_df['cluster'].nunique()
    clustered = imputed_df.T.join(cluster_df, how='outer')

    # a list to concatenate all analyzed dfs later
    pval_master = []
    enrch_master = []

    # iterate through each cluster to generate neg con group
    clust_list = list(np.arange(num_clusters))
    multi_args = zip(clust_list, repeat(clustered))
    p = Pool()
    enrch_master, pval_master = zip(*p.starmap(multi_pval, multi_args))
    p.close()
    p.join()

    enrichment_df = pd.concat(enrch_master).T
    pval_master_df = pd.concat(pval_master).T

    # add informational columns again

    category_cols = [col for col in list(imputed_df) if col[0] == 'Info']

    for cat in category_cols:
        enrichment_df[cat] = imputed_df[cat]
        pval_master_df[cat[1]] = imputed_df[cat]

    return enrichment_df, pval_master_df


def multi_pval(cluster, clustered):
    """function generating negative control andcalculating pvals for
    each cluster. Fed into multiprocess Pool.  """
    print("cluster " + str(cluster))

    # create the neg control df
    neg_control = clustered[clustered['cluster'] != cluster].copy()
    neg_control.drop('cluster', axis=1, inplace=True)
    neg_control.drop('Info', level='Baits', inplace=True)

    # calculate the neg con median and stds
    con_median = neg_control.median()
    con_std = neg_control.std()


    # This is the enrichment calcuation

    # choose the cluster to calculate enrichment
    enrch_clust = clustered[clustered['cluster'] == cluster].copy().T
    enrch_clust.drop('cluster', inplace=True)
    col_names = list(enrch_clust)
    # iterate through each bait and calculate enrichment
    for col in col_names:
        enrch_clust[col] = (enrch_clust[col] - con_median)\
            / con_std
    # choose the cluster
    pval_clust = clustered[clustered['cluster'] == cluster].copy()

    # Get a list of baits
    baits = list(pval_clust.index.get_level_values('Baits'))
    baits = list(set(baits))
    pval_clust = pval_clust.T
    pval_clust.drop('cluster', inplace=True)


    # create a new df to populate
    pval_df = pd.DataFrame()

    # iterate through each bait and calculate pvals using Welch's
    # t test
    for bait in baits:
        # combine values of replicates into one list
        bait_series = pval_clust[bait].values.tolist()
        if len(bait_series[0]) < 2:
            print(bait)
            print('Not enough replicates')
            continue


        # add an index value to the list for locating neg_control indices
        for i in np.arange(len(bait_series)):
            bait_series[i].append(i)

        # perform the p value calculations
        pval_df[bait] = bait_series
        pval_df[bait] = pval_df[bait].apply(get_pvals, args=[neg_control])

    print('cluster ' + str(cluster) + ' calculations finished')
    # add cluster pvals to master df
    return [enrch_clust.T, pval_df.T]


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


# MPI's negative control generation
def mpi_corr(grouped_df, verbose=True):
    """Filter only preys that are present across all samples.
    Calculate the correlation df from the filtered set and return it

    rtype: corr_df pd DataFrame"""

    filtered = grouped_df.reset_index(drop=True).copy()
    unfiltered_num = grouped_df.shape[0]

    # Get a list of all groups in the df
    group_list = list(set([col[0] for col in list(grouped_df) if col[0] != 'Info']))

    # booleans for if there is a valid value
    finites = filtered[group_list].apply(np.isfinite)

    # loop through each group, and filter rows that have valid values
    for group in group_list:

        # filter all rows that qualify as all triplicates having values
        finites = finites[finites[group].any(axis=1)]


    # a list containing all the rows to delete
    keep_list = list(finites.index)

    # create a new df, dropping rows with invalid data
    filtered = filtered[filtered.index.isin(keep_list)]

    filtered_num = filtered.shape[0]

    if verbose:
        print("Removed invalid values. " + str(filtered_num) + " from "
              + str(unfiltered_num) + " rows remaining.")

    # replace replicates with median values and calculate correlations
    median_df = median_replicates(filtered, save_info=False, col_str="")
    corr_df = median_df.corr()

    return corr_df


def negcon_filter(corr_df, threshold=95):
    """based on the correlation df, return a pd.Series of all baits
    that should be excluded in the enrichment/pval calculations

    rtype: neg_filter pd Series"""

    # convert all correlation values to a flattened list
    corrlist = corr_df.to_numpy().flatten()

    # remove diagonal 1.0 correlation values
    corrlist = list(filter(lambda x: x != 1, corrlist))

    # calculate correlation value that corresponds
    # to the given percentile threshold
    corr_thresh = np.percentile(corrlist, threshold)

    # initiate a dict to store baits to exclude in neg control
    # for each bait analysis
    neg_filter = {}


    # iterate through baits and obtain a list of similar baits
    # to exclude

    bait_list = list(corr_df)
    for bait in bait_list:
        exc_list = list(corr_df[bait][corr_df[bait] > corr_thresh].index)
        neg_filter[bait] = exc_list


    return pd.Series(neg_filter)


def mpi_enrich_pvals(imputed_df, neg_filter):
    """excluding the baits listed in the neg_filter series,
    construct a negative control for each bait and calculate
    enrichment and pvals

    rtype enrichment_df, pval_df"""

    temporary = imputed_df.copy()
    temporary.drop('Info', level='Baits', inplace=True, axis=1)

    bait_list = list(set([col[0] for col in list(imputed_df) if col[0] != 'Info']))

    # initiate a pval df and enrich df
    pval_df = pd.DataFrame()
    enrich_df = pd.DataFrame()

    print(len(bait_list))
    for i, bait in enumerate(bait_list):
        if i % 50 == 0:
            print(i)

        # construct a negative control by dropping all similar baits
        neg_control = temporary.copy()
        drop_list = neg_filter[bait]
        neg_control.drop(columns=drop_list, inplace=True)

        # calculate the neg con median and stds
        con_median = neg_control.median(axis=1)
        con_std = neg_control.std(axis=1)

        # calculate enrichment
        enrich_df[bait] = (temporary[bait].median(axis=1) - con_median) / con_std

        # calculate the p-values

        # combine values of replicates into one list
        bait_series = temporary[bait].values.tolist()
        if len(bait_series[0]) < 2:
            print(bait)
            print('Less than 2 replicates')
            continue


        # add an index value to the list for locating neg_control indices
        for i in np.arange(len(bait_series)):
            bait_series[i].append(i)

        # perform the p value calculations
        pval_df[bait] = bait_series
        pval_df[bait] = pval_df[bait].apply(get_pvals, args=[neg_control.T])

    category_cols = [col for col in list(imputed_df) if col[0] == 'Info']

    for cat in category_cols:
        enrich_df[cat[1]] = imputed_df[cat]
        pval_df[cat[1]] = imputed_df[cat]

    return enrich_df, pval_df


# PCA Functions, perform after median_replicates
def standard_scale(median_df, drop=True, transpose=False,
        drop_col_list=None):
    """Before PCA, median values need to be scaled across each prey
    distribution"""

    if drop_col_list is None:
        drop_col_list = ['Protein names', 'Gene names', 'Protein IDs',
            'Fasta headers']

    # prep the DF
    pre_scale = median_df.copy()
    if drop:
        pre_scale.drop(drop_col_list, axis=1, inplace=True)

    # save column names
    col_names = list(pre_scale)
    row_names = list(pre_scale.index)

    # Transpose to normalize across preys
    if transpose:
        pre_scale = pre_scale.T

    # initiate standard scaler and scale
    sc = StandardScaler()
    transformed = sc.fit_transform(pre_scale)
    # Transformed data is a list of numpy arrays, so convert back to a df
    scaled = pd.DataFrame(transformed)
    if transpose:
        scaled = scaled.T
    scaled.index = row_names
    scaled = rename_cols(scaled, list(scaled), col_names)

    return scaled


def pca_transform(scaled_df, components=10):
    """Using the standard scaled df, perform PCA given the # of components
    and return the df of PCA

    rtype pca_model: trained pca model
    rtype pca_df = df with PCA transformations"""

    bait_names = list(scaled_df.index)

    # copy and transpose the df (baits as rows)
    scaled_df = scaled_df.copy()

    # initiate PCA with given number of components
    pca_model = PCA(n_components=components)
    pca_array = pca_model.fit_transform(scaled_df)

    # Generate a df
    pca_df = pd.DataFrame(pca_array)
    pca_df.index = bait_names

    return pca_model, pca_df


def cluster_dfs(pca_df, k=4, n_init=100):
    """Assign each bait to a a cluster generated by KMeans clustering
    from the PCA_df

    rtype cluster_df: pd Series/df"""

    # fit kmeans clustering to the PCA df
    kmeans = KMeans(n_clusters=k, n_init=n_init).fit(pca_df)
    clustered_baits = kmeans.predict(pca_df)

    # bait names
    bait_names = list(pca_df.index)
    bait_names = new_col_names(bait_names, ['median '], [''])

    clustered_df = pd.DataFrame(clustered_baits)
    clustered_df.rename(columns={0: 'cluster'}, inplace=True)
    clustered_df.index = bait_names
    clustered_df.index.rename('Baits', inplace=True)

    return clustered_df


# Auxillary functions
def all_valids(grouped_df):
    """Filter only preys that are present across all samples.

    rtype: corr_df pd DataFrame"""

    filtered = grouped_df.reset_index(drop=True).copy()

    # Get a list of all groups in the df
    group_list = list(set([col[0] for col in list(grouped_df) if col[0] != 'Info']))

    # booleans for if there is a valid value
    finites = filtered[group_list].apply(np.isfinite)

    # loop through each group, and filter rows that have valid values
    for group in group_list:

        # filter all rows that qualify as all triplicates having values
        finites = finites[finites[group].any(axis=1)]


    # a list containing all the rows to delete
    keep_list = list(finites.index)

    # create a new df, dropping rows with invalid data
    filtered = filtered[filtered.index.isin(keep_list)]

    return filtered


def reg_and_imputed_dfs(imputed_df, drop_col_list=None):

    """After imputation step, it is good to look at imputed data stats
    this function returns two dfs - a comprehensive df including imputed vals,
    and a df composed only of imputed vals. The dfs are transposed for easier
    analysis of prey distributions

    rtype: alls pd dataframe
    rtype imputes_only pd dataframe"""

    if drop_col_list is None:
        drop_col_list = ['Protein names', 'Gene names', 'Protein IDs', 'Fasta headers']

    alls = imputed_df.copy()
    # Drop the added layer of col headings for technical groups

    alls.columns = imputed_df.columns.droplevel()
    alls.drop(drop_col_list, axis=1, inplace=True)

    alls = alls.T

    # df3 will be the df of only imputed vals
    imputes_only = alls.copy()

    # get col names
    col_names = list(imputes_only)
    # iterate through each col and replace non-imputed vals with np.nans
    for col in col_names:
        imputes_only[col] = imputes_only[col].apply(lambda x: np.nan
            if x == round(x, 4) else x)

    return alls, imputes_only


def select_intensity_cols(orig_cols, intensity_type):
    """from df column names, return a list of only intensity cols
    rtype: intensity_cols list """
    # new list of intensity cols
    intensity_cols = []

    # create a regular expression that can distinguish between
    # intensity and LFQ intensity
    re_intensity = '^' + intensity_type.lower()

    # for loop to include all the intensity col names
    intensity_type = intensity_type.lower()
    for col in orig_cols:
        col_l = col.lower()

        # check if col name has intensity str
        if re.search(re_intensity, col_l):
            intensity_cols.append(col)

    return intensity_cols


def new_col_names(col_names, RE, replacement_RE):
    """A better version of fix_cols that has exact regular expression
    search and output that can be customized. Inputs are a list of REs
    and replacement REs

    rtype: new_cols, list"""

    # start a new col list
    new_cols = []

    # Loop through cols and make quaifying subs
    for col in col_names:
        for i in np.arange(len(RE)):
            col = re.sub(RE[i], replacement_RE[i], col, flags=re.IGNORECASE)
        new_cols.append(col)

    return new_cols


def rename_cols(df, old_cols, new_cols):
    """Just a two liner to rename columns using two lists
    rtype: renamed, pd Dataframe"""

    rename = {i: j for i, j in zip(old_cols, new_cols)}

    renamed = df.rename(columns=rename)

    return renamed


def fix_cols(col_names, reps=3):
    """Simple function: Sometimes the MS raw file has unnecessary string
    after the replicate id, this fn will replace the string without that bit.

    rtype: new_cols, list """

    # import file and column names
    # col_names = list(df)

    # create a RE pattern to match the replicate id
    rep_id = '(_0[1-' + str(reps) + ']_)'

    # for every column name, find where the RE pattern is
    # matching, and delete unnecessary string.
    # return a new list of col_names

    new_cols = []
    for col in col_names:
        # search for the RE
        rep_search = re.search(rep_id, col)
        # if there is a match, get an index start
        if rep_search:
            end = rep_search.end()
            # make a new column name that deletes
            # unncessary str
            col = col[:end-1]

        # append fixed (or intact) column name
        new_cols.append(col)

    # return the new column names
    return new_cols


def random_imputation_val(x, mean, std):
    """from a normal distribution take a random sample if input is
    np.nan. For real values, round to 4th decimal digit.
    Floats with longer digits will be 'barcoded' by further digits

    rtype: float"""

    if np.isnan(x):
        return np.random.normal(mean, std, 1)[0]
    else:
        return np.round(x, 4)


def find_missing_names(raw_df, verbose=True):
    """from a list of protein IDS that have missing gene names
    in the uniprot table, """


    # Identify entries with missing gene names
    raw_df = raw_df.copy()
    name_filter = raw_df[['Protein IDs', 'Gene names']]
    missing_names = name_filter[name_filter['Gene names'].isna()].copy()

    if verbose:
        num_missing = missing_names.shape[0]
        print("Gene names missing in " + str(num_missing) + ' rows.')
        print("Accessing Uniprot to correct records..")


    # format protein ids to standard uniprot entry
    missing_names['new IDs'] = missing_names['Protein IDs']\
        .apply(lambda x: x.replace(";", ' '))
    missing_list = missing_names['new IDs'].values.tolist()

    # initiate a dictionary to save fetched gene names
    id_names = {}

    url = "https://www.uniprot.org/uploadlists/"

    # Iterate through protein ids with missing gene names to fetch
    # Uniprot gene names
    for ids in missing_list:
        # remove isoform information from the protein ids
        n_ids = re.sub(r'-\d+', '', ids)

        params = {"from": "ACC+ID",
            'to': 'GENENAME',
            'format': 'tab',
            'query': n_ids}

        data = urllib.parse.urlencode(params)
        data = data.encode('utf-8')
        # create a new request
        req = urllib.request.Request(url, data)
        try:
            with urllib.request.urlopen(req) as f:
                response = f.read()

            # convert the request to a df for easier processing
            request_list = response.decode('utf-8')
            temp = pd.DataFrame([x.split('\t') for x in request_list.split('\n')])
            headers = temp.iloc[0]
            gene_names = pd.DataFrame(temp.values[1:], columns=headers)

            # from the converted df, extract the name
            names_list = gene_names["To"].values.tolist()
            names_list = list(set([x for x in names_list if x is not None]))
            name_str = ';'.join(names_list)
            # Append to the dict
            if name_str:
                id_names[ids] = name_str
            else:
                id_names[ids] = 'Unnamed'
        except Exception:
            print("UniProt Offline, all missing genes are 'Unnamed'")
            id_names[ids] = 'Unnamed'

    # Create a DF from the dict
    found_names = pd.Series(id_names)
    found_names.rename('Gene names', inplace=True)
    found_names.index.name = 'New IDs'

    # Join the df to the names df using New IDs column
    missing_names.reset_index(inplace=True, drop=False)
    missing_names.set_index('new IDs', inplace=True)
    missing_names.update(found_names)
    missing_names.set_index('index', inplace=True)

    # Join to the original df using Protein Ids column
    raw_df.update(missing_names)
    if verbose:
        print("Finished identifying missing gene names.")

    return raw_df


# Functions to identify missing Gene names and match column gene names
# with prey names


def multi_impute(filtered_df, distance=1.8, width=0.3):
    """To test for enrichment, preys with that were undetected in some baits
    need to be assigned some baseline values. This function imputes
    a value from a normal distribution of the left-tail of a bait's
    capture distribution for the undetected preys.

    This process is for multiprocessing

    rtype df: pd dataframe"""

    imputed = filtered_df.copy()

    # Retrieve all col names that are not classified as Info
    bait_names = [col[0] for col in list(imputed) if col[0] != 'Info']
    baits = list(set(bait_names))
    bait_series = [imputed[bait].copy() for bait in baits]

    # Use multiprocessing pool to parallel impute
    p = Pool()
    impute_list = p.map(pool_impute, bait_series)
    p.close()
    p.join()

    for i, bait in enumerate(baits):
        imputed[bait] = impute_list[i]

    return imputed


def pool_impute(bait_group, distance=1.8, width=0.3):
    """target for multiprocessing pool from multi_impute_nans"""
    all_vals = bait_group.stack()
    mean = all_vals.mean()
    stdev = all_vals.std()

    # get imputation distribution mean and stdev
    imp_mean = mean - distance * stdev
    imp_stdev = stdev * width

    # copy a df of the group to impute values
    bait_df = bait_group.copy()

    # loop through each column in the group
    for col in list(bait_df):
        bait_df[col] = bait_df[col].apply(random_imputation_val,
            args=(imp_mean, imp_stdev))
    return bait_df


def median_pca_filter(imputed_df, mad_factor=1, prey=True):
    """As an option to visualize clustering so that each intensity
    is subtracted by the prey group median, this function
    alters the base dataframe with the transformation"""

    transformed = imputed_df.copy()


    # Remove info columns for now, will add back again after transformation
    transformed.drop(columns=['Info'], level='Baits', inplace=True)
    transformed = median_replicates(transformed, save_info=False, col_str='')
    if prey:
        transformed = transformed.T

    # Get a list of the columns (baits or preys)
    cols = list(transformed)

    # go through each prey (now in columns) and subtract median
    for col in cols:
        transformed[col] = transformed[col] - transformed[col].median()
        mad = transformed[col].mad() * mad_factor
        transformed[col] = transformed[col].apply(lambda x: x if x > mad else 0)

    return transformed.T


def gridsearch_distance_params(imputed_df, mad_range, pca_range):
    """Search for mod_threshold, pca_components, and # clusters to find the optimum
    set of parameters for proper clustering, given a specific function"""
    imputed_df = imputed_df.copy()
    master_list = []
    count = 0
    total = len(mad_range) * len(pca_range)

    for mad in mad_range:
        t_pca = median_pca_filter(imputed_df, mad_factor=mad)
        for component in pca_range:
            _, pca_df = pca_transform(t_pca.T, components=component)
            if count % 10 == 0:
                countstr = 'Processed ' + str(count) + ' / ' + str(total) + \
                    ' parameter sets.'
                sys.stdout.write("\r{}".format(countstr))

            bait_names = pca_df.index.values.tolist()

            # This is customizable
            # distance_df = pd.DataFrame(squareform(pdist(pca_df)),
            #     columns=bait_names, index=bait_names)
            distance_df = pd.DataFrame(cosine_similarity(pca_df),
                columns=bait_names, index=bait_names)
            # nparray of all distances in distance_df
            atl_d = distance_df['20190830_ATL3'].loc['20190911_ATL3']
            # atl_vals = distance_df['20190830_ATL3'].to_numpy().flatten()
            # atl_p = percentileofscore(atl_vals, atl_d)

            clta_d = distance_df['20190830_CLTA'].loc['20190911_CLTB']
            # clta_vals = distance_df['20190830_CLTA'].to_numpy().flatten()
            # clta_p = percentileofscore(clta_vals,clta_d)

            master_list.append([mad, component, atl_d, clta_d])

            count += 1
    return master_list


def atl3_clta_metric(pca_df, n_clusters, repeats):
    """Check for proper clustering of ATL3 and CLTA/B"""
    atl_score = 0
    clta_score = 0
    for _ in np.arange(repeats):
        cluster_df = cluster_dfs(pca_df, k=n_clusters, n_init=10)
        if cluster_df.loc['20190830_ATL3'][0] == cluster_df.loc['20190911_ATL3'][0]:
            atl_score += 1
        if cluster_df.loc['20190830_CLTA'][0] == cluster_df.loc['20190911_CLTB'][0]:
            clta_score += 1

    atl_score = (100 * atl_score) / repeats
    clta_score = (100 * clta_score) / repeats

    return atl_score, clta_score


def iter_pvals(imputed_df, fc_var1, fc_var2, max_iter=5):
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
        repeat(fc_var1), repeat(fc_var2), repeat(max_iter))

    p = Pool()
    print("Parallel processing pval / enrichment calculations..")
    pval_dfs = p.starmap(iter_enrich_pval, multi_args)
    p.close()
    p.join()
    print("Done!")
    master_table = pd.concat(pval_dfs, axis=1)


    return master_table


def iter_enrich_pval(bait, df, num, total, fc_var1, fc_var2, max_iter=5):

    # initiate a counter and a list of drop vars
    count = 0
    drop_genes = []
    drop_list = [bait]
    new_drops = [bait]
    con_diff = 1

    # initiate other variables required for the fx
    bait_list = [col[0] for col in list(df) if col[0] != 'Info']
    gene_list = df[('Info', 'Gene names')].tolist()


    # construct a negative control by dropping all similar baits

    temporary = df.copy()
    neg_control = df.copy()
    temporary.drop('Info', level='Baits', inplace=True, axis=1)
    neg_control.drop('Info', level='Baits', inplace=True, axis=1)

    while ((con_diff > 0) & (count < max_iter)):

        neg_control.drop(columns=new_drops, inplace=True)

        # calculate the neg con median and stds
        con_median = neg_control.median(axis=1)
        con_std = neg_control.std(axis=1)

        # calculate enrichment
        enrich_series = (temporary[bait].median(axis=1) - con_median) / con_std
        enrich_series.index = gene_list
        enrich_series.name = 'enrichment'

        # calculate the p-values

        # combine values of replicates into one list
        bait_series = temporary[bait].values.tolist()
        # if len(bait_series[0]) < 2:
        #     print(bait)
        #     print('Less than 2 replicates')
        #     continue


        # add an index value to the list for locating neg_control indices
        for i in np.arange(len(bait_series)):
            bait_series[i].append(i)

        # perform the p value calculations
        pval_series = pd.Series(bait_series, index=gene_list, name='pvals')
        pval_series = pval_series.apply(get_pvals, args=[neg_control.T])

        # Find positive hits from enrichment and pval calculations
        pe_df = pd.concat([enrich_series, pval_series], axis=1)
        pe_df['thresh'] = pe_df['enrichment'].apply(calc_thresh,
            args=[fc_var1, fc_var2])
        pe_df['hits'] = np.where((pe_df['pvals'] > pe_df['thresh']), True, False)

        # Get genes names of all the hits
        hits = set(pe_df[pe_df['hits']].index.tolist())

        # compare hits to previous iteration
        drop_set = set(drop_genes)
        drop_diff = hits - drop_set


        # update drop genes
        drop_genes = list(drop_set.union(hits))
        # get a list of bait names to add to drop list
        new_drops = []

        # If there are too many hits, add only top 35 baits
        # to the drop list, and only iterate once more.
        if len(drop_diff) > 35:
            filter_cons = pe_df.loc[drop_diff]
            filter_cons.sort_values(by='pvals', ascending=False, inplace=True)
            drop_diff = filter_cons[:35].index.tolist()
            count = max_iter - 2
        if drop_diff:
            for gene in drop_diff:
                if ';' in gene:
                    mult_genes = gene.split(';')
                    for ind in mult_genes:
                        drops = [x for x in bait_list if ind in x]
                        new_drops = new_drops + drops
                else:
                    try:
                        drops = [x for x in bait_list if gene in x]
                    except Exception:
                        print(gene)
                    new_drops = new_drops + drops

        new_drops = list(set(new_drops)-set(drop_list))

        # number of newly discovered baits to drop
        con_diff = len(new_drops)

        # print('Iter ' + str(count))
        # print(new_drops)
        # print()
        # print(drop_diff)
        # print()

        drop_list = list(set(drop_list + new_drops))

        # Update counter
        count += 1
    output = pd.concat([pe_df[['enrichment', 'pvals', 'hits']]], keys=[bait],
        names=['baits', 'values'], axis=1)
    if num % 10 == 0:
        print(str(num) + ' / ' + str(total) + ' baits processed')
    # print(str(num) + ' / ' + str(total) + ' baits processed')
    return output


def pval_remove_significants(imputed_df, fc_vars1, fc_vars2):
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

    fc_var1, fc_var2 = fc_vars1[0], fc_vars1[1]

    multi_args = zip(bait_list, repeat(imputed_df), baitrange, repeat(total),
        repeat(fc_var1), repeat(fc_var2))

    p = Pool()
    print("First round p-val calculations..")
    neg_dfs = p.starmap(first_round_pval, multi_args)
    p.close()
    p.join()
    master_neg = pd.concat(neg_dfs, axis=1)
    print("First round finished!")

    master_neg.reset_index(inplace=True, drop=True)

    fc_var1, fc_var2 = fc_vars2[0], fc_vars2[1]

    multi_args2 = zip(bait_list, repeat(imputed_df), repeat(master_neg),
        baitrange, repeat(total), repeat(fc_var1), repeat(fc_var2))

    p = Pool()
    outputs = p.starmap(second_round_pval, multi_args2)

    master_df = pd.concat(outputs, axis=1)

    return master_df


def first_round_pval(bait, df, num, total, fc_var1, fc_var2):
    """ A first round of pval calculations to remove any significant hits
    from negative controls """

    # initiate other variables required for the fx
    gene_list = df[('Info', 'Gene names')].tolist()

    # construct a negative control by dropping all similar baits
    temporary = df.copy()
    neg_control = df.copy()
    temporary.drop('Info', level='Baits', inplace=True, axis=1)
    neg_control.drop('Info', level='Baits', inplace=True, axis=1)


    # calculate the neg con median and stds
    con_median = neg_control.median(axis=1)
    con_std = neg_control.std(axis=1)

    # calculate enrichment
    enrich_series = (temporary[bait].median(axis=1) - con_median) / con_std
    enrich_series.index = gene_list
    enrich_series.name = 'enrichment'

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

    # perform the p value calculations
    pval_series = pd.Series(bait_series, index=gene_list, name='pvals')
    pval_series = pval_series.apply(get_pvals, args=[neg_control.T])

    # Find positive hits from enrichment and pval calculations
    pe_df = pd.concat([enrich_series, pval_series], axis=1)
    pe_df['thresh'] = pe_df['enrichment'].apply(calc_thresh,
        args=[fc_var1, fc_var2])
    pe_df['hits'] = np.where((pe_df['pvals'] > pe_df['thresh']), True, False)

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


def second_round_pval(bait, df, neg_control, num, total, fc_var1, fc_var2):
    """ A first round of pval calculations to remove any significant hits
    from negative controls """

    # initiate other variables required for the fx
    gene_list = df[('Info', 'Gene names')].tolist()

    # construct a negative control by dropping all similar baits
    temporary = df.copy()
    neg_control = neg_control.copy()
    temporary.drop('Info', level='Baits', inplace=True, axis=1)

    # calculate the neg con median and stds
    con_median = neg_control.median(axis=1)
    con_std = neg_control.std(axis=1)

    # calculate enrichment
    enrich_series = (temporary[bait].median(axis=1) - con_median) / con_std
    enrich_series.index = gene_list
    enrich_series.name = 'enrichment'

    # calculate the p-values

    # combine values of replicates into one list
    bait_series = temporary[bait].values.tolist()

    # add an index value to the list for locating neg_control indices
    for i in np.arange(len(bait_series)):
        bait_series[i].append(i)

    # perform the p value calculations
    pval_series = pd.Series(bait_series, index=gene_list, name='pvals')
    pval_series = pval_series.apply(get_pvals, args=[neg_control.T])

    # Find positive hits from enrichment and pval calculations
    pe_df = pd.concat([enrich_series, pval_series], axis=1)
    pe_df['thresh'] = pe_df['enrichment'].apply(calc_thresh,
        args=[fc_var1, fc_var2])
    pe_df['hits'] = np.where((pe_df['pvals'] > pe_df['thresh']), True, False)

    output = pd.concat([pe_df[['enrichment', 'pvals', 'hits']]], keys=[bait],
        names=['baits', 'values'], axis=1)
    if num % 20 == 0:
        print(str(num) + ' / ' + str(total) + ' baits processed')
    # print(str(num) + ' / ' + str(total) + ' baits processed')

    return output




def calc_thresh(enrich, fc_var1, fc_var2):
    """simple function to get FCD thresh to recognize hits"""
    if enrich < fc_var2:
        return np.inf
    else:
        return fc_var1 / (abs(enrich) - fc_var2)
