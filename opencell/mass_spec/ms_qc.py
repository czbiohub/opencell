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

plt.style.use('ggplot')


#

def problematic_replicates(imputed_df, corr_thresh=0.7, cv_thresh=0.05):
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
    summary[cols[0]] = summary[cols[0]].apply(round, args=[2])
    summary[cols[1]] = summary[cols[1]].apply(round, args=[2])
    return summary, corr_fig, cv_fig


def replicates_qc_report(summary, corr_fig, cv_fig, exp_name='all_mbr',
        directory='qc/'):
    """From the output of replicates QC, generate a pdf report"""

    # save figures to png
    corr_fig.savefig(directory + exp_name + '_corr_fig.png')
    cv_fig.savefig(directory + exp_name + '_cv_fig.png')

    # initiate PDF
    pdf = FPDF('P', 'cm', 'Letter')
    pdf.add_page()
    pdf.set_font('Arial', '', 14)
    pdf.cell(0, 0.8, "QC Report - Technical Replicates", ln=1, align='C')

    # Add images to pdf
    pdf.image(directory + exp_name + '_corr_fig.png', x=0, y=1.8, w=10, h=6)
    pdf.image(directory + exp_name + '_cv_fig.png', x=10, y=1.8, w=10, h=6)
    pdf.cell(0, 5.8, ln=1)

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
    bins_list = np.arange(0, 1, 0.025)
    ax = corrs.plot.hist(label='', alpha=0.9, bins=bins_list)
    _ = ax.axvline(corr_thresh, label='Threshold: ' + str(corr_thresh),
                color=colors[1], linestyle='--', linewidth=4)
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
    bins_list = np.arange(0, 0.6, 0.25)
    ax = sum_cvs.plot.hist(label='', alpha=0.9, bins=bins_list)
    _ = ax.axvline(cv_thresh, label='Threshold: ' + str(cv_thresh),
                color=colors[1], linestyle='--', linewidth=4)
    _ = ax.set_xlabel("CV of total intensity", fontsize=18)
    _ = ax.set_ylabel("Bait Counts", fontsize=18)
    _ = ax.set_title("Total Intensity Variation between Replicates", fontsize=18)
    _ = ax.legend(fontsize=18)
    plt.close(fig)
    return fig


def match_qc_report(match_series, bait_match, match_fig, exp_name='all_mbr',
        directory='qc/'):
    """From the output of replicates QC, generate a pdf report"""

    # Process a list of all missing preys
    bait_match = list(set(bait_match.values.tolist()))
    bait_match.sort()

    # save figures to png
    match_fig.savefig(directory + exp_name + '_match_fig.png')

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
        pdf.cell(6, 0.5, '%s' % (match_series.index[i]), ln=0, align='C', border=1)
        pdf.cell(6, 0.5, '%s' % (match_series[i]), ln=1, border=1, align='C')

    pdf.cell(0, 0.5, ln=1)
    pdf.set_font('Arial', '', 14)
    pdf.cell(0, 1, "Missing / Unidentified Prey matches", align='C', ln=1)
    pdf.set_font('arial', '', 9)
    pdf.cell(7, 0.5, ln=0)
    pdf.cell(6, 0.5, "Bait", ln=1, align='C', border=1)
    for i in range(0, len(bait_match)):
        pdf.cell(7, 0.5, ln=0)
        pdf.cell(6, 0.5, '%s' % (bait_match[i]), ln=1, border=1)
    pdf.output(directory + exp_name + "_match_QC.pdf", 'F')


def plot_match_intensities(match_series, thresh):
    """ plot the fig of distributions of bait-prey match intensities

    rtype: fig.matplotlib figure"""

    fig, ax = plt.subplots(figsize=(12, 6))
    colors = plt.rcParams['axes.prop_cycle']
    colors = colors.by_key()['color']
    bins_list = np.arange(8, 32, 1)
    ax = match_series.plot.hist(label='', alpha=0.9, bins=bins_list)
    _ = ax.axvline(thresh, label='Threshold: ' + str(thresh),
                color=colors[1], linestyle='--', linewidth=4)
    _ = ax.set_xlabel("Total intensity (log2 transformed)", fontsize=18)
    _ = ax.set_ylabel("Bait Counts", fontsize=18)
    _ = ax.set_title("Total Intensity in Bait-Prey match", fontsize=18)
    _ = ax.legend(fontsize=18)
    plt.close(fig)
    return fig


def bait_match(raw_df, REs, replacement_RE, rep_re1=r'\d{8}_',
            rep_re2=r'_\d{2}', plot=True, thresh=20):
    """ Mass spec results of a specific bait should identify the same protein
    as prey, significantly. This function tests whether the bait-prey match is
    significantly enriched, and returns a fig and a table of QC hits that are below
    the threshold

    rtype: match_fig matplotlib fig
    rtype: hits pd DataFrame"""

    # Import raw file, taking raw intensities rather than LFQ
    qc_df = raw_df.copy()
    qc_df = pys.transform_intensities(qc_df, intensity_type='Intensity')
    qc_df.drop(['Intensity'], axis=1, inplace=True)

    # Use REs to simplify col_names to bait_## format
    col_list = list(qc_df)
    new_cols = pys.new_col_names(col_list, REs, replacement_RE)
    qc_df = pys.rename_cols(qc_df, col_list, new_cols)

    # DF set up for qc analysis
    qc_df.drop(['Protein IDs', 'Protein names', 'Fasta headers'],
        axis=1, inplace=True)

    # A list of prey targets that may have multiples (to be used later)
    multiples = qc_df['Gene names']
    multiples = multiples[multiples.apply(lambda x: True
        if ';' in x else False)]
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

    # Plot the histogram of the distribution
    if plot:
        match_fig = plot_match_intensities(match_series, thresh=thresh)
    else:
        match_fig = ''
    match_series = match_series[match_series < thresh].sort_values()
    match_series = match_series.apply(lambda x: np.round(x, 2))
    misnamed = pd.Series(misnamed)
    return match_series, misnamed, match_fig
