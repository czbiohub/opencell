import matplotlib.pyplot as plt
import matplotlib
from numbers import Number
import numpy as np
import pandas as pd
import plotly.offline
import plotly.graph_objects as go
import plotly.figure_factory as ff
from plotly.subplots import make_subplots
import plotly.express as px
import umap
from sklearn.cluster import KMeans
from node2vec import Node2Vec
import networkx as nx


def spatial_kmeans_cluster(spatial_df, n_clusters=8):
    spatial_df = spatial_df.copy()

    fractions = ['Nuc', '03K', '05K', '12K', '24K', '80K', 'Cyt']

    sdata = spatial_df[fractions].values
    cluster_labels = KMeans(n_clusters=n_clusters).fit_predict(sdata)
    col_label = 'cluster_' + str(n_clusters)

    spatial_df[col_label] = cluster_labels

    return spatial_df


def spatial_umap(spatial_df, label='Nuc', opacity=0.5, width=800, height=600,
        show_ticks=False, misc_hover=False):
    """
    Ways of showing interactive HEK spatial maps
    """
    spatial_df = spatial_df.copy()
    fractions = ['Nuc', '03K', '05K', '12K', '24K', '80K', 'Cyt']
    for fraction in fractions:
        spatial_df[fraction] = spatial_df[fraction].apply(np.round, args=[3])

    if type(label) == list:
        labelling = spatial_df['Gene names'].isin(label)
        labelled = spatial_df[labelling]
        unlabelled = spatial_df[~labelling]

        fig = px.scatter(
            labelled,
            x='umap_1',
            y='umap_2',
            hover_name='Gene names',
            hover_data=['Nuc', '03K', '05K', '12K', '24K', '80K', 'Cyt'],
            opacity=opacity)
        if misc_hover:
            hover = 'text'
        else:
            hover = 'skip'

        fig.add_scatter(
            x=unlabelled['umap_1'],
            y=unlabelled['umap_2'],
            mode='markers',
            showlegend=False,
            hoverinfo='skip',
            opacity=0.2,
            text=unlabelled['Gene names'],
            marker=dict(color='grey'))

    elif 'mcl' in label:
        spatial_df.sort_values(by=label, inplace=True)
        labelling = spatial_df[label].apply(np.isfinite)
        labelled = spatial_df[labelling]
        unlabelled = spatial_df[~labelling]

        fig = px.scatter(
            labelled,
            x='umap_1',
            y='umap_2',
            color=label,
            color_continuous_scale=px.colors.cyclical.mygbm[:-1],
            hover_name='Gene names',
            hover_data=['Nuc', '03K', '05K', '12K', '24K', '80K', 'Cyt'],
            opacity=opacity)
        fig.update(layout_coloraxis_showscale=False)
        if misc_hover:
            hover = 'text'
        else:
            hover = 'skip'

        fig.add_scatter(
            x=unlabelled['umap_1'],
            y=unlabelled['umap_2'],
            mode='markers',
            showlegend=False,
            hoverinfo='skip',
            opacity=0.2,
            text=unlabelled['Gene names'],
            marker=dict(color='grey'))


    elif 'cluster' in label:
        spatial_df[label] = spatial_df[label].apply(str)
        spatial_df.sort_values(by=label, inplace=True)
        fig = px.scatter(
            spatial_df,
            x='umap_1',
            y='umap_2',
            color=label,
            color_discrete_sequence=px.colors.qualitative.T10,
            hover_name='Gene names',
            hover_data=['Nuc', '03K', '05K', '12K', '24K', '80K', 'Cyt'],
            opacity=opacity)

    elif label in ['Nuc', 'Cyt', 'Org']:
        fig = px.scatter(
            spatial_df,
            x='umap_1',
            y='umap_2',
            color=label,
            color_continuous_scale='Geyser',
            hover_name='Gene names',
            hover_data=['Nuc', '03K', '05K', '12K', '24K', '80K', 'Cyt'],
            opacity=opacity)
    elif label == 'reference':
        # mode for showing reference genes
        # divide the into labeled and unlabelled
        labelling = spatial_df[label].apply(lambda x: True if
            type(x) == str else False)
        labelled = spatial_df[labelling]

        unlabelled = spatial_df[~labelling]
        labelled.sort_values(by=label, inplace=True)
        unlabelled[label] = unlabelled[label].apply(
            lambda x: 'Unlabelled')
        fig = px.scatter(
            labelled,
            x='umap_1',
            y='umap_2',
            hover_name='Gene names',
            hover_data=['Nuc', '03K', '05K', '12K', '24K', '80K', 'Cyt'],
            color=label,
            color_discrete_sequence=px.colors.qualitative.Light24,
            # color_discrete_sequence=px.colors.cyclical.mrybm,
            opacity=opacity)
        fig.update_traces(marker=dict(size=6))
        if misc_hover:
            hover = 'text'
        else:
            hover = 'skip'

        fig.add_scatter(
            x=unlabelled['umap_1'],
            y=unlabelled['umap_2'],
            mode='markers',
            showlegend=False,
            hoverinfo='skip',
            opacity=0.2,
            text=unlabelled['Gene names'],
            marker=dict(color='grey'))
    elif label.split('_')[0].lower() in ['atlas', 'oc', 'mutual']:
        # mode for showing reference genes
        # divide the into labeled and unlabelled
        atlas_col = label.split('_')[0].lower() + '_loc'
        compartment = label.split('_')[1].lower()
        labelling = spatial_df[atlas_col].apply(lambda x: x if
            type(x) == str else '')

        if compartment == 'org':
            labelling = labelling.apply(simple_org)
        else:
            labelling = labelling.apply(lambda x: True if compartment in x.lower()
                else False)

        labelled = spatial_df[labelling]


        unlabelled = spatial_df[~labelling]
        labelled = labelled.iloc[
            labelled.groupby(atlas_col).atlas_loc.transform('size').argsort(kind='mergesort')]
        labelled = labelled.iloc[::-1]
        # labelled.sort_values(by=atlas_col, inplace=True)
        unlabelled[label] = unlabelled[atlas_col].apply(
            lambda x: 'Unlabelled')

        fig = px.scatter(
            labelled,
            x='umap_1',
            y='umap_2',
            hover_name='Gene names',
            color=atlas_col,
            color_discrete_sequence=px.colors.qualitative.Vivid,
            hover_data=['Nuc', '03K', '05K', '12K', '24K', '80K', 'Cyt'],
            opacity=opacity)
        fig.update_traces(marker=dict(size=5.5))
        if misc_hover:
            hover = 'text'
        else:
            hover = 'skip'

        fig.add_scatter(
            x=unlabelled['umap_1'],
            y=unlabelled['umap_2'],
            mode='markers',
            showlegend=False,
            hoverinfo='skip',
            opacity=0.2,
            text=unlabelled['Gene names'],
            marker=dict(color='grey'))
    elif 'search' in label:
        search = label.split('_')[1].lower()
        labelling = spatial_df['Gene names'].map(lambda x: search in x.lower())
        labelled = spatial_df[labelling]
        unlabelled = spatial_df[~labelling]
        fig = px.scatter(
            labelled,
            x='umap_1',
            y='umap_2',
            hover_name='Gene names',
            hover_data=['Nuc', '03K', '05K', '12K', '24K', '80K', 'Cyt'],
            opacity=opacity)
        fig.update_traces(marker=dict(size=5.5, color='#008fd5'))
        if misc_hover:
            hover = 'text'
        else:
            hover = 'skip'

        fig.add_scatter(
            x=unlabelled['umap_1'],
            y=unlabelled['umap_2'],
            mode='markers',
            showlegend=False,
            hoverinfo=hover,
            opacity=0.2,
            text=unlabelled['Gene names'],
            marker=dict(color='grey'))


    else:
        print("Label not recognized, please double check!")
        return


    fig.update_xaxes(showticklabels=show_ticks, title_text='')
    fig.update_yaxes(showticklabels=show_ticks, title_text='')
    fig.update_layout(
        width=width,
        height=height,
        title={'text': "HEK Spatial Proteomics",
        'x': 0.5},
        margin={'l': 30, 'r': 30, 'b': 20})
    fig.show()


def simple_org(x):
    if 'nuc' in x.lower():
        return False
    elif 'cyt' in x.lower():
        return False
    elif len(x) == 0:
        return False
    else:
        return True


def interaction_umap(
        matrix, n_neighbors=3, min_dist=0.5, metric='euclidean', opacity=0.5,
        width=800, height=600, cluster='mcl_cluster', node_name='prey', highlight=None):

    matrix = matrix.copy()
    cluster_cols = [x for x in list(matrix) if 'cluster' in str(x)]
    cluster_cols.append(node_name)
    umatrix = matrix.drop(columns=cluster_cols)
    data = umatrix.values

    fit = umap.UMAP(
        n_neighbors=n_neighbors,
        min_dist=min_dist,
        metric=metric
    )

    u = fit.fit_transform(data)
    matrix['umap_1'] = u[: , 0]
    matrix['umap_2'] = u[: , 1]
    matrix.reset_index(inplace=True, drop=False)
    fig = px.scatter(
        matrix,
        x='umap_1',
        y='umap_2',
        hover_name=node_name,
        color=cluster,
        color_continuous_scale=px.colors.cyclical.mygbm[: -1],
        opacity=opacity)
    fig.update_traces(marker=dict(size=5.5))
    fig.update(layout_coloraxis_showscale=False)
    if highlight:
        labelled = matrix[matrix[node_name].isin(highlight)]
        fig.add_scatter(
            x=labelled['umap_1'],
            y=labelled['umap_2'],
            mode='markers',
            showlegend=False,
            hoverinfo='text',
            opacity=1,
            text=labelled[node_name],
            marker=dict(color='#fc4f30', size=14))

    fig.update_layout(
        width=width,
        height=height,
        margin={'l': 30, 'r': 30, 'b': 20})
    fig.show()


def cluster_umap(
        cluster_df, n_neighbors=3, min_dist=0.5, metric='euclidean',
        width=800, height=600, target_col='target', prey_col='prey', edge_col='pvals'):

    cluster_df = cluster_df.copy()
    # create networkX graph
    graph = nx.convert_matrix.from_pandas_edgelist(
        cluster_df, target_col, prey_col, edge_attr=edge_col)

    # featurize graph with node2vec
    node2vec = Node2Vec(
        graph, dimensions=64, walk_length=30, num_walks=200, workers=8, quiet=True)

    # transformation of graph to word2vec format
    model = node2vec.fit(window=10, min_count=1, batch_words=4)

    # convert to pandas (some word2vec terminologies in the code)
    ordered_nodes = [(term, voc.index, voc.count) for term, voc in model.wv.vocab.items()]
    ordered_nodes = sorted(ordered_nodes, key=lambda k: k[2])
    ordered_terms, term_indices, term_counts = zip(*ordered_nodes)
    # featurized df
    node_vectors = pd.DataFrame(model.wv.syn0[term_indices, :], index=ordered_terms)

    data = node_vectors.values

    fit = umap.UMAP(
        n_neighbors=n_neighbors,
        min_dist=min_dist,
        metric=metric,
        random_state=10
    )

    u = fit.fit_transform(data)
    node_vectors['umap_1'] = u[:, 0]
    node_vectors['umap_2'] = u[:, 1]
    node_vectors.reset_index(inplace=True, drop=False)
    node_vectors.rename(columns={'index': 'node'}, inplace=True)
    fig = px.scatter(
        node_vectors,
        x='umap_1',
        y='umap_2',
        text='node',
        hover_name='node',
        opacity=1)
    fig.update_traces(textposition='top center', marker=dict(size=10))

    for _, row in cluster_df.iterrows():
        target = row[target_col]
        prey = row[prey_col]

        target_node = node_vectors[node_vectors['node'] == target]
        target_x = target_node.umap_1.item()
        target_y = target_node.umap_2.item()

        prey_node = node_vectors[node_vectors['node'] == prey]
        prey_x = prey_node.umap_1.item()
        prey_y = prey_node.umap_2.item()

        fig.add_shape(
            type='line',
            x0=target_x,
            y0=target_y,
            x1=prey_x,
            y1=prey_y,
            line=dict(
                width=0.2))

    # fig.update_traces(marker=dict(size=5.5))
    # fig.update(layout_coloraxis_showscale=False)
    fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
    fig.update_layout(
        width=width,
        height=height,
        margin={'l': 30, 'r': 30, 'b': 20, 't': 20})
    fig.show()
