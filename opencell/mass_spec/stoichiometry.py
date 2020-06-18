import pyseus as pys
import pandas as pd
import numpy as np
import re
import multiprocessing
from multiprocessing import Pool
from itertools import repeat
import pdb
import sys
from Bio import SeqIO
from collections import defaultdict

from opencell.database import models
from opencell.database import utils
from opencell.database import ms_utils
from opencell.database import ms_operations as ms_ops
from opencell.imaging import processors
from opencell import constants
import sqlalchemy
# from eralchemy import render_er
from sqlalchemy import inspect
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Numeric
from sqlalchemy.orm import sessionmaker



def compute_stoich_df(m_imputed, seq_df, rnaseq, pvals, pull_uni, target_re=r'P\d{3}_(.*)'):
    """
    wrapper function to generate interaction stoich data
    and abundance stoich data in a dataframe
    """

    pvals = pvals.copy()
    rnaseq = rnaseq.copy()

    stoi_df = multi_theoretical_peptides(m_imputed, seq_df)
    stoi_df = pys.median_replicates(stoi_df)
    divided = divide_by_theoretical_peptides(stoi_df, 'median ')
    final_stoi = divide_by_bait(divided, pull_uni)

    # remove median headings
    col_names = list(final_stoi)
    med_RE = ['median ']
    replacement_RE = ['']
    new_cols = pys.new_col_names(col_names, med_RE, replacement_RE)
    final_stoi = pys.rename_cols(final_stoi, col_names, new_cols)

    final_stoi = abundance_stoichiometry(final_stoi, rnaseq, ms=True)
    # return final_stoi

    final_stoi.set_index('Protein IDs', drop=True, inplace=True)
    tpm_vals = final_stoi[['Gene names', 'tpm_ave']].copy()

    final_stoi.drop(
        columns=['Gene names', 'Protein names', 'Majority protein IDs',
        'Fasta headers', 'tpm_ave'], inplace=True)


    baits = list(set(pvals.columns.get_level_values(0).tolist()))

    # Append abundance stoichiometries
    abundance_stoi = pd.DataFrame()
    for bait in baits:
        if bait == 'gene_names':
            continue
        pvals[(bait, 'interaction_stoi')] = None
        pvals[(bait, 'abundance_stoi')] = None
        try:
            target = re.search(target_re, bait).groups()[0]
        except Exception:
            print(bait)
        target_row = tpm_vals[tpm_vals['Gene names'] == target]
        if target_row.shape[0] >= 1:
            target_tpm = target_row['tpm_ave'].iloc[0]
            if target_tpm:
                if target_tpm > 0:
                    abundance_stoi[bait] = tpm_vals['tpm_ave'] / target_tpm

    abundance_stoi.columns = pd.MultiIndex.from_product(
        [abundance_stoi.columns, ['abundance_stoi']])
    pvals.update(abundance_stoi, join='left')

    # Append interaction stoichiometries
    interaction_stoi = final_stoi.copy()
    interaction_stoi.columns = pd.MultiIndex.from_product(
        [interaction_stoi.columns, ['interaction_stoi']])
    pvals.update(interaction_stoi, join='left')

    pvals.sort_index(inplace=True, axis=1)
    return pvals



def fasta_df(addr):
    # read Uniprot fasta file
    seq_dict = {rec.id : rec.seq.__str__() for rec in SeqIO.parse(addr, "fasta")}

    # Turn fasta dict into df
    seq_df = pd.DataFrame.from_dict(seq_dict, orient='index')
    seq_df.reset_index(inplace=True)
    seq_df.rename(columns={'index': 'reference', 0: 'sequence'},
        inplace=True)

    # Get the protein id from Fasta reference
    seq_df['protein_id'] = seq_df['reference'].apply(
        lambda x: re.split('[|]', x)[1])

    return seq_df


def multi_theoretical_peptides(imputed_df, seq_df, cut='K', pmin=7, pmax=30):
    """
    Returns a new PD df with 'num_theoretical_peptides" column
    """

    imputed_df = imputed_df.copy()
    seq_df = seq_df.copy()

    # Get a list of majority protein IDs, and feed into multiprocess Pool
    protein_ids = imputed_df[('Info', 'Majority protein IDs')].tolist()

    # multi args for parallel pool
    multi_args = zip(protein_ids, repeat(seq_df), repeat(cut),
        repeat(pmin), repeat(pmax))


    # start multiprocessing
    p = Pool()
    num_peps = p.starmap(theoretical_peptides, multi_args)
    p.close()
    p.join()

    # add new column to imputed_df, and return the dataframe
    imputed_df[('Info', 'num_theoretical_peptides')] = num_peps
    imputed_df.sort_index(axis=1, inplace=True)
    return imputed_df


def theoretical_peptides(protein_ids, seq_df, cut='K', pmin=7, pmax=30):
    """ For each protein group, calculate the theoretical number of peptides
    in ms after digestion """

    # protein ids is a string list with ; as separator, convert to a list
    protein_ids = protein_ids.split(';')

    all_nums = []
    for protein_id in protein_ids:
        # fetch the fasta sequence
        reference_row = seq_df[seq_df['protein_id'] == protein_id]['sequence']
        if reference_row.shape[0] == 1:
            sequence = reference_row.item()
        else:
            continue

        # split by cut (Lysine)
        digests = pd.DataFrame()
        digests['peptides'] = sequence.split('K')
        # Length of the cuts (excluding lysine)
        digests['len'] = digests['peptides'].apply(lambda x: len(x))

        # Get the number of fragments that qualify peptide length threshold
        num_peps = digests[(digests['len'] > pmin - 1)
            & (digests['len'] < pmax + 1)].shape[0]

        # append to master list
        all_nums.append(num_peps)
    return np.median(all_nums)


def exp2(x):
    return 2 ** x


def divide_by_theoretical_peptides(median_stoi_df, intensity_re='median '):
    """ divide intensities by calculated theoretical peptides"""
    median_stoi_df = median_stoi_df.copy()
    absolute_intensity = pys.transform_intensities(median_stoi_df,
        intensity_type="median ", func=exp2)

    intensity_cols = pys.select_intensity_cols(list(absolute_intensity), intensity_re)

    # for each intensity column, transform the values
    for int_col in intensity_cols:
        absolute_intensity[int_col] = absolute_intensity[int_col]\
            / median_stoi_df['num_theoretical_peptides']

    return absolute_intensity


def divide_by_bait(divided_df, pull_uni, intensity_re=r'P(\d{3})_(.*)'):
    """
    divide by the normalized bait intensity to get final stoichiometry
    """
    pull_uni = pull_uni.copy()

    divided_df = divided_df.copy()
    cols = list(divided_df)
    for col in cols:
        gene_names = []

        search = re.search(intensity_re, col)
        target = ''
        if search:
            plate = search.groups()[0]
            plate = ms_utils.format_ms_plate(plate)

            target = search.groups()[1]
            re_target = re.sub(r'-.*$', '', target, flags=re.IGNORECASE)
        else:
            continue

        if target:
            uni_row = pull_uni[
                (pull_uni['pulldown_plate_id'] == plate) & (pull_uni['target_name'] == re_target)]

            if uni_row.shape[0] == 0:
                uni_row = pull_uni[
                    (pull_uni['pulldown_plate_id'] == plate) & (
                        pull_uni['gene_names'].apply(lambda x: re_target in x))]
            if uni_row.shape[0] > 0:
                uni_row = uni_row.iloc[0]
                gene_names = uni_row.gene_names

            target_row = divided_df[divided_df['Gene names'].apply(
                lambda x: re_target in x)]
            if target_row.shape[0] > 0:
                target_intensity = target_row[col].max()
                divided_df[col] = divided_df[col] / target_intensity

            elif gene_names:
                matches = []
                for gene in gene_names:
                    target_row = divided_df[divided_df['Gene names'].apply(
                        lambda x: gene in x)]
                    if target_row.shape[0] > 0:
                        matches.append(target_row)
                if matches:
                    target_row = pd.concat(matches)
                    target_intensity = target_row[col].max()
                    divided_df[col] = divided_df[col] / target_intensity
                else:
                    print(target + " not found")
                    divided_df.drop(col, axis=1, inplace=True)
            else:
                print(target + " not found")
                divided_df.drop(col, axis=1, inplace=True)


        else:
            divided_df.drop(col, axis=1, inplace=True)
    return divided_df


def abundance_stoichiometry(stoich_df, rnaseq_df, ms=True):
    """
    """
    stoich_df = stoich_df.copy()
    rnaseq_df = rnaseq_df.copy()
    if ms:
        rnaseq_df = rnaseq_df[
            [('Info', 'Gene names'), ('Normalized Intensity', 'Normalized Intensity')]]
        rnaseq_df.columns = rnaseq_df.columns.droplevel('Baits')
        rnaseq_df.rename(
            columns={
                'Gene names': 'gene', 'Normalized Intensity': 'tpm_ave'}, inplace=True)

    else:
        rnaseq_df.drop(columns='major coding ENST', inplace=True)

    rnaseq_df['gene'] = rnaseq_df['gene'].astype(str)

    stoich_gene_set = set(stoich_df['Gene names'].tolist())
    rnaseq_gene_set = set(rnaseq_df['gene'].tolist())

    genes_intersect = stoich_gene_set.intersection(rnaseq_gene_set)

    genes_missing = stoich_gene_set - rnaseq_gene_set


    missing_dict = defaultdict(list)
    for genes in list(genes_missing):
        gene_list = genes.split(';')
        for gene in gene_list:
            if gene in rnaseq_gene_set:
                missing_dict[genes].append(gene)

    # completely_missing = genes_missing - set(missing_dict.keys())

    # stoich_drop_idx = stoich_df[stoich_df['Gene names'].isin(completely_missing)].index
    # stoich_df.drop(stoich_drop_idx, inplace=True)

    rnaseq_stoich = rnaseq_df[rnaseq_df['gene'].isin(genes_intersect)]

    for missing_gene in list(missing_dict.keys()):
        sum_tpm = rnaseq_df[
            rnaseq_df['gene'].isin(missing_dict[missing_gene])]['tpm_ave'].sum()
        rnaseq_stoich = rnaseq_stoich.append(pd.Series({'gene': missing_gene,
            'tpm_ave': sum_tpm}), ignore_index=True)

    stoich_df.set_index('Gene names', drop=True, inplace=True)
    rnaseq_stoich = rnaseq_stoich.groupby('gene').sum()
    # rnaseq_stoich.set_index('gene', drop=True, inplace=True)
    stoich_df['tpm_ave'] = None
    stoich_df.update(rnaseq_stoich, join='left')
    stoich_df = stoich_df.reset_index().rename(columns={'index': 'Gene names'})

    return stoich_df


def fetch_uniprot_meta(url):
    url = utils.url_from_credentials('../../../db-credentials-cap.json')
    engine = sqlalchemy.create_engine(url)
    engine.connect()

    # fetch table and process right columns
    uniprot_meta = pd.read_sql(
        'select * from crispr_design inner join uniprot_metadata using (uniprot_id)', engine)
    uni = uniprot_meta[['plate_design_id', 'well_id', 'target_name', 'gene_names']]
    uni['gene_names'] = uni['gene_names'].apply(lambda x: x.split(' '))

    return uni
