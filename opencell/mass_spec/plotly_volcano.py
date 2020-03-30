import matplotlib.pyplot as plt
import matplotlib
from numbers import Number
import numpy as np
import pandas as pd
import plotly.offline
import plotly.graph_objects as go
import plotly.figure_factory as ff
from plotly.subplots import make_subplots


# this is a random change

def volcano_plot(v_df, bait, fcd1):
    """plot the volcano plot of a given bait"""
    v_df = v_df.copy()

    # Specify the bait column
    bait_vals = v_df[bait]
    hits = bait_vals[bait_vals['hits']]
    print("Number of Significant Hits: " + str(hits.shape[0]))
    no_hits = bait_vals[~bait_vals['hits']]

    xmax = hits['enrichment'].max() + 3
    if hits.shape[0] > 0:
        ymax = hits['pvals'].max() + 4
    else:
        ymax = 30
    # FCD plot calculation
    x1 = np.array(list(np.linspace(-12, -1 * fcd1[1] - 0.001, 200))
        + list(np.linspace(fcd1[1] + 0.001, 12, 200)))
    y1 = fcd1[0] / (abs(x1) - fcd1[1])
    # x2 = np.array(list(np.linspace(-12, -1 * fcd2[1] - 0.001, 200))
    #     + list(np.linspace(fcd2[1] + 0.001, 12, 200)))
    # y2 = fcd2[0] / (abs(x2) - fcd2[1])


    # Figure Generation
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hits['enrichment'], y=hits['pvals'],
        mode='markers+text', text=hits.index.tolist(), textposition='bottom right',
        opacity=0.6, marker=dict(size=10)))
    fig.update_traces(mode='markers+text', marker_line_width=2)
    fig.add_trace(go.Scatter(x=no_hits['enrichment'], y=no_hits['pvals'],
        mode='markers', text=no_hits.index.tolist(), opacity=0.4, marker=dict(size=8)))

    fig.add_trace(go.Scatter(x=x1, y=y1, mode='lines',
        line=dict(color='royalblue', dash='dash')))
    # fig.add_trace(go.Scatter(x=x2, y=y2, mode='lines',
    #     line=dict(color='firebrick', dash='dash')))

    fig.update_layout(
        title={'text': bait,
            'x': 0.5,
            'y': 0.95},
            xaxis_title='Enrichment (log2)',
            yaxis_title='P value (-log10)',
            showlegend=False,
            margin={'l': 30, 'r': 30, 'b': 20, 't': 40})
    fig.update_xaxes(range=[-1 * xmax, xmax])
    fig.update_yaxes(range=[-1, ymax])
    fig.show()


def comparison_volcano(v_df, v2_df, bait, fcd, fcd2):
    """plot volcano plots from two analyses for qualitative comparisons"""

    # initiate dfs
    v_df = v_df.copy()
    v2_df = v2_df.copy()
    v_dfs = [v_df, v2_df]
    fcds = [fcd, fcd2]

    # start a subplot
    fig = make_subplots(rows=1, cols=2)
    for i in [1, 2]:
        bait_vals = v_dfs[i-1][bait]
        hits = bait_vals[bait_vals['hits']]
        print(str(i) + "st Analysis: Number of Significant Hits: "
            + str(hits.shape[0]))
        no_hits = bait_vals[~bait_vals['hits']]

        # calculations for x axis min, max parameters
        xmax = hits['enrichment'].max() + 3
        if hits.shape[0] > 0:
            ymax = hits['pvals'].max() + 4
        else:
            ymax = 30

        # calculation for FCD threshold
        x1 = np.array(list(np.linspace(-12, -1 * fcds[i-1][1] - 0.001, 200))
            + list(np.linspace(fcds[i-1][1] + 0.001, 12, 200)))
        y1 = fcds[i-1][0] / (abs(x1) - fcds[i-1][1])

        # add significant hits
        fig.add_trace(go.Scatter(x=hits['enrichment'], y=hits['pvals'],
            mode='markers+text', text=hits.index.tolist(), textposition='bottom right',
            opacity=0.6, marker=dict(size=10, line=dict(width=2))), row=1, col=i)

        # add non-significant hits
        fig.add_trace(go.Scatter(x=no_hits['enrichment'], y=no_hits['pvals'],
            mode='markers', text=no_hits.index.tolist(), opacity=0.4,
            marker=dict(size=8)), row=1, col=i)

        fig.add_trace(go.Scatter(x=x1, y=y1, mode='lines',
            line=dict(color='royalblue', dash='dash')), row=1, col=i)

        # axis customization
        fig.update_xaxes(title_text='Enrichment (log2)', row=1, col=i,
            range=[-1 * xmax, xmax])
        fig.update_yaxes(title_text='p-value (-log10)', row=1, col=i,
            range=[-1, ymax])

    # layout
    fig.update_layout(
        # width=1000,
        # height=600,
        width=800,
        height=400,
        title={'text': bait,
            'x': 0.5,
            'y': 0.98},
            showlegend=False,
            margin={'l': 30, 'r': 30, 'b': 20, 't': 40})
    fig.show()





def mult_volcano(v_df, baits):
    """plot the volcano plot of a given bait"""
    v_df = v_df.copy()
    fig = go.Figure()
    g_xmax = 0
    g_ymax = 0
    for bait in baits:
        bait_vals = v_df[bait]
        hits = bait_vals[bait_vals['hits']]
        print("Number of Significant Hits: " + str(hits.shape[0]))
        no_hits = bait_vals[~bait_vals['hits']]

        xmax = hits['enrichment'].max() + 3
        if hits.shape[0] > 0:
            ymax = hits['pvals'].max() + 4
        else:
            ymax = 30
        if xmax > g_xmax:
            g_xmax = xmax
        if ymax > g_ymax:
            g_ymax = ymax

        fig.add_trace(go.Scatter(x=hits['enrichment'], y=hits['pvals'],
            mode='markers', text=hits.index.tolist(), textposition='bottom right',
            opacity=0.4, marker=dict(size=10), name=bait))
        fig.update_traces(mode='markers', marker_line_width=2)
        fig.add_trace(go.Scatter(x=no_hits['enrichment'], y=no_hits['pvals'],
            mode='markers', opacity=0.4, marker=dict(size=8)))

    x1 = np.array(list(np.linspace(-8, -1.750001, 100)) + list(np.linspace(1.750001,
        8, 100)))
    y1 = 3.65 / (abs(x1)-1.75)
    x2 = np.array(list(np.linspace(-8, -0.9001, 100)) + list(np.linspace(0.90001,
        8, 100)))
    y2 = 2.9 / (abs(x2)-0.9)


    fig.add_trace(go.Scatter(x=x1, y=y1, mode='lines',
        line=dict(color='royalblue', dash='dash')))
    fig.add_trace(go.Scatter(x=x2, y=y2, mode='lines',
        line=dict(color='firebrick', dash='dash')))

    fig.update_layout(
        title={'text': bait,
            'x': 0.5,
            'y': 0.95},
        xaxis_title='Enrichment (log2)',
        yaxis_title='P value (-log10)',
        showlegend=False,
        margin={'l': 30, 'r': 30, 'b': 20, 't': 40})
    fig.update_xaxes(range=[-1 * g_xmax, g_xmax])
    fig.update_yaxes(range=[-1, g_ymax])
    fig.show()
