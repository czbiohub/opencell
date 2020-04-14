import matplotlib.pyplot as plt
import matplotlib
from numbers import Number
import numpy as np
import pandas as pd
import plotly.offline
import plotly.graph_objects as go
import plotly.figure_factory as ff
from plotly.subplots import make_subplots
import re


def stoich_plot(v_df, bait, target_re=r'P\d{3}_(.*)'):
    """plot the volcano plot of a given bait"""
    v_df = v_df.copy()

    # Specify the bait column
    bait_vals = v_df[bait]
    tpm_vals = v_df[['Gene names', 'tpm_ave']]


    # Calculate tpm stoich
    target = re.search(target_re, bait).groups()[0]
    target_row = tpm_vals[tpm_vals['Gene names'] == target]
    if target_row.shape[0] == 1:
        target_tpm = target_row['tpm_ave'].item()
    else:
        raise ValueError(target + " not found in list of preys")

    tpm_vals = tpm_vals['tpm_ave'] / target_tpm



    # xmax = hits['enrichment'].max() + 3
    # if hits.shape[0] > 0:
    #     ymax = hits['pvals'].max() + 4
    # else:
    #     ymax = 30

    # Figure Generation
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=bait_vals, y=tpm_vals,
        mode='markers', text=v_df['Gene names'].tolist(), textposition='bottom right',
        opacity=0.6, marker=dict(size=10)))

    fig.update_traces(mode='markers', marker_line_width=1)
    # fig.add_trace(go.Scatter(x=no_hits['enrichment'], y=no_hits['pvals'],
    #     mode='markers', text=no_hits.index.tolist(), opacity=0.4, marker=dict(size=8)))


    fig.update_layout(
        title={'text': bait,
            'x': 0.5,
            'y': 0.95},
            xaxis_type='log',
            yaxis_type='log',
            xaxis_title='Interaction Stoichiometry',
            yaxis_title='Abundance Stoichiometry',
            showlegend=False,
            margin={'l': 30, 'r': 30, 'b': 20, 't': 40})
    fig.update_xaxes(range=[-6.2, 1.2])
    fig.update_yaxes(range=[-5.5, 3.2])
    fig.show()


def hits_stoich_plot(v_df, pvals_df, bait, labels=True, target_re=r'P\d{3}_(.*)'):
    """plot the volcano plot of a given bait"""
    v_df = v_df.copy()
    pvals_df = pvals_df.copy()

    # Specify the bait column
    tpm_vals = v_df[['Gene names', 'tpm_ave']]

    # get only hits
    pvals_df = pvals_df[bait]
    hits = list(set(pvals_df[pvals_df['hits']].index.tolist()))
    minor_hits = list(set(pvals_df[pvals_df
        ['minor_hits']].index.tolist()))

    hits_df = v_df[v_df['Gene names'].isin(hits)]
    hit_vals = hits_df[bait]

    minor_hits_df = v_df[v_df['Gene names'].isin(minor_hits)]
    minor_hit_vals = minor_hits_df[bait]

    # Calculate tpm stoich
    target = re.search(target_re, bait).groups()[0]
    target_row = tpm_vals[tpm_vals['Gene names'] == target]
    if target_row.shape[0] > 0:
        target_tpm = target_row['tpm_ave'].max()
    else:
        raise ValueError(target + " not found in list of preys")

    hit_tpm_vals = tpm_vals[tpm_vals['Gene names'].isin(hits)]
    hit_tpm_vals = hit_tpm_vals['tpm_ave'] / target_tpm

    minor_tpm_vals = tpm_vals[tpm_vals['Gene names'].isin(minor_hits)]
    minor_tpm_vals = minor_tpm_vals['tpm_ave'] / target_tpm


    # Figure Generation
    fig = go.Figure()

    fig.add_trace(go.Scatter(x=hit_vals, y=hit_tpm_vals,
        mode='markers', text=hits_df['Gene names'].tolist(), textposition='bottom right',
        opacity=0.6, marker=dict(size=10, color='LightSkyBlue')))
    fig.add_trace(go.Scatter(x=minor_hit_vals, y=minor_tpm_vals,
        mode='markers', text=minor_hits_df['Gene names'].tolist(), textposition='bottom right',
        opacity=0.6, marker=dict(size=10, color='firebrick')))
    if labels:
        fig.update_traces(mode='markers+text', marker_line_width=1)
    else:
        fig.update_traces(mode='markers', marker_line_width=1)
    fig.add_trace(go.Scatter(x=[0.3], y=[1],
        mode='markers', opacity=0.1, hoverinfo='skip',
        text='Marcos Circle', marker=dict(size=160, color='Green')))


    # fig.add_trace(go.Scatter(x=no_hits['enrichment'], y=no_hits['pvals'],
    #     mode='markers', text=no_hits.index.tolist(), opacity=0.4, marker=dict(size=8)))


    fig.update_layout(
        width=550,
        height=600,
        title={'text': bait,
            'x': 0.5,
            'y': 0.98},
            xaxis_type='log',
            yaxis_type='log',
            xaxis_title='Interaction Stoichiometry',
            yaxis_title='Abundance Stoichiometry',
            showlegend=False,
            margin={'l': 30, 'r': 30, 'b': 20, 't': 40})
    fig.update_xaxes(range=[-5.2, 1.2])
    fig.update_yaxes(range=[-3.2, 3.2])
    fig.show()
