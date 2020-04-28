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


def subtract_prey_median(matrix_df, mad_mod=True, mad_factor=1):
    """As an option to visualize clustering so that each intensity
    is subtracted by the prey group median, this function
    alters the base dataframe with the transformation"""

    transformed = matrix_df.copy()

    # Get a list of the columns (baits or preys)
    cols = list(transformed)

    # go through each prey (now in columns) and subtract median
    for col in cols:
        transformed[col] = transformed[col] - transformed[col].median()
        if mad_mod:
            mad = transformed[col].mad() * mad_factor
            transformed[col] = transformed[col].apply(lambda x: x if x > mad else 0)

    transformed = transformed.T
    # if mad_mod:
    #     t_cols = list(transformed)
    #     for col in t_cols:
    #         mad = transformed[col].mad() * mad_factor
    #         transformed[col] = transformed[col].apply(lambda x: x if x > mad else 0)

    # transpose back to original shape and add the info columns again
    info_cols = list([col for col in list(matrix_df) if col[0] == 'Info'])
    for col in info_cols:
        transformed[col] = matrix_df[col]

    return transformed


def prey_kmeans(matrix_df, k=20, method='single', ordering=True, verbose=True):
    """Create a large k clustered groups, and sort them by average group intensity.
    Return a list of Protein IDs after the sort

    rtype: dendro_side plotly figurefactory
    rtype: dendro_leaves list"""

    if verbose:
        print("Generating prey hierarchies and dendrogram...")
        start_time = time.time()

    matrix_df = matrix_df.copy()

    # Conduct K means clustering
    kmeans_model = KMeans(n_clusters=k).fit(matrix_df)
    kmeans_clusters = kmeans_model.predict(matrix_df)

    matrix_df['cluster'] = kmeans_clusters

    # Sort clusters by cluster average intensity
    grouped_df = matrix_df.groupby(['cluster'])
    cluster_intensities = grouped_df.mean()

    # Create a hierarchy of the clusters
    cluster_linkage = linkage(cluster_intensities, method=method,
        optimal_ordering=ordering)

    # List of clusters to be plotted sequentially
    cluster_leaves = leaves_list(cluster_linkage)

    # list of preys to be populated from cluster sequence
    leaves = []

    # sort thrugh clusters and populate with hierarchy of individual leaves
    for cluster in cluster_leaves:
        cluster_df = matrix_df[matrix_df['cluster'] == cluster]
        cluster_df.drop(columns=['cluster'], inplace=True)

        if cluster_df.shape[0] > 1:
            # Use plotly function to generate a linkage
            prey_linkage = linkage(cluster_df, method=method, optimal_ordering=ordering)

            # Retrieve the order of preys in the new linkage
            prey_leaves = leaves_list(prey_linkage)
            prey_leaves = [list(cluster_df.index)[x] for x in prey_leaves]

        else:
            prey_leaves = list(cluster_df.index)

        # add to the master list of leaves
        leaves = leaves + prey_leaves

    if verbose:
        end_time = np.round(time.time() - start_time, 2)
        print("Finished generating linkage in " + str(end_time) + " seconds.")

    return leaves


def bait_leaves(matrix_df, method='average', distance='euclidean', hit_bool=False,
        verbose=True):
    """Calculate the prey linkage and return the list of
    prey plotting sequence to use for heatmap. Use prey_kmeans for better performance
    rtype: prey_leaves list"""

    if verbose:
        print("Generating bait linkage...")
        start_time = time.time()
    # Create a matrix_df, taking median of all replicates
    matrix_df = matrix_df.copy()

    if hit_bool:
        matrix_df = matrix_df.applymap(hit_bool_cat)

    # Transpose to get linkages of baits
    matrix_df = matrix_df.T

    bait_linkage = linkage(matrix_df, method=method, optimal_ordering=True)

    # Retreieve the order of baits in the new linkage
    bait_leaves = leaves_list(bait_linkage)
    bait_leaves = [list(matrix_df.index)[x] for x in bait_leaves]

    if verbose:
        end_time = np.round(time.time() - start_time, 2)
        print("Finished generating linkage in " + str(end_time) + " seconds.")

    return bait_leaves


def prey_leaves(matrix_df, method='average', distance='euclidean', hit_bool=False,
        verbose=True):
    """Calculate the prey linkage and return the list of
    prey plotting sequence to use for heatmap. Use prey_kmeans for better performance.

    rtype: prey_leaves list"""
    if verbose:
        print("Generating prey linkage...")
        start_time = time.time()

    matrix_df = matrix_df.copy()
    if hit_bool:
        matrix_df = matrix_df.applymap(hit_bool_cat)

    prey_linkage = linkage(matrix_df, method=method)

    # Retrieve the order of preys in the new linkage
    prey_leaves = leaves_list(prey_linkage)
    prey_leaves = [list(matrix_df.index)[x] for x in prey_leaves]


    if verbose:
        end_time = np.round(time.time() - start_time, 2)
        print("Finished generating linkage in " + str(end_time) + " seconds.")

    return prey_leaves


def hit_bool_cat(distance):
    if distance == 0:
        return distance
    # elif distance < 12:
    #     return 0.5
    # # elif distance < 20:
    # #     return 1
    else:
        return 1


def dendro_heatmap(matrix_df, prey_leaves, hexmap, zmin, zmax, bait_leaves=None,
        bait_clust=False, verbose=True):
    """ From the dendro_leaves data, generate a properly oriented
    heatmap

    rtype fig pyplot Fig"""

    if verbose:
        print("Generating Heatmap...")
        start_time = time.time()

    plot_df = matrix_df.copy()

    # Correctly order the plot df according to dendro leaves
    plot_df = plot_df.T[prey_leaves].T


    # Reorder columns based on bait_leaves
    if bait_clust:
        plot_df = plot_df[bait_leaves]


    # Generate the heatmap
    heatmap = [
        go.Heatmap(x=list(plot_df), y=list(plot_df.index), z=plot_df.values.tolist(),
        colorscale=hexmap, zmin=zmin, zmax=zmax)]



    if verbose:
        end_time = np.round(time.time() - start_time, 2)
        print("Finished heatmap in " + str(end_time) + " seconds.")

    return heatmap


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
