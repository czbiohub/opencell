import pandas as pd
from opencell.api import payloads


def protein_group_to_node(protein_group, kind):
    node = payloads.generate_protein_group_payload(protein_group)
    node['id'] = protein_group.id
    node['type'] = kind
    node.pop('is_bait')
    return node


def construct_network(target_pulldown=None, interacting_pulldowns=None, uniprot_metadata=None):
    '''
    Construct the nodes and edges for the cytoscape network of interactions
    for a given opencell target or interactor

    For an opencell target, its pulldown must be provided as `target_pulldown`
    (its interacting pulldowns are determined from this pulldown).

    For an opencell interactor, the list of `interacting_pulldowns`
    in which the interactor appears as a hit must be provided,
    as well as a single uniprot_metadata entry to 'represent' the interactor.

    For both targets and interactors, the networks consist of:
    1) the direct interactors; these include both the 'interacting pulldowns'
     and, if target_pulldown is provided, all of the significant hits in the target pulldown
    2) the direct interactions between the direct interactors
       (these exist when one direct interactor appears in the pulldown of another)
    '''

    nodes = []
    bait_hit = None
    direct_hits = []

    if target_pulldown:
        direct_hits = target_pulldown.get_significant_hits()
        bait_hit = target_pulldown.get_bait_hit(only_one=True)
        interacting_pulldowns = target_pulldown.get_interacting_pulldowns()

    # create a node to represent the target if the bait hit exists
    if bait_hit:
        bait_node = protein_group_to_node(bait_hit.protein_group, kind='bait')
        bait_node['pulldown'] = target_pulldown
    else:
        # if a pulldown was provided but the target (the bait hit) does not appear in it,
        # we have to manually construct the bait node (rather than using protein_group_to_node)
        if target_pulldown:
            bait_node = {
                'type': 'bait',
                'id': 'bait-placeholder',
                'uniprot_gene_names': [target_pulldown.cell_line.crispr_design.target_name],
                'opencell_target_names': [target_pulldown.cell_line.crispr_design.target_name],
            }
        # if no pulldown was provided at all,
        # manually construct the bait node using the provided uniprot_metadata
        else:
            bait_node = {
                'type': 'bait',
                'id': 'bait-placeholder',
                'uniprot_gene_names': [uniprot_metadata.get_primary_gene_name()],
                'opencell_target_names': [],
            }

    nodes.append(bait_node)

    # create nodes to represent the hits in the target's pulldown
    for direct_hit in direct_hits:
        if bait_hit and bait_hit.protein_group.id == direct_hit.protein_group.id:
            continue
        node = protein_group_to_node(direct_hit.protein_group, kind='hit')
        node['hit'] = direct_hit
        nodes.append(node)

    # the bait hits from each of the interacting pulldowns
    interacting_bait_hits = [
        interacting_pulldown.get_bait_hit(only_one=True)
        for interacting_pulldown in interacting_pulldowns
    ]

    # create nodes to represent the interacting pulldowns
    for interacting_pulldown, bait_hit in zip(interacting_pulldowns, interacting_bait_hits):

        # if the bait was not found in the interacting pulldown,
        # we cannot create a node to represent the pulldown
        if not bait_hit:
            continue

        node = protein_group_to_node(bait_hit.protein_group, kind='pulldown')
        node['pulldown'] = interacting_pulldown
        nodes.append(node)

    # if no target pulldown was provided, the 'direct hits', for the purpose of constructing edges,
    #  are the bait hits from the interacting pulldowns
    if not target_pulldown:
        direct_hits = interacting_bait_hits

    # generate the edges between direct nodes
    edges = []
    all_node_ids = [node['id'] for node in nodes]

    for node in nodes:
        indirect_hits = None

        if node['type'] == 'bait':
            indirect_hits = direct_hits

        # if the node represents a pulldown, we already have the list of indirect hits
        if node['type'] == 'pulldown':
            indirect_hits = node['pulldown'].get_significant_hits(eagerload=False)

        # if the node represents a direct hit in the target's pulldown,
        # we need to determine whether the hit corresponds to an opencell target
        # (and therefore to a pulldown with its own hits)
        if node['type'] == 'hit':
            designs = node['hit'].protein_group.crispr_designs

            # if the hit does not correspond to any opencell targets,
            # or if the hit corresponds to multiple distinct opencell targets,
            # we do not need to generate edges between the hit and the other hits
            num_distinct_designs = len(set([d.uniprot_id for d in designs]))
            if not designs or num_distinct_designs > 1:
                continue

            # if the hit does correspond to an opencell target,
            # find the best cell line corresponding to the hit's protein group
            # note that this is complicated because there may be more than one crispr design
            # for a protein group, and because there may be more than one cell line per design
            # (e.g., for resorted targets)
            node_pulldown = None
            for design in designs:
                cell_line = design.get_best_cell_line()
                if cell_line:
                    node_pulldown = cell_line.get_best_pulldown()
                    if node_pulldown:
                        indirect_hits = node_pulldown.get_significant_hits(eagerload=False)
                        break

        if not indirect_hits:
            continue

        for indirect_hit in indirect_hits:
            indirect_node_id = indirect_hit.protein_group.id

            # if the hit of the node is not among the nodes, we don't need to create an edge
            if indirect_node_id not in all_node_ids or indirect_node_id == node['id']:
                continue

            # create the edge between the two direct interactors
            edges.append({
                'id': '%s-%s' % (node['id'], indirect_node_id),
                'source': node['id'],
                'target': indirect_node_id,
            })

    # drop the pulldown and hit instances from the node dicts
    for node in nodes:
        node.pop('hit', None)
        node.pop('pulldown', None)

    return nodes, edges


def construct_compound_nodes(nodes, clustering_analysis_type, subcluster_type, engine):
    '''
    '''
    clusters = pd.read_sql(
        f'''
        select protein_group_id, cluster_id, subcluster_id, core_complex_id
        from mass_spec_cluster_heatmap heatmap
        inner join mass_spec_hit hit on hit.id = heatmap.hit_id
        where analysis_type = '{clustering_analysis_type}'
        ''',
        engine
    )

    # cluster memberships are the same for all hits with the same protein group (by design)
    clusters = clusters.groupby(['protein_group_id']).first().reset_index()

    # all clusters in which more than one node appears
    clusters = clusters.loc[clusters.protein_group_id.isin([node['id'] for node in nodes])]
    cluster_sizes = clusters.groupby('cluster_id').count().reset_index()
    clusters = clusters.loc[
        clusters.cluster_id.isin(
            cluster_sizes.loc[cluster_sizes.protein_group_id > 1].cluster_id.values
        )
    ]

    # the type of subclustering that will be represented by the compound nodes
    subcluster_id_name = 'core_complex_id'
    if subcluster_type == 'subclusters':
        subcluster_id_name = 'subcluster_id'

    # append cluster, subcluster, and parent node ids to the nodes
    for node in nodes:
        row = clusters.loc[clusters.protein_group_id == node['id']]
        if len(row):
            row = row.iloc[0]
            node['cluster_id'] = int(row.cluster_id) if not pd.isna(row.cluster_id) else None
            node['subcluster_id'] = (
                int(row[subcluster_id_name]) if not pd.isna(row[subcluster_id_name]) else None
            )

        # if the node is in a subcluster, its parent should be the subcluster compound node
        if node.get('subcluster_id'):
            node['parent'] = '%s-%s' % (node.get('cluster_id'), node.get('subcluster_id'))

        # if the node is in a cluster but not a subcluster,
        # its parent should be the cluster compound node itself
        elif node.get('cluster_id'):
            node['parent'] = '%s' % node.get('cluster_id')

    # create the parent nodes for clusters
    cluster_ids = [node['cluster_id'] for node in nodes if node.get('cluster_id') is not None]
    parent_nodes = [{'id': '%s' % cluster_id} for cluster_id in list(set(cluster_ids))]

    # create the parent nodes for subclusters
    for node in nodes:
        if node.get('subcluster_id') is None:
            continue
        parent_node_id = node.get('parent')
        if parent_node_id in [node['id'] for node in parent_nodes]:
            continue
        parent_nodes.append({'id': parent_node_id, 'parent': node['cluster_id']})

    return nodes, parent_nodes
