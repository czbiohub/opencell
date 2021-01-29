import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import hack_pvals as hp
import validations as vali
import dynamic_fdr as dfdr
import os
from itertools import repeat
from multiprocessing import Pool
plt.style.use('ggplot')


def run_hits_post_processing(plates, data_root, date_root, root, date, chosen):
    """
    wrapper code to combine make_version­_directory, get_all_interactors, and drop_unchosen
    to organize all processed data in proper directory by version
    """
    print("Generating Directories..")
    make_version_directory(root, date)

    print("Creating master hits table..")
    all_hits = get_all_interactors(
        plates, data_root, date_root, metrics=[
            'protein_ids',
            'pvals',
            'interaction_stoi',
            'abundance_stoi',
            'enrichment'],
        name='_pval_and_stoich_', just_hits=True)

    root = root + '/' + date
    all_hits.to_pickle(root + '/raw_results/all_hits_' + date + '.pkl')

    print('Selecting chosen puilldowns..')
    dropped_hits = drop_unchosen(all_hits, chosen)
    dropped_hits.to_pickle(root + '/raw_results/all_hits_dropped_' + date + '.pkl')

    return dropped_hits


def run_all_post_processing(
        dropped_hits, root, date, corum, helas, threshold=None,
        reference_pr=None, reference_str=None):

    """
    wrapper code to combine dynamic_fdr.all_hits_get_fdrs, fdr_precision_recall,
    and make_pr_figure to compute interactome metrics and organize output in
    proper directories
    """

    root = root + '/' + date
    print("Getting DFDRs at 10, 12, 14..")


    _, dfdr10 = dfdr.all_hits_get_fdrs(dropped_hits, perc=10)
    _, dfdr12 = dfdr.all_hits_get_fdrs(dropped_hits, perc=12)
    _, dfdr14 = dfdr.all_hits_get_fdrs(dropped_hits, perc=14)

    dfdr10.to_pickle(root + '/dfdr_10/all_hits_dropped_dfdr10.pkl')
    dfdr12.to_pickle(root + '/dfdr_12/all_hits_dropped_dfdr12.pkl')
    dfdr14.to_pickle(root + '/dfdr_14/all_hits_dropped_dfdr14.pkl')

    print("Making interaction summaries...")

    # ints short for interactions
    dfdr10_ints = dfdr10[(dfdr10['hits']) | (dfdr10['minor_hits'])]
    dfdr12_ints = dfdr12[(dfdr12['hits']) | (dfdr12['minor_hits'])]
    dfdr14_ints = dfdr14[(dfdr14['hits']) | (dfdr14['minor_hits'])]

    dfdr10_ints.to_pickle(root + '/dfdr_10/all_interactions_dropped_dfdr10.pkl')
    dfdr12_ints.to_pickle(root + '/dfdr_12/all_interactions_dropped_dfdr12.pkl')
    dfdr14_ints.to_pickle(root + '/dfdr_14/all_interactions_dropped_dfdr14.pkl')

    # save as csvs too
    dfdr10_ints.to_csv(root + '/dfdr_10/all_interactions_dropped_dfdr10.csv', index=False)
    dfdr12_ints.to_csv(root + '/dfdr_12/all_interactions_dropped_dfdr12.csv', index=False)
    dfdr14_ints.to_csv(root + '/dfdr_14/all_interactions_dropped_dfdr14.csv', index=False)

    dfdr10_summary = interaction_count_summary(dfdr10_ints)
    dfdr12_summary = interaction_count_summary(dfdr12_ints)
    dfdr14_summary = interaction_count_summary(dfdr14_ints)

    dfdr10_summary.to_csv(root + '/summary/interactions_summary_dfdr10.csv', index=False)
    dfdr12_summary.to_csv(root + '/summary/interactions_summary_dfdr12.csv', index=False)
    dfdr14_summary.to_csv(root + '/summary/interactions_summary_dfdr14.csv', index=False)


    print("Calculating precision-recall...")

    pr_table = fdr_precision_recall(dropped_hits, corum, helas, threshold)
    pr_table.to_pickle(root + '/summary/pr_table_' + date + '.pkl')

    # calculate recall-precision for DFDRs
    print("Calculating precision-recall for DFDRs")
    dfdrs = [dfdr10_ints, dfdr12_ints, dfdr14_ints]

    dfdr_precisions = []
    dfdr_recalls = []
    dfdr_interactions = []

    for dfdr_hits in dfdrs:
        dfdr_pr = interactors_precision_recall(dfdr_hits, corum, helas)
        dfdr_precisions.append(dfdr_pr[0])
        dfdr_recalls.append(dfdr_pr[1])
        dfdr_interactions.append(dfdr_pr[2])

    dfdr_pr_table = pd.DataFrame()
    dfdr_pr_table['precision'] = dfdr_precisions
    dfdr_pr_table['recall'] = dfdr_recalls
    dfdr_pr_table['num_interactions'] = dfdr_interactions

    dfdr_pr_table.to_pickle(root + '/summary/dfdr_pr_table_' + date + '.pkl')

    fig = make_pr_figure(pr_table, dfdr_pr_table, date, reference_pr, reference_str)
    fig.savefig(root + '/summary/precision_recall_' + date + '.pdf')


def make_pr_figure(pr_table, dfdr_pr_table, date, reference_pr, reference_str):
    """
    """

    fig, ax = plt.subplots()
    _ = ax.plot(pr_table['recall'], pr_table['precision'], color='#E24A33',
        label=date, linewidth=3, alpha=0.7)
    _ = ax.scatter(dfdr_pr_table['recall'], dfdr_pr_table['precision'], color='#E24A33',
        s=60, label='DFDR 10/12/14')

    if reference_pr is not None:
        _ = ax.plot(reference_pr['recall'], reference_pr['precision'], color='#348ABD',
        label=reference_str, linewidth=3, alpha=0.7)
    plt.xlim(-0.02, 0.52)
    plt.ylim(0.75, 0.98)
    # plt.legend(fontsize=11)
    plt.xlabel("Recall (Corum Coverage)")
    plt.ylabel('Precision (Co-localization)')
    plt.tick_params(labelsize=11)
    _ = plt.legend(fontsize=13, loc='lower left')
    _ = plt.yticks(np.arange(0.7, 0.96, 0.05))

    return fig


def make_version_directory(root, date):
    """
    make a directory with uniform subfolders for each version of pulldown
    """

    date_root = root + '/' + date
    os.mkdir(date_root)
    summary = date_root + '/summary'
    graph_clustering = date_root + '/graph_clustering'
    raw_results = date_root + '/raw_results'
    dfdr_10 = date_root + '/dfdr_10'
    dfdr_12 = date_root + '/dfdr_12'
    dfdr_14 = date_root + '/dfdr_14'

    os.mkdir(summary)
    os.mkdir(graph_clustering)
    os.mkdir(raw_results)
    os.mkdir(dfdr_10)
    os.mkdir(dfdr_12)
    os.mkdir(dfdr_14)


def get_plate_interactors(pvals, metrics=['pvals'], just_hits=False):
    """
    Return a dataframe that has all hits or interactions in 3-column (target, prey, metric) format
    """

    protein_ids = pvals.index.to_list()
    pvals = pvals.copy()

    pvals.set_index(('gene_names', 'gene_names'), inplace=True)
    pvals.index.name = 'gene_names'
    targets = pvals.columns.get_level_values('baits')
    targets = list(set(targets))

    all_hits = []
    # Get all hits and minor hits along with the metric data
    for target in targets:
        target_pvs = pvals[target]
        target_pvs['protein_ids'] = protein_ids

        # return target_pvs
        # just_hits bool will return all hits, else it will only return interactors
        if just_hits:
            hits = target_pvs
            hits.reset_index(inplace=True)
        else:
            selection = ['hits', 'minor_hits'] + metrics
            hits = target_pvs[target_pvs['hits'] | target_pvs['minor_hits']][selection]
            hits.reset_index(inplace=True)


        hits['target'] = target.upper()
        hits.rename(columns={'gene_names': 'prey'}, inplace=True)
        hits.reset_index(drop=True, inplace=True)
        all_hits.append(hits)

    all_hits = pd.concat(all_hits, axis=0)
    return all_hits


def get_all_interactors(plates, root, date, metrics=['pvals'], name='_pval_and_stoich_',
        just_hits=False):
    """
     combines multiple outputs of calculated pval/stoich datasets into one DataFrame
     of all interactions/hits

        plates: list, a list of all mass_spec plate sample set to include for the overall dataset
        root: str, root directory of the output files
        date: str, processed date for the output files
        metric: list, list of column names to include in the final DataFrame
        name: str, standard name given to output files
        just_hits: boolean, specifies whether to include all hits or just significant interactors

    """
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

    # return hit/minor_hits information if just_hits is flagged False
    if just_hits:
        selection = ['target', 'prey'] + metrics
        all_hits = all_hits[selection]
    else:
        selection = ['target', 'prey', 'hits', 'minor_hits'] + metrics
        all_hits = all_hits[selection]
    # all_hits = all_hits.dropna()
    all_hits = all_hits.sort_values(by='target')

    # separate out the plate and target information from plate_target format
    all_hits['plate'] = all_hits['target'].apply(lambda x: x.split('_', 1)[0])
    all_hits['target'] = all_hits['target'].apply(lambda x: x.split('_', 1)[1])

    return all_hits


def drop_unchosen(all_hits, chosens):
    """

    in cases where there are multiple pulldowns of the same cell line,
    drop pulldowns that did not make manual selection

    all_hits: DataFrame, output from get_all_interactors
    chosens: DataFrame, manually curated selection of chosen pulldowns

    RETURN: DataFrame
    """
    all_hits = all_hits.copy()
    chosens = chosens.copy()

    droplist = []
    for i, row in chosens.iterrows():
        target = row.target
        pick = row.pick
        select = all_hits[(all_hits['target'] == target) & (all_hits['plate'] != pick)]
        droplist += select.index.to_list()

    all_hits.drop(droplist, inplace=True)
    all_hits.reset_index(drop=True, inplace=True)

    return all_hits
    # all_hits.to_pickle(root + '/summary/all_hits_dropped_' + date + '.pkl')
    # all_hits.to_csv(root + '/summary/all_hits_dropped_' + date + '.csv')


def interaction_count_summary(interactions):
    """
    create a standard summary table of hit counts
    """
    new_hits = interactions[['target', 'plate', 'prey', 'hits', 'minor_hits']]

    # get target match
    idxs = []
    for i, row in new_hits.iterrows():
        target = str(row.target)
        prey = str(row.prey).split(';')
        if target in prey:
            idxs.append(i)

    better_match = new_hits[new_hits.index.isin(idxs)]
    better_match = better_match[['target', 'prey']]
    better_match['target_match'] = 1
    better_match = better_match[['target', 'target_match']]

    summary = pd.DataFrame(new_hits.groupby('target').count()['prey'])
    summary.reset_index(inplace=True)


    summary2 = summary.merge(better_match, on='target', how='left')
    summary2['target_match'] = summary2['target_match'].apply(lambda x: 1 if x == 1 else 0)
    summary2.rename(columns={'prey': 'hit_count'}, inplace=True)
    summary2['subtracted_hits'] = summary2['hit_count']-summary2['target_match']

    targets = summary2['target'].to_list()

    prey_counts = []
    for target in targets:
        prey_count = new_hits[new_hits['prey'].apply(
            lambda x: str(target) in str(x).split(';'))].shape[0]
        prey_counts.append(prey_count)

    summary2['preys'] = prey_counts
    summary2['subtracted_preys'] = summary2['preys'] - summary2['target_match']

    summary2 = summary2[[
        'target', 'hit_count', 'preys', 'target_match', 'subtracted_hits', 'subtracted_preys']]

    summary2.drop_duplicates(inplace=True)

    return summary2


def fdr_precision_recall(all_hits, corum, helas, thresholds, pvals=False):
    """
    calculates colocalization precision and corum coverage recall to create precision-recall
    curve data by sliding across interaction calling thresholds

        all_hits – DataFrame, output of get_all_interactors or drop_unchosen, just_hits=False
        corum – DataFrame, CORUM complex dataframe
        helas – DataFrame, protein group localization data from fractions MS, despite the naming,
        it can either be HELA or HEK dataset
        thresholds – list, a list of floats that serve as thresholds for interaction calling
        pvals – boolean, whether to use simple p-value thresholding or FDR curve thresholding

    """

    if pvals:
        all_hits = all_hits[['target', 'prey', 'pvals']]
    else:
        all_hits = all_hits[['target', 'prey', 'pvals', 'enrichment']]
    all_hits['target'] = all_hits['target'].astype(str)
    all_hits['prey'] = all_hits['prey'].astype(str)

    recalls = []
    precisions = []
    num_interactions = []

    # For recall-precisions, set default threshold if threshold is not defined
    if not thresholds:
        if pvals:
            thresholds = [1, 2, 3, 4.5, 6, 9, 12, 15, 20, 25, 30]
        else:
            thresholds = [0, 1, 2, 3, 4, 5, 6, 7]

    multi_args = zip(repeat(all_hits), repeat(corum), repeat(helas), thresholds)

    # multi processing
    p = Pool()
    if pvals:
        precision_recalls = p.starmap(precision_recall_pvals, multi_args)
    else:
        precision_recalls = p.starmap(precision_recall, multi_args)
    p.close()
    p.join()

    unzip_prs = list(zip(*precision_recalls))
    precisions, recalls, num_interactions = unzip_prs[0], unzip_prs[1], unzip_prs[2]


    pr_table = pd.DataFrame()
    pr_table['precision'] = precisions
    pr_table['recall'] = recalls
    pr_table['num_interactions'] = num_interactions

    return pr_table


def precision_recall(all_hits, corum, helas, threshold):
    """
    function for calulating precision recall in single threshold, used for parallel processing
    """

    test = all_hits.copy()
    test['thresh'] = test['enrichment'].apply(hp.calc_thresh, args=[3, threshold])
    test['hits'] = np.where((test['pvals'] > test['thresh']), True, False)
    test2 = test[test['hits']]
    num_interaction = test2.shape[0]

    cov, ov, _ = vali.corum_interaction_coverage_2(test2, corum, 'target', 'prey')
    recall = cov/ov

    test2 = vali.convert_to_unique_interactions(test2, 'target', 'prey')
    a_df, i_df = vali.return_colocalized_df(test2, helas, 'prot_1', 'prot_2')
    precision = i_df.shape[0] / a_df.shape[0]

    return [precision, recall, num_interaction]


def precision_recall_pvals(all_hits, corum, helas, threshold):
    """
    function for calulating precision recall in single threshold, used for parallel processing
    """

    test = all_hits.copy()
    test['hits'] = np.where((test['pvals'] > threshold), True, False)
    test2 = test[test['hits']]
    num_interaction = test2.shape[0]

    cov, ov, _ = vali.corum_interaction_coverage_2(test2, corum, 'target', 'prey')
    recall = cov/ov

    test2 = vali.convert_to_unique_interactions(test2, 'target', 'prey')
    a_df, i_df = vali.return_colocalized_df(test2, helas, 'prot_1', 'prot_2')
    precision = i_df.shape[0] / a_df.shape[0]

    return [precision, recall, num_interaction]


def interactors_precision_recall(all_hits, corum, helas):
    """
    function for calculating precision recall for already called hits
    """

    test2 = all_hits.copy()
    test2['target'] = test2['target'].astype(str)
    test2['prey'] = test2['prey'].astype(str)
    num_interaction = test2.shape[0]

    cov, ov, _ = vali.corum_interaction_coverage_2(test2, corum, 'target', 'prey')
    recall = cov/ov

    test2 = vali.convert_to_unique_interactions(test2, 'target', 'prey')
    a_df, i_df = vali.return_colocalized_df(test2, helas, 'prot_1', 'prot_2')
    precision = i_df.shape[0] / a_df.shape[0]

    return [precision, recall, num_interaction]

# def fdr_all_interactors(plates, root, date, fdr1, fdr5, dynamic=False,
#      metric=['pvals'], name='_pval_and_stoich_', just_hits=False):
#     """
#     Similar to get_all_interactors, but process interactions with
#     dynamic FDR and include the fdrs too
#     """
#     pval_plates = []
#     all_fdrs = []
#     for plate in plates:
#         df_name = root + plate + name + date + '.pkl'
#         pvals = pd.read_pickle(df_name)
#         if not dynamic:
#             pvals = pval.two_fdrs(pvals, fdr1, fdr5)
#         else:
#             fdrs, pvals = dfdr.get_fdrs(pvals)
#             # concatenate fdrs to pvals table
#             all_fdrs.append(fdrs)
#         pval_plates.append(pvals)

#     multi_args = zip(pval_plates, repeat(metric), repeat(just_hits))

#     # multi processing
#     p = Pool()
#     plate_hits = p.starmap(get_plate_interactors, multi_args)
#     p.close()
#     p.join()

#     all_hits = pd.concat(plate_hits, axis=0)
#     all_hits.reset_index(drop=True, inplace=True)
#     selected_cols = ['target', 'prey', 'hits', 'minor_hits'] + metric
#     all_hits = all_hits[selected_cols]
#     all_hits = all_hits.sort_values(by='target')
#     all_hits['plate'] = all_hits['target'].apply(lambda x: x.split('_', 1)[0])
#     all_hits['target'] = all_hits['target'].apply(lambda x: x.split('_', 1)[1])
#     all_hits['target'] = all_hits['target'].apply(lambda x: x.upper())
#     if dynamic:
#         fdrs = pd.concat(all_fdrs)
#         fdrs.reset_index(inplace=True)
#         fdrs['target'] = fdrs['bait'].apply(lambda x: x.split('_', 1)[1])
#         fdrs['plate'] = fdrs['bait'].apply(lambda x: x.split('_', 1)[0])
#         fdrs['target'] = fdrs['target'].apply(lambda x: x.upper())
#         fdrs.drop(columns=['bait'], inplace=True)
#         all_hits = all_hits.merge(fdrs, on=['target', 'plate'], how='left')

#     return all_hits
