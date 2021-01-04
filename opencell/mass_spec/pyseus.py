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


def process_raw_file(file_name, filter_rows=True, fix_col_names=True,
        remove_dup_baits=True, find_gene_names=True, verbose=True):
    """
    wrapper script that filters only important metadata and intensity columns,
    and filters rows with MaxQuant QC flags.

        file_name: str, directory of the protein groups file
        filter_rows: bool, filter rows based on ‘Potential Contaminant’,
            ‘Only Identified by site’, and ‘Reverse’ flags
        fix_col_names: bool, should be deprecated, as it is replaced
            by new_col_names function
        remove_dup_baits: bool, for any duplicate intensity columns,
            keep only column with max value
        find_gene_names: bool, access Uniprot online to retrieve
            gene names for any protein groups that are lacking gene names.

        RETURN: DataFrame – minimally processed DataFrame containing metadata and intensity columns
    """

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
    selected_cols = ['Protein IDs', 'Protein names', 'Majority protein IDs',
        'Gene names', 'Fasta headers']
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
        # use groups from re.search to customize group names
        if intensity_search:
            group_search = re.search(reg_exp, col, flags=re.IGNORECASE)
            group_name = ''

            for re_group in group_search.groups():
                group_name += re_group
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


def combine_transformed(data1, data2, join='outer'):
    """ This combines two ProteinGroups data tables that have gone through
    initial dataframe transformations up to transformations.
    Used primarily to combine two separate quant tables under the assumption
    that there are not significant batch effects.
    NOT to be used for final data analysis, but exploratory analysis
    """
    data1 = data1.copy()
    data2 = data2.copy()

    # Combine info columns of the two data tables
    info_cols = ['Protein IDs', 'Protein names', 'Gene names', 'Fasta headers']
    info1 = data1[info_cols]
    info2 = data2[info_cols]

    infos = pd.concat([info1, info2])
    infos.drop_duplicates(subset='Protein IDs', inplace=True)
    infos.set_index('Protein IDs', drop=True, inplace=True)



    # Change indexing to 'Protein IDs' on the dfs, and drop info cols
    data1.set_index('Protein IDs', drop=True, inplace=True)
    data1.drop(columns=['Protein names', 'Gene names', 'Fasta headers'], inplace=True)

    data2.set_index('Protein IDs', drop=True, inplace=True)
    data2.drop(columns=['Protein names', 'Gene names', 'Fasta headers'], inplace=True)

    # Join the two tables on Protein IDs, outer join
    joined = pd.concat([data1, data2], axis=1, join=join)

    # Join back the info cols
    final = pd.concat([joined, infos], axis=1, join='inner')
    final.reset_index(inplace=True)
    final.rename(columns={'index': 'Protein IDs'}, inplace=True)
    return final


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


def bool_imputes(imputed_df, drop_col_list=None):

    """After imputation step, it is good to look at imputed data stats
    this function returns two dfs - a comprehensive df including imputed vals,
    and a df composed only of imputed vals. The dfs are transposed for easier
    analysis of prey distributions

    rtype: alls pd dataframe
    rtype imputes_only pd dataframe"""

    if drop_col_list is None:
        drop_col_list = ['Protein names', 'Gene names', 'Protein IDs',
        'Majority protein IDs', 'Fasta headers']

    alls = imputed_df.copy()
    # Drop the added layer of col headings for technical groups

    alls.columns = imputed_df.columns.droplevel()
    protein_ids = imputed_df[('Info', 'Protein IDs')].copy()
    alls.drop(drop_col_list, axis=1, inplace=True)

    alls = alls.T

    # df3 will be the df of only imputed vals
    imputes_only = alls.copy()

    # get col names
    col_names = list(imputes_only)
    # iterate through each col and replace non-imputed vals with np.nans
    for col in col_names:
        imputes_only[col] = imputes_only[col].apply(lambda x: True
            if x == round(x, 4) else False)
    imputes_only = imputes_only.T
    imputes_only['Protein IDs'] = protein_ids
    return imputes_only


def imputed_bool_df(bool_imputes):
    """Convenience method to find which bait-prey pair has all
    imputed values in replicates
    Uses input from bool_imputes after an appropriate group_replicates
    processing"""

    # reset index
    bool_imputes = bool_imputes.copy()

    # Get a list of all groups in the df
    bait_list = list(set([col[0] for col in list(bool_imputes) if col[0] != 'Info']))

    # start a new df
    simple_imputes = pd.DataFrame()
    simple_imputes['Protein IDs'] = bool_imputes[('Info', 'Protein IDs')]

    # for each bait, find out which protein group has all imputed values
    # across replicates
    for bait in bait_list:
        simple_imputes[bait] = bool_imputes[bait].all(axis=1)
    simple_imputes.set_index('Protein IDs', drop=True, inplace=True)
    simple_imputes.columns = pd.MultiIndex.from_product([
        simple_imputes.columns, ['imputed']])
    simple_imputes.columns.set_names(['baits', 'values'], inplace=True)

    return simple_imputes


def convert_pg_to_primary(pg_id, change_dict):
    """
    convert pgs with same gene name to a pre-determined primary protein group
    """
    change_dict = change_dict.copy()

    # search for a protein id match in change_dict
    change_row = change_dict[change_dict['Protein IDs'] == pg_id]

    # return new id if pg_id in chnage_dict else return original id
    if change_row.shape[0] == 1:
        return change_row.primary_id.item()

    else:
        return pg_id


def consolidate_pgs(raw_df, change_dict):
    """
    to address multiple protein groups (rows) representing the same gene name / ENSG id
    in graph representation, this fx consolidates protein groups into one and sum up all
    their intensities using a prepared consolidation proteingroup table

        raw_df: DataFrame, output of the process_raw_file fx
        change_dict: DataFrame, precomputed dictionary of all pgs to consolidate
        RETURN: DataFrame, new df that has protein groups consolidated

    """
    raw_df = raw_df.copy()
    change_dict = change_dict.copy()

    # replace synonymous protein group id with one primary id
    raw_df['Protein IDs'] = raw_df['Protein IDs'].apply(
        convert_pg_to_primary, args=[change_dict])
    infos = raw_df[
        ['Protein IDs',
        'Majority protein IDs',
        'Protein names',
        'Gene names',
        'Fasta headers']]

    # consolidate same-name protein ids with summation, or taking first real value in information columns
    info_grouped = infos.groupby('Protein IDs').first()

    intensities_grouped = raw_df.groupby('Protein IDs').sum()
    intensities_grouped.replace(0, np.nan, inplace=True)

    new_df = pd.concat([info_grouped, intensities_grouped], axis=1)
    new_df.reset_index(inplace=True)

    return new_df




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


def new_col_names(col_names, RE, replacement_RE, repl_search=False):
    """
    change intensity column names to a readable format. More specifically,
    search a column name from an input RE and substitute matches with another
    input substitute strings or REs.
        col_names: list, a list of column names from raw_df
        RE: list, a list of regular expressions to search in column names
        replacement_RE: list, a list of strs/REs that substitute the original expression
        repl_search: boolean, if True, elements in replacement_RE are treated as regular
            expressions used in search, and all specified groups are used in substitution

        RETURN: list, a list of renamed columns
    """

    # start a new col list
    new_cols = []

    # Loop through cols and make quaifying subs
    for col in col_names:
        for i in np.arange(len(RE)):
            if re.search(RE[i], col, flags=re.IGNORECASE):
                replacement = replacement_RE[i]
                if (repl_search) & (len(replacement) > 1):
                    rep_search = re.search(replacement, col,
                                flags=re.IGNORECASE)
                    replacement = ''
                    for group in rep_search.groups():
                        replacement += group

                col = re.sub(RE[i], replacement, col, flags=re.IGNORECASE)
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
    """
    bait-imputation for sets of data without enough samples.
    This fx imputes a value from a normal distribution of the left-tail
    of a bait’s capture distribution for the undetected preys using
    multi-processing.
        filtered_df: DataFrame, precomputed from filter_valids
        distance: float, distance in standard deviation from the
            mean of the sample distribution upon which to impute. Default = 0
        width: float, width of the distribution to impute in standard deviations. Default = 0.3
        RETURN: DataFrame, df of imputed values ready for p-val/enrichment calculations
    """

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


def multi_impute_prey(filtered_df, distance=0, width=0.3, threshold=100):
    """
    default mode of imputation. For protein groups with less than threshold number
    of sample number, impute a value from a normal distribution of the prey’s capture
    distribution using multi-processing. Note- most protein groups do not need imputation
    with 12-plate MBR

        filtered_df: DataFrame, precomputed from filter_valids
        distance: float, distance in standard deviation from the mean of the
            sample distribution upon which to impute. Default = 0
        width: float, width of the distribution to impute in standard deviations.
            Default = 0.3
        threshold: int, max number of samples required for imputation

        RETURN: DataFrame, df of imputed values ready for p-val/enrichment calculations
    """

    imputed = filtered_df.copy()
    imputed.drop(columns='Info', inplace=True)
    imputed = imputed.T

    # Retrieve all col names that are not classified as Info
    baits = list(imputed)
    bait_series = [imputed[bait].copy() for bait in baits]

    # Use multiprocessing pool to parallel impute
    p = Pool()
    impute_list = p.map(pool_impute_prey, bait_series)
    p.close()
    p.join()

    for i, bait in enumerate(baits):
        imputed[bait] = impute_list[i]

    imputed = imputed.T

    info_cols = [x for x in list(filtered_df) if x[0] == 'Info']
    for col in info_cols:
        imputed[col] = filtered_df[col]

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


def pool_impute_prey(bait_group, distance=0, width=0.3):
    """target for multiprocessing pool from multi_impute_nans"""

    if bait_group.count() > 100:
        return bait_group


    mean = bait_group.mean()
    stdev = bait_group.std()

    # get imputation distribution mean and stdev
    imp_mean = mean - distance * stdev
    imp_stdev = stdev * width

    # copy a df of the group to impute values
    bait_df = bait_group.copy()


    bait_df = bait_df.apply(random_imputation_val,
            args=(imp_mean, imp_stdev))
    return bait_df


def median_normalization(imputed, axis=1):
    """
    normalize columns/rows with median subtraction
    """

    normalized = imputed.copy()
    normalized.drop(columns='Info', inplace=True)

    if axis == 0:
        normalized = normalized.T

    # take median of all the rows/cols
    medians = normalized.median(axis=0)

    cols = list(normalized)

    # take the median subtraction
    for col in cols:
        normalized[col] = normalized[col] - medians[col]

    if axis == 0:
        normalized = normalized.T

    info_cols = [x for x in list(imputed) if x[0] == 'Info']
    for col in info_cols:
        normalized[col] = imputed[col]

    return normalized
