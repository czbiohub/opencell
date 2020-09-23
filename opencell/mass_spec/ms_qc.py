import matplotlib.pyplot as plt
import matplotlib
from numbers import Number
import numpy as np
import pandas as pd
import pyseus as pys
import imp
import plotly.offline
import plotly.graph_objects as go
import seaborn as sns
import plotly.figure_factory as ff
from scipy.cluster.hierarchy import linkage, leaves_list
from sklearn.cluster import KMeans
import time
import pdb
from fpdf import FPDF
import re
from matplotlib.colors import LogNorm
import math
import os

plt.style.use('ggplot')


def chosen_targets(renamed_df, bait='ATL3', output_dir=''):
    """check the Raw intensities of curated list of targets for ATL3,
    return a heatmap and a table"""

    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)

    # Curated list of targets
    if bait == 'ATL3':
        targets = ['ATL3', 'ATL2', 'RTN3', 'ATL1', 'ARCN1', 'RTN4', 'ESYT1',
    'RDH11', 'REEP4', 'REEP5', 'ARL6IP5', 'ARL6IP1', 'ESYT2', 'DHRS7', 'TMEM33']
    elif bait == 'CLTA':
        targets = ['CLTA', 'EDC4', 'AP1B1', 'EDC3', 'PIK3C2A', 'DCP2', 'DCP1A', 'SEC16A',
            'XRN1', 'AP1M1', 'CLTB', 'KIAA0430', 'CLTCL1', 'DCP1B', 'ALDH18A1',
            'AFTPH', 'PATL1', 'HIP1', 'DDX6', 'AP2A1', 'LSM2', 'YTHDC2',
            'EPN2', 'SCYL2', 'KIDINS220', 'CLTC', 'AP2S1', 'GAK', 'AP1G1',
            'AP2A2', 'IST1', 'GTSE1', 'SMAP2', 'BMP2K', 'AP2B1', 'CD2AP',
            'SH3D19', 'MAP7D2', 'IGF2BP3', 'LSM6', 'IGF2BP1', 'LSM4', 'IGF2R',
            'CHMP5', 'HEATR5B', 'HIP1R', 'HSPA4', 'CLINT1', 'LSM1', 'EPS15',
            'AP2M1', 'C10orf88', 'HNRNPL', 'AP1S2', 'FMR1', 'LSM14A',
            'CHMP2A', 'CPSF7', 'NBR1', 'EPN1', 'EIF4ENIF1', 'LSM7',
            'CCNB1', 'SPAST', 'STAU1', 'LSM14B', 'SEC24B', 'ZBTB10',
            'VTI1B', 'BAG2', 'PNRC1', 'EIF4E', 'BTBD6', 'UPF1', 'HELZ',
            'STX8', 'STX12', 'CHMP2B', 'RPL35A', 'BTBD3', 'CALCOCO1',
            'VPRBP', 'RPS26', 'STUB1', 'TFRC', 'KLHL20', 'PICALM',
            'ENPP4', 'DDX17', 'AAK1', 'HSPA1L', 'RPL13A;RPL13a',
            'FXR1', 'AAK1', 'LSM5', 'VAMP4', 'SORT1', 'DHX9',
            'DYRK1A', 'RPL36', 'L1RE1', 'HNRNPA0', 'REPS1',
            'STX10', 'RPS17L;RPS17', 'DNAJC6', 'NONO', 'MAGED1',
            'NUDT21', 'IGF2BP2', 'MEA1', 'IQSEC1', 'EIF3J',
            'EPS15L1', 'RPLP0;RPLP0P6', 'VTA1', 'DDX5',
            'SART3', 'DYNLL1;DYNLL2', 'RPS23', 'RAB5C', 'RPS13',
            'CHMP3', 'HSPA2', 'BAG4', 'HSPA9', 'EIF3C;EIF3CL',
            'DDX3X', 'RPL5', 'PYCR1', 'RPL30', 'SMG7', 'CLSPN',
            'YBX1;YBX3', 'HSPA1B;HSPA1A', 'EIF3H', 'RPL11', 'ABCE1', 'RPL10A']


    # initiate a dataframe of specified protein groups file
    atl3 = renamed_df.copy()
    # orig_cols = list(atl3)
    # new_cols = pys.new_col_names(orig_cols, REs, rep_REs)
    # atl3 = pys.rename_cols(atl3, orig_cols, new_cols)
    atl3.set_index('Gene names', inplace=True)

    # Select only columns that are ATL3
    atl_cols = [col for col in list(atl3) if (bait in col) & ('LFQ' not in col)]

    atl3 = atl3[atl_cols].copy()

    # Some rows will not be present because they are not detected
    # Identify these rows and add them to the df as an array of 0's

    target_set = set(targets)
    preys = set(list(atl3.T))
    missing = target_set - preys
    atl3 = atl3.T
    for col in missing:
        atl3[col] = [0] * atl3.shape[0]
    atl3 = atl3.T

    # Calculate target proportioned to total intensity
    atl3_frac = pd.DataFrame()
    for col in atl_cols:
        col_sum = np.nansum(atl3[col])
        atl3_frac[col] = atl3[col].apply(lambda x: (100*x) / col_sum)
        atl3_frac[col] = atl3_frac[col].apply(lambda x: 0.001 if x == 0 else x)

    # Grab only curated targets
    atl3_target_frac = atl3_frac.T[targets].T

    # Save a csv of the dataframe
    # atl3_target_frac.to_csv(output_dir + bait + '_target_frac.csv')

    # Convert 0s into something plottable in logscale
    # for col in atl_cols:
    #     atl3_frac[col] = atl3_frac[col].apply(lambda x: 0.0001 if x == 0 else x)


    # Plot and save a heatmap
    heatmap_atl3_frac(atl3_target_frac, bait, output_dir)

    # Calculate raw target intensities
    atl3_target = atl3.T[targets].T

    # Export the csv of the raw target
    # atl3_target.to_csv(output_dir + bait + '_target_raw.csv')

    # Convert to log2 scale for heatmap, replace 0 with something plottable
    for col in atl_cols:
        atl3_target[col] = atl3_target[col].apply(lambda x: np.log2(1024)
            if x == 0 else np.log2(x))

    # Plot and save a heatmap
    heatmap_atl3_raw(atl3_target, bait, output_dir)


def heatmap_atl3_frac(atl3_target_frac, bait, output_dir):
    """Plot and save heatmap of target fractions"""

    # Set up log colormap axes
    vmin = atl3_target_frac.min().min()
    vmax = atl3_target_frac.max().max() + 5
    lognorm = LogNorm(vmin=vmin, vmax=vmax)
    cbar_ticks = [math.pow(10, i) for i in range(math.floor(math.log10(vmin)),
        1+math.ceil(math.log10(vmax)))]

    # Plot the data
    if bait == 'ATL3':
        fig, ax = plt.subplots(figsize=(12, 10))
        ax.tick_params(axis="y", labelsize=14)
    elif bait == 'CLTA':
        fig, ax = plt.subplots(figsize=(12, 24))
        ax.tick_params(axis="y", labelsize=7)
    ax = sns.heatmap(atl3_target_frac, norm=lognorm,
        cbar_kws={'ticks': cbar_ticks}, cmap="YlGnBu")
    ax.set_ylim(atl3_target_frac.shape[0], 0)
    ax.set_title(bait + " Known Targets (% Raw Intensity / Total)", fontsize=20)
    ax.tick_params(axis="x", labelsize=14)
    cax = plt.gcf().axes[-1]
    cax.tick_params(labelsize=16)
    plt.ylabel('Curated Preys', fontsize=20)
    plt.savefig(output_dir + bait + "_fraction.pdf", bbox_inches='tight')
    plt.close(fig)


def heatmap_atl3_raw(atl3_target, bait, output_dir):
    """Plot and save heatmap of target fractions"""

    # Plot the data
    if bait == 'ATL3':
        fig, ax = plt.subplots(figsize=(12, 10))
        ax.tick_params(axis="y", labelsize=14)
    elif bait == 'CLTA':
        fig, ax = plt.subplots(figsize=(12, 24))
        ax.tick_params(axis="y", labelsize=7)
    ax = sns.heatmap(atl3_target, cmap="YlGnBu", vmin=10, vmax=26)
    ax.set_ylim(atl3_target.shape[0], 0)
    ax.set_title(bait + " Known Targets (Raw intensity, log2)", fontsize=20)
    ax.tick_params(axis="x", labelsize=14)
    cax = plt.gcf().axes[-1]
    cax.tick_params(labelsize=16)
    plt.ylabel('Curated Preys', fontsize=20)
    plt.savefig(output_dir + bait + "_raw.pdf", bbox_inches='tight')
    plt.close(fig)


def problematic_replicates(imputed_df, corr_thresh=0.65, cv_thresh=0.05):
    """ Using profile correlation between replicates, and coefficient of
    Variation between total sum of replicate intensities - find outliers
    in baits that are not replicating well

    rtype: problem_df pd DataFrame
    rtype: cv_fig matplotlib figure
    rtype corr_fig matplotlib figure"""

    # prep the df for easy QC checks
    qc = imputed_df.copy()
    qc.drop('Info', level='Baits', inplace=True, axis=1)
    bait_list = list(set([col[0] for col in list(qc)]))

    # Find CVs betwee total intensities of replicates
    cvs_dict = {}

    for bait in bait_list:
        sums = qc[bait].sum()
        cv = sums.std()/sums.mean()
        cvs_dict[bait] = cv
    sum_cvs = pd.Series(cvs_dict, name="Sum Intensity CVs")

    # Create a plot to visualize distribution
    cv_fig = plot_CV_fig(sum_cvs, cv_thresh)

    # Filter the series to contain only hits above the threshold
    hits_cvs = sum_cvs[sum_cvs > cv_thresh].sort_values(ascending=False)

    # Find correlations between replicates
    corr_dict = {}
    for bait in bait_list:
        corr_list = qc[bait].corr().values.flatten().tolist()
        corr_list = list(set(corr_list))
        corr_min = np.min(corr_list)

        # get the lowest correlation coefficient
        corr_dict[bait] = corr_min

    corrs = pd.Series(corr_dict, name="Corr between Replicates")


    # Create a plot to visualize distribution
    corr_fig = plot_corr_fig(corrs, corr_thresh)

    # Filter the series to contain hits
    hits_corrs = corrs[corrs < corr_thresh].sort_values()

    summary = pd.DataFrame(hits_corrs).join(hits_cvs, how='outer')


    # Sort the summary df in a useful way

    cols = list(summary)
    first = summary.dropna()

    first = first.sort_values(by=[cols[1]], ascending=False)
    first = first.sort_values(by=[cols[0]], ascending=True)

    remaining = [x for x in list(summary.index) if x not in list(first.index)]
    rems = summary.T[remaining].T
    rems = rems.sort_values(by=[cols[1]], ascending=False)
    rems = rems.sort_values(by=[cols[0]], ascending=True)

    summary = pd.concat([first, rems])
    summary[cols[0]] = summary[cols[0]].apply(round, args=[3])
    summary[cols[1]] = summary[cols[1]].apply(round, args=[3])
    return summary, corr_fig, cv_fig


def replicates_qc_report(summary, corr_fig, cv_fig, exp_name='all_mbr',
        directory='qc/'):
    """From the output of replicates QC, generate a pdf report"""

    if not os.path.isdir(directory):
        os.mkdir(directory)

    # save figures to png
    corr_fig.savefig(directory + exp_name + '_corr_fig.png',
        bbox_inches='tight')
    cv_fig.savefig(directory + exp_name + '_cv_fig.png',
        bbox_inches='tight')

    # initiate PDF
    pdf = FPDF('P', 'cm', 'Letter')
    pdf.add_page()
    pdf.set_font('Arial', '', 14)
    pdf.cell(0, 0.8, "QC Report - Technical Replicates", ln=1, align='C')

    # Add images to pdf
    pdf.image(directory + exp_name + '_corr_fig.png', x=4, y=1.8, w=12, h=6)
    pdf.image(directory + exp_name + '_cv_fig.png', x=4, y=7.8, w=12, h=6)
    pdf.cell(0, 12.5, ln=1)

    # Generate Hits table
    pdf.cell(0, 0.8, "Poor QC Hits", align='C', ln=1)
    pdf.set_font('arial', '', 9)
    pdf.cell(6, 0.5, "Bait", ln=0, align='C', border=1)
    pdf.cell(6, 0.5, "Correlation between Replicates", ln=0, align='C', border=1)
    pdf.cell(6, 0.5, "Sum Intensity CVs", align='C', border=1, ln=1)
    for i in range(0, summary.shape[0]):
        pdf.cell(6, 0.5, '%s' % (summary.index[i]), ln=0, align='C', border=1)
        pdf.cell(6, 0.5, '%s' % (summary['Corr between Replicates'][i]),
            ln=0, border=1, align='C')
        pdf.cell(6, 0.5, '%s' % (summary['Sum Intensity CVs'][i]), ln=1,
            border=1, align='C')

    pdf.output(directory + exp_name + "_replicate_QC.pdf", 'F')


def plot_corr_fig(corrs, corr_thresh):
    """ plot the fig of correlation distributions between replicates

    rtype: fig matplotlib figure
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    colors = plt.rcParams['axes.prop_cycle']
    colors = colors.by_key()['color']
    bins_list = np.arange(0, 1, 0.01)
    ax = corrs.plot.hist(label='', alpha=0.9, bins=bins_list)
    _ = ax.axvline(corr_thresh, label='Threshold: ' + str(corr_thresh),
                color=colors[1], linestyle='--', linewidth=4)
    ax.tick_params(axis="x", labelsize=15)
    ax.tick_params(axis="y", labelsize=15)
    _ = ax.set_xlabel("Correlation", fontsize=18)
    _ = ax.set_xlim(0.1, 1)
    _ = ax.set_ylabel("Bait Counts", fontsize=18)
    _ = ax.set_title("Replicate Correlation Distribution", fontsize=18)
    _ = ax.legend(fontsize=18)
    plt.close(fig)
    return fig


def plot_CV_fig(sum_cvs, cv_thresh):
    """ plot the fig of bait distributions of CV between replicates

    rtype: fig matplotlib figure
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    colors = plt.rcParams['axes.prop_cycle']
    colors = colors.by_key()['color']
    bins_list = np.arange(0, 0.6, 0.005)
    ax = sum_cvs.plot.hist(label='', alpha=0.9, bins=bins_list)
    _ = ax.axvline(cv_thresh, label='Threshold: ' + str(cv_thresh),
                color=colors[1], linestyle='--', linewidth=4)
    _ = ax.set_xlim(0, 0.2)
    ax.tick_params(axis="x", labelsize=15)
    ax.tick_params(axis="y", labelsize=15)
    _ = ax.set_xlabel("CV of total intensity", fontsize=18)
    _ = ax.set_ylabel("Bait Counts", fontsize=18)
    _ = ax.set_title("Intensity Variation between Replicates", fontsize=18)
    _ = ax.legend(fontsize=18)
    plt.close(fig)
    return fig


def match_qc_report(match_series, no_match, thresh, exp_name='all_mbr',
        directory='qc/'):
    """From the output of replicates QC, generate a pdf report"""
    if not os.path.isdir(directory):
        os.mkdir(directory)

    # Process a list of all missing preys
    no_match = list(set(no_match.values.tolist()))
    no_match.sort()

    # save figures to png
    match_fig = plot_match_intensities(match_series, thresh)
    match_fig.savefig(directory + exp_name + '_match_fig.png')

    # Filter for below threshold
    match_series = match_series.copy()
    match_series = match_series[match_series['match intensity'] < thresh]
    match_series.reset_index(inplace=True)
    # initiate PDF
    pdf = FPDF('P', 'cm', 'Letter')
    pdf.add_page()
    pdf.set_font('Arial', '', 14)
    pdf.cell(0, 0.8, "QC Report - Bait-Prey Match", ln=1, align='C')

    # Add images to pdf
    pdf.image(directory + exp_name + '_match_fig.png', x=3, y=1.8, w=16, h=8)
    pdf.cell(0, 8, ln=1)

    # Generate Hits table
    pdf.cell(0, 1, "Poor QC Hits", align='C', ln=1)
    pdf.set_font('arial', '', 9)
    pdf.cell(4, 0.5, ln=0)
    pdf.cell(6, 0.5, "Bait", ln=0, align='C', border=1)
    pdf.cell(6, 0.5, "Total intensity", ln=1, align='C', border=1)

    for i in range(0, match_series.shape[0]):
        pdf.cell(4, 0.5, ln=0)
        pdf.cell(6, 0.5, '%s' % (match_series.loc[i]['bait']), ln=0, align='C', border=1)
        pdf.cell(6, 0.5, '%s' % (match_series.loc[i]['match intensity']), ln=1, border=1, align='C')

    pdf.cell(0, 0.5, ln=1)
    pdf.set_font('Arial', '', 14)
    pdf.cell(0, 1, "Missing / Unidentified Prey matches", align='C', ln=1)
    pdf.set_font('arial', '', 9)
    pdf.cell(7, 0.5, ln=0)
    pdf.cell(6, 0.5, "Bait", ln=1, align='C', border=1)
    for i in range(0, len(no_match)):
        pdf.cell(7, 0.5, ln=0)
        pdf.cell(6, 0.5, '%s' % (no_match[i]), ln=1, border=1)
    pdf.output(directory + exp_name + "_match_QC.pdf", 'F')


def plot_match_intensities(match_df, thresh):
    """ plot the fig of distributions of bait-prey match intensities

    rtype: fig.matplotlib figure"""

    plt.style.use('ggplot')
    fig, ax = plt.subplots(figsize=(12, 8))
    ax = sns.swarmplot(data=match_df, x='experiment', y='match intensity')
    ax.tick_params(axis="x", labelsize=13, labelrotation=40)
    ax.tick_params(axis="y", labelsize=13)
    ax.axhline(thresh, linestyle='--')
    plt.xlabel('Experiment', fontsize=18)
    plt.ylabel('Raw Intensity (log2)', fontsize=18)
    _ = plt.title("Bait-match Intensities")
    plt.close(fig)
    return fig


def bait_match(transformed_df, rep_re1=r'^\d{8}_',
            rep_re2=r'_\d{2}'):
    """ Mass spec results of a specific bait should identify the same protein
    as prey, significantly. This function tests whether the bait-prey match is
    significantly enriched, and returns a fig and a table of QC hits that are below
    the threshold

    rtype: match_fig matplotlib fig
    rtype: hits pd DataFrame"""

    qc_df = transformed_df.copy()
    # new_cols = [x for x in list(qc_df) if 'LFQ' not in x]
    # qc_df = qc_df[new_cols]
    # DF set up for qc analysis
    qc_df.drop(['Protein IDs', 'Protein names', 'Fasta headers'],
        axis=1, inplace=True)

    # A list of prey targets that may have multiples (to be used later)
    multiples = qc_df['Gene names']
    # pdb.set_trace()
    multiples = multiples[multiples.apply(lambda x: True
        if ';' in str(x) else False)]
    multiples = multiples.values.tolist()

    qc_df.set_index('Gene names', inplace=True)

    bait_list = list(qc_df)


    # dict to save info
    bait_match = {}

    # List to add unidentified preys
    misnamed = {}

    # REs to remove replicate number to search for
    rep_re1 = rep_re1
    rep_re2 = rep_re2


    # Iterate through each bait/replicate and get the prey match intensity

    for bait in bait_list:
        prey_name = re.sub(rep_re1, '', bait)
        prey_name = re.sub(rep_re2, '', prey_name)

        try:
            prey_intensity = qc_df[bait][prey_name]
            if isinstance(prey_intensity, Number):
                bait_match[bait] = prey_intensity
            else:
                prey_intensity = np.nanmax(prey_intensity.values)
                bait_match[bait] = prey_intensity
        except Exception:
            # error occurs when prey name is not found
            # one of the reasons is that target preys could be in multiples
            # identify if this is so.
            for preys in multiples:
                in_multiples = prey_name in preys
                # if prey is found, add the prey match intensity
                if in_multiples:
                    prey_intensity = qc_df[bait][preys]
                    bait_match[bait] = prey_intensity
                    break
            # If prey is not found, append in misnamed list
            if not in_multiples:
                misnamed[bait] = prey_name

    match_series = pd.Series(bait_match)
    match_series = match_series.apply(lambda x: np.round(x, 2))
    match_df = pd.DataFrame(match_series)
    match_df.rename(columns={0: 'match intensity'}, inplace=True)
    match_df.index.rename('bait', inplace=True)
    misnamed = pd.Series(misnamed)
    return match_df, misnamed


def hela_summary(hela_dir, exp_name):
    """ Return the total peptides and proteins identified in an experiment:
    mostly used for HeLa

    rtype pep_count : list
    rtype prot_count : list"""

    all_peps = pd.read_csv(hela_dir + 'peptides.txt', sep='\t', header=0,
                    low_memory=False)
    hela_cols = [x for x in list(all_peps) if (('Experiment' in x) & ('Hela' in x))]

    # get the peptide counts for each replicate
    pep_count = [all_peps[col].count() for col in hela_cols]

    prots = pd.read_csv(hela_dir + 'proteinGroups.txt', sep='\t', header=0,
                    low_memory=False)
    ms_cols = [x for x in list(prots) if (('MS/MS count' in x) & ('Hela' in x))]

    # get the protein counts for each replicate
    prot_count = [int(prots[col].apply(lambda x: 0 if x == 0 else 1).sum()) for col in ms_cols]

    hela_summary = pd.DataFrame()
    hela_summary['experiment'] = [exp_name] * len(pep_count)
    hela_summary['peptide_count'] = pep_count
    hela_summary['protein_count'] = prot_count

    return hela_summary


def pulldown_summary(plate, renamed, transformed, rep_re, pep_re):
    """From a plate number and a renamed df from proteinGroups,
    prepare dataframe compatible to generate summary table used to plot
    total intensity of each bait and also number of peptides identified
    by MS/MS"""

    renamed = renamed.copy()
    transformed = transformed.copy()

    # get a list of intensity columns
    cols = list(renamed)
    intensity_cols = pys.select_intensity_cols(cols, rep_re)
    intensity_df = renamed[intensity_cols]

    # generate a df of total intensities for each replicate
    intensities = pd.DataFrame(intensity_df.sum(axis=0)).rename(columns={0:
        'total intensity'})
    intensities.index.rename('bait', inplace=True)
    bait_list = intensities.index.to_list()
    intensities['total intensity'] = intensities['total intensity'].apply(np.log2)
    # import the peptides table to get total peptides identified for bait
    peptides = pd.read_csv(plate + 'peptides.txt', sep='\t', header=0,
        low_memory=False)
    pep_cols = list(peptides)
    pep_ids = [x for x in pep_cols if 'Identification type' in x]

    peptides = peptides[pep_ids]
    peptides = pys.rename_cols(peptides, pep_ids, bait_list)

    # Calculate total peptides identified by MSMS
    ms_counts = pd.DataFrame()
    for col in bait_list:
        try:
            ms_counts[col] = [peptides[col].value_counts()['By MS/MS']]
        except Exception:
            continue
    ms_counts = ms_counts.T
    ms_counts.rename(columns={0: 'identified peptides'}, inplace=True)
    ms_counts.index.rename('bait', inplace=True)

    # Combine total intensities and total peptides dataframes
    master = ms_counts.join(intensities, on='bait')

    # Calculate bait matches
    match_df, no_match = bait_match(transformed, rep_re1=rep_re)

    master = master.join(match_df, on='bait')
    master.reset_index(inplace=True)
    master['experiment'] = master['bait'].apply(lambda x: x[:4])

    return master, no_match


def pulldown_plot(summary, output, plate, width=20):
    """Plot a summary figure and save a pdf to the designated output folder"""

    if not os.path.isdir(output):
        os.mkdir(output)
    fig, ax = plt.subplots(3, 1, figsize=(width, 10))
    _ = sns.violinplot(x='experiment', y='identified peptides', data=summary,
        inner='quartile', ax=ax[0])
    ax[0].set(ylim=(0, 5000))
    _ = sns.violinplot(x='experiment', y='total intensity', data=summary,
        inner='quartile', ax=ax[1])
    ax[1].set(ylim=(26, 32))
    # ax[1].set_yscale('log')

    _ = sns.violinplot(x='experiment', y='match intensity', data=summary,
        inner='quartile', ax=ax[2])
    ax[2].set(ylim=(12, 32))
    ax[0].set_xlabel('')
    ax[1].set_xlabel('')
    ax[2].set_xlabel('Experiment', fontsize=18)
    ax[0].set_ylabel('Peptide Counts (MS/MS)', fontsize=14)
    ax[1].set_ylabel('Total Raw Intensity (log2)', fontsize=14)
    ax[2].set_ylabel('Bait Match Intensity (log2)', fontsize=14)
    for i in np.arange(3):
        ax[i].xaxis.set_tick_params(labelsize=12)
        ax[i].yaxis.set_tick_params(labelsize=12)
    ax[0].set_title("Summary Stats for MS Experiments", fontsize=20)
    plt.close(2)
    plt.close(3)

    fig.tight_layout()
    plt.savefig(output + plate + '_summary.pdf', bbox_inches='tight')


def hela_plot(hela_summary, output):
    fig, ax = plt.subplots(2, 1, figsize=(10, 10))
    _ = sns.catplot(x='experiment', y='peptide_count', data=hela_summary, s=10, ax=ax[0])
    ax[0].set(ylim=(10000, 18000))
    _ = sns.catplot(x='experiment', y='protein_count', data=hela_summary, s=10, ax=ax[1])
    ax[1].set(ylim=(2000, 4000))
    ax[0].set_xlabel('')
    ax[1].set_xlabel('Experiment', fontsize=18)
    ax[0].set_ylabel('Peptide Counts', fontsize=16)
    ax[1].set_ylabel('Protein Counts', fontsize=16)
    ax[0].xaxis.set_tick_params(labelsize=12)
    ax[1].xaxis.set_tick_params(labelsize=12)
    ax[0].yaxis.set_tick_params(labelsize=12)
    ax[1].yaxis.set_tick_params(labelsize=12)
    ax[0].set_title("HeLa QC", fontsize=24)
    plt.close(2)
    plt.close(3)

    fig.tight_layout()

    plt.savefig(output, bbox_inches='tight')
