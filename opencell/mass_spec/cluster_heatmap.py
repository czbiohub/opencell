import matplotlib.pyplot as plt
import matplotlib
from numbers import Number
import numpy as np
import pandas as pd
import plotly.offline
import plotly.graph_objects as go
import seaborn as sns
import plotly.figure_factory as ff
from scipy.cluster.hierarchy import linkage, leaves_list
from sklearn.cluster import KMeans
import time



def dendro_heatmap(matrix_df, hexmap, zmin, zmax, verbose=True):
    """ From the dendro_leaves data, generate a properly oriented
    heatmap

    rtype fig pyplot Fig"""

    if verbose:
        print("Generating Heatmap...")
        start_time = time.time()

    plot_df = matrix_df.copy()
    columns = plot_df.columns.to_flat_index().to_list()
    rows = plot_df.index.to_flat_index().to_list()
    columns = [x[0] + ', ' + str(x[1]) for x in columns]
    rows = [x[0] + ', ' + str(x[1]) for x in rows]

    # Generate the heatmap
    heatmap = [
        go.Heatmap(x=columns, y=rows, z=plot_df.values.tolist(),
        colorscale=hexmap, zmin=zmin, zmax=zmax)]

    if verbose:
        end_time = np.round(time.time() - start_time, 2)
        print("Finished heatmap in " + str(end_time) + " seconds.")

    return heatmap


def cluster_map(matrix_df, clusters, width=800, height=800, method='ward', metric='euclidean',
        off_diagonal=False, save=False, filename='clustermap.pdf'):
    """
    Create a dendrogram from a specific cluster
    """
    matrix_df = matrix_df.copy()

    # get all off diagonal targets if true
    if off_diagonal:
        row_df = matrix_df.loc[matrix_df.index.isin(clusters, level='cluster')]
        cols = (row_df.sum() > 0).index.tolist()

        col_df = matrix_df.loc[:, matrix_df.columns.isin(clusters, level='cluster')]
        rows = col_df[col_df.sum(axis=1) > 0].index.tolist()

        cluster_df = matrix_df.T[rows].T[cols]

    else:
        cluster_df = matrix_df.loc[
            matrix_df.index.isin(clusters, level='cluster'),
            matrix_df.columns.isin(clusters, level='cluster'),
        ]
    cluster_df.columns = cluster_df.columns.droplevel(level='cluster')
    cluster_df.index = cluster_df.index.droplevel(level='cluster')

    # drop all zero cols or rows
    cluster_df = cluster_df[(cluster_df.T != 0).any()]
    cluster_df = cluster_df.loc[:, (cluster_df != 0).any(axis=0)]
    wow = cluster_df

    # Initialize figure by creating upper dendrogram
    col_labels = list(wow)
    row_labels = wow.index.to_list()

    fig = ff.create_dendrogram(wow.T, orientation='bottom', linkagefun=lambda x:
        linkage(wow.T, method=method, metric=metric))
    for i in range(len(fig['data'])):
        fig['data'][i]['yaxis'] = 'y2'
    dendro_tops = fig['layout']['xaxis']['ticktext']
    dendro_tops = list(map(int, dendro_tops))

    # Create Side Dendrogram
    dendro_side = ff.create_dendrogram(wow, orientation='right', linkagefun=lambda x:
        linkage(wow, method=method, metric=metric))
    for i in range(len(dendro_side['data'])):
        dendro_side['data'][i]['xaxis'] = 'x2'

    # Add Side Dendrogram Data to Figure
    for data in dendro_side['data']:
        fig.add_trace(data)

    dendro_sides = dendro_side['layout']['yaxis']['ticktext']
    dendro_sides = list(map(int, dendro_sides))

    ordered_cols = [col_labels[x] for x in dendro_tops]
    bwow = wow[ordered_cols]

    ordered_rows = [row_labels[x] for x in dendro_sides]
    bwow = bwow.loc[ordered_rows]

    heat_data = bwow.values

    hovertext = list()
    for yi, yy in enumerate(ordered_rows):
        hovertext.append(list())
        for xi, xx in enumerate(ordered_cols):
            hovertext[-1].append(
                xx + ', ' + yy + ', ' + str(round(heat_data[yi][xi], 2)))

    heatmap = [
        go.Heatmap(
            x=ordered_cols,
            y=ordered_rows,
            z=heat_data,
            hoverinfo='text',
            text=hovertext,
            colorscale='Blues',
            showscale=False
        )
    ]

    heatmap[0]['x'] = fig['layout']['xaxis']['tickvals']
    heatmap[0]['y'] = dendro_side['layout']['yaxis']['tickvals']


    fig.add_traces(heatmap)

    # Edit Layout
    fig.update_layout({'width': width, 'height': height,
        'showlegend': False, 'hovermode': 'closest',
        'yaxis': {'mirror': 'allticks', 'side': 'right'}})

    # Edit xaxis
    fig.update_layout(xaxis={'domain': [.15, 1],
        'mirror': False,
        'showgrid': False,
        'showline': False,
        'zeroline': False,
        'showticklabels': True,
        'ticktext': ordered_cols,
        'ticks': ""})
    # Edit xaxis2
    fig.update_layout(xaxis2={'domain': [0, .15],
        'mirror': False,
        'showgrid': False,
        'showline': False,
        'zeroline': False,
        'showticklabels': False,
        'ticks': ""})

    # Edit yaxis
    fig.update_layout(yaxis={'domain': [0, .85],
        'mirror': True,
        'showgrid': False,
        'showline': False,
        'zeroline': False,
        'tickvals': dendro_side['layout']['yaxis']['tickvals'],
        'showticklabels': True,
        'ticktext': ordered_rows,
        'ticks': ""})

    # Edit yaxis2
    fig.update_layout(yaxis2={'domain': [.825, .925],
        'mirror': False,
        'showgrid': False,
        'showline': False,
        'zeroline': False,
        'showticklabels': False,
        'ticks': ""})
    fig.show()
    if save:
        fig.write_image(filename)


def df_min_max(df):
    """Quickly output min and max values of the df"""

    # flatten the df to a list of all values
    all_vals = df.values.flatten().tolist()
    all_vals = list(filter(lambda x: isinstance(x, Number), all_vals))

    return min(all_vals), max(all_vals)


def color_map(df, zmin, zmax):
    """generate a color map, zmin, and zmax that the heatmap function will use
    Will add customization features in the future"""

    dfmin, dfmax = df_min_max(df)
    if zmin is None:
        zmin = dfmin
    if zmax is None:
        zmax = dfmax

    # Use built in seaborn function to blend palette
    cmap = sns.blend_palette(('black', 'blue', 'green', 'yellow',
        'orange', 'red'), n_colors=8, as_cmap=False)
    hexmap = []
    # change to hex values that Plotly can read
    for color in cmap:
        hexmap.append(matplotlib.colors.rgb2hex(color))

    # a range list from zmin to zmax
    a = list(range(int(zmin), int(zmax)))
    y = [0]*len(a)
    # plot colorscale
    fig = go.Figure(go.Heatmap(x=a, y=y, z=a, zmin=zmin, zmax=zmax,
        colorscale=hexmap, showscale=False),
        layout=go.Layout({'width': 1000, 'height': 200}, yaxis={'showticklabels': False}))

    return fig, zmin, zmax, hexmap


def print_clusterone_cluster(cluster_one, gene_name):
    """print cluster numbers of a gene"""

    cluster_one = cluster_one.copy()
    cluster_one['Members'] = cluster_one['Members'].apply(
        lambda x: x.split(' '))
    selected = cluster_one[cluster_one['Members'].apply(lambda x: gene_name in x)]
    if selected.shape[0] == 0:
        print("Gene not found in clusters list.")
    else:
        print(selected['Cluster'].to_list())


def generate_clusterone_matrix(stoichs, cluster_one, clusters, metric):
    """ generate cluster dendrogram from listed clusters """

    stoichs = stoichs.copy()
    cluster_one = cluster_one.copy()

    # retrieve specified clusters
    cluster_one = cluster_one[cluster_one['Cluster'].isin(clusters)]

    cluster_one['Members'] = cluster_one['Members'].apply(
        lambda x: x.split(' '))


    # get all the interacting genes
    genes = []
    for _, row in cluster_one.iterrows():
        genes += row.Members
    genes = list(set(genes))

    selected_stoichs = stoichs[
        stoichs['target'].isin(genes) & stoichs['prey'].isin(genes)
    ]
    matrix = convert_to_sparse_matrix(selected_stoichs, metric=metric)

    return matrix


def convert_to_sparse_matrix(double_df, metric='distance'):
    """
    Convert double column pval/stoich dataframe to sparse pairwise matrix
    """
    double_df = double_df.copy()

    # get a unique list of targets and preys
    targets = double_df['target'].unique().tolist()
    preys = double_df['prey'].unique().tolist()

    # set up a new matrix df, unique preys will be the indicies
    matrix = pd.DataFrame()
    matrix['prey'] = preys
    matrix.set_index('prey', drop=True, inplace=True)

    # iterate through each target and create a sparse matrix
    # with PD update/merge
    for target in targets:
        matrix[target] = [0] * matrix.shape[0]
        sample = double_df[double_df['target'] == target][['prey', metric]]
        sample.set_index('prey', drop=True, inplace=True)
        sample.rename(columns={metric: target}, inplace=True)
        matrix.update(sample, join='left')

    return matrix


def clusterone_map(matrix_df, width=800, height=800, method='ward', metric='euclidean',
         save=False, filename='clustermap.pdf'):
    """
    Create a dendrogram from a specific cluster
    """
    cluster_df = matrix_df.copy()

    # drop all zero cols or rows
    cluster_df = cluster_df[(cluster_df.T != 0).any()]
    cluster_df = cluster_df.loc[:, (cluster_df != 0).any(axis=0)]
    wow = cluster_df

    # Initialize figure by creating upper dendrogram
    col_labels = list(wow)
    row_labels = wow.index.to_list()

    if wow.T.shape[0] == 1:
        print("Error: 1D Matrix")
        return


    fig = ff.create_dendrogram(wow.T, orientation='bottom', linkagefun=lambda x:
        linkage(wow.T, method=method, metric=metric))
    for i in range(len(fig['data'])):
        fig['data'][i]['yaxis'] = 'y2'
    dendro_tops = fig['layout']['xaxis']['ticktext']
    dendro_tops = list(map(int, dendro_tops))

    # Create Side Dendrogram
    dendro_side = ff.create_dendrogram(wow, orientation='right', linkagefun=lambda x:
        linkage(wow, method=method, metric=metric))
    for i in range(len(dendro_side['data'])):
        dendro_side['data'][i]['xaxis'] = 'x2'

    # Add Side Dendrogram Data to Figure
    for data in dendro_side['data']:
        fig.add_trace(data)

    dendro_sides = dendro_side['layout']['yaxis']['ticktext']
    dendro_sides = list(map(int, dendro_sides))

    ordered_cols = [col_labels[x] for x in dendro_tops]
    bwow = wow[ordered_cols]

    ordered_rows = [row_labels[x] for x in dendro_sides]
    bwow = bwow.loc[ordered_rows]

    heat_data = bwow.values

    hovertext = list()
    for yi, yy in enumerate(ordered_rows):
        hovertext.append(list())
        for xi, xx in enumerate(ordered_cols):
            hovertext[-1].append(
                xx + ', ' + yy + ', ' + str(round(heat_data[yi][xi], 2)))

    heatmap = [
        go.Heatmap(
            x=ordered_cols,
            y=ordered_rows,
            z=heat_data,
            hoverinfo='text',
            text=hovertext,
            colorscale='Blues',
            showscale=False
        )
    ]

    heatmap[0]['x'] = fig['layout']['xaxis']['tickvals']
    heatmap[0]['y'] = dendro_side['layout']['yaxis']['tickvals']


    fig.add_traces(heatmap)

    # Edit Layout
    fig.update_layout({'width': width, 'height': height,
        'showlegend': False, 'hovermode': 'closest',
        'yaxis': {'mirror': 'allticks', 'side': 'right'}})

    # Edit xaxis
    fig.update_layout(xaxis={'domain': [.15, 1],
        'mirror': False,
        'showgrid': False,
        'showline': False,
        'zeroline': False,
        'showticklabels': True,
        'ticktext': ordered_cols,
        'ticks': ""})
    # Edit xaxis2
    fig.update_layout(xaxis2={'domain': [0, .15],
        'mirror': False,
        'showgrid': False,
        'showline': False,
        'zeroline': False,
        'showticklabels': False,
        'ticks': ""})

    # Edit yaxis
    fig.update_layout(yaxis={'domain': [0, .85],
        'mirror': True,
        'showgrid': False,
        'showline': False,
        'zeroline': False,
        'tickvals': dendro_side['layout']['yaxis']['tickvals'],
        'showticklabels': True,
        'ticktext': ordered_rows,
        'ticks': ""})

    # Edit yaxis2
    fig.update_layout(yaxis2={'domain': [.825, .925],
        'mirror': False,
        'showgrid': False,
        'showline': False,
        'zeroline': False,
        'showticklabels': False,
        'ticks': ""})
    fig.show()
    if save:
        fig.write_image(filename)
