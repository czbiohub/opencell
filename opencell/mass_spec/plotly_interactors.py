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


def second_neighbor_umap(
        protein, network, sn_table, n_neighbors=3, min_dist=0.5,
        metric='euclidean', width=800, height=600,
        target_col='target', prey_col='prey', edge_col='pvals'):


    interactors = network[(network[target_col] == protein) | (
        network[prey_col] == protein)]

    all_interactors = set(
        interactors[prey_col].to_list() + interactors[target_col].to_list())



    # second_neighbors = sn_table[
    #     (sn_table['prot_1'] == protein) |
    #     (sn_table['prot_2']== protein)]

    # all_neighbors = set(
    #     second_neighbors['prot_1'].to_list() + second_neighbors['prot_2'].to_list())

    # all_neighbors = all_neighbors.union(all_interactors)

    interactors = network[
        (network[target_col].isin(all_interactors))
        & (network[prey_col].isin(all_interactors))]

    interactors['interaction'] = True


    second_neighbors = sn_table[
        (sn_table['prot_1'].isin(all_interactors))
        & (sn_table['prot_2'].isin(all_interactors))]

    second_neighbors.rename(columns={'prot_1': target_col, 'prot_2': prey_col},
        inplace=True)
    second_neighbors[edge_col] = 11
    second_neighbors['interaction'] = False

    interactors = pd.concat([interactors, second_neighbors])


    # create networkX graph
    graph = nx.convert_matrix.from_pandas_edgelist(
        interactors, target_col, prey_col, edge_attr=edge_col)

    # featurize graph with node2vec
    node2vec = Node2Vec(
        graph, dimensions=64, walk_length=30, num_walks=10, workers=8, quiet=True)

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

    for _, row in interactors.iterrows():
        target = row[target_col]
        prey = row[prey_col]

        target_node = node_vectors[node_vectors['node'] == target]
        target_x = target_node.umap_1.item()
        target_y = target_node.umap_2.item()

        prey_node = node_vectors[node_vectors['node'] == prey]
        prey_x = prey_node.umap_1.item()
        prey_y = prey_node.umap_2.item()

        if row.interaction:
            fig.add_shape(
                type='line',
                x0=target_x,
                y0=target_y,
                x1=prey_x,
                y1=prey_y,
                line=dict(
                    width=0.2))
        else:
            fig.add_shape(
                type='line',
                x0=target_x,
                y0=target_y,
                x1=prey_x,
                y1=prey_y,
                line=dict(
                    color='firebrick',
                    dash='dash',
                    width=0.2))

    # fig.update_traces(marker=dict(size=5.5))
    # fig.update(layout_coloraxis_showscale=False)
    fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
    fig.update_layout(
        width=width,
        height=height,
        margin={'l': 30, 'r': 30, 'b': 20, 't': 20})
    fig.show()
