import os
import io
import flask
import json
import urllib
import imageio
import tifffile
import pandas as pd
import sqlalchemy as db
from flask_restful import Resource, reqparse

from opencell.imaging import utils
from opencell.api import payloads
from opencell.api.cache import cache
from opencell.database import models, operations, uniprot_utils
from opencell.database import utils as db_utils
from opencell.imaging.processors import FOVProcessor


# copied from https://stackoverflow.com/questions/24816799/how-to-use-flask-cache-with-flask-restful
def cache_key():
    args = flask.request.args
    key = flask.request.path + '?' + urllib.parse.urlencode([
        (k, v) for k in sorted(args) for v in sorted(args.getlist(k))
    ])
    return key


class Search(Resource):
    def get(self, search_string):

        payload = {}
        search_string = search_string.upper()

        # search for opencell targets
        query = (
            flask.current_app.Session.query(models.CellLine).join(models.CellLine.crispr_design)
            .filter(db.func.upper(models.CrisprDesign.target_name) == search_string)
        )

        # hack for the positive controls
        if search_string.lower() in ['CLTA', 'BCAP31']:
            query = query.filter(models.CrisprDesign.plate_design_id == 'P0001')

        targets = query.all()
        if targets:
            payload['oc_id'] = 'OPCT%06d' % targets[0].id

        # search the gene names column in the uniprot metadata table
        uniprot_metadata = pd.read_sql(
            f'''
            select ensg_id from (
                select *, string_to_array(gene_names, ' ') as gene_names_array
                from uniprot_metadata
            ) tmp
            where '{search_string}' = any(gene_names_array)
            ''',
            flask.current_app.Session.get_bind()
        )
        if len(uniprot_metadata):
            payload['ensg_ids'] = list(set([row.ensg_id for _, row in uniprot_metadata.iterrows()]))

        return flask.jsonify(payload)



class Plate(Resource):

    def get(self, plate_id):
        plate = (
            flask.current_app.Session.query(models.PlateDesign)
            .filter(models.PlateDesign.design_id == plate_id)
            .one_or_none()
        )
        targets = [d.target_name for d in plate.crispr_designs]
        return {
            'plate_id': plate.design_id,
            'targets': targets,
        }


class CellLines(Resource):
    '''
    A list of cell line metadata for all cell lines,
    possibly filtered by plate_id and target name
    '''
    @cache.cached(timeout=3600, key_prefix=cache_key)
    def get(self):

        Session = flask.current_app.Session

        args = flask.request.args
        plate_id = args.get('plate_id')
        target_like = args.get('target_like')
        target_name = args.get('target_name')

        included_fields = args.get('fields')
        included_fields = included_fields.split(',') if included_fields else []

        cell_line_ids = args.get('ids')
        cell_line_ids = [int(_id) for _id in cell_line_ids.split(',')] if cell_line_ids else []

        query = Session.query(models.CellLine).join(models.CellLine.crispr_design)

        # search for an exact match to the target_name
        # TODO: filter for 'good' crispr designs when there's more than one for a target name
        if target_name:
            query = query.filter(
                db.func.lower(models.CrisprDesign.target_name) == target_name.lower()
            )

            # hack for the positive controls
            if target_name.lower() in ['clta', 'bcap31']:
                query = query.filter(models.CrisprDesign.plate_design_id == 'P0001')

        # filter by plate_id and target_like
        else:
            if plate_id:
                query = query.filter(models.CrisprDesign.plate_design_id == plate_id)
            if target_like:
                query = query.filter(
                    db.func.lower(models.CrisprDesign.target_name).startswith(target_like.lower())
                )
            if cell_line_ids:
                query = query.filter(models.CellLine.id.in_(cell_line_ids))

        lines = (
            Session.query(models.CellLine)
            .options(
                (
                    db.orm.joinedload(models.CellLine.crispr_design, innerjoin=True)
                    .joinedload(models.CrisprDesign.uniprot_metadata, innerjoin=True)
                ),
                db.orm.joinedload(models.CellLine.facs_dataset),
                db.orm.joinedload(models.CellLine.sequencing_dataset),
                db.orm.joinedload(models.CellLine.annotation),
                db.orm.joinedload(models.CellLine.pulldowns)
            )
            .filter(models.CellLine.id.in_([line.id for line in query.all()]))
            .all()
        )

        # TODO: pass the FOV counts to the cell_line_payload method if they are needed
        _ = (
            Session.query(
                models.CellLine.id,
                db.func.count(models.MicroscopyFOV.id).label('num_fovs'),
                db.func.count(models.MicroscopyFOVAnnotation.id).label('num_annotated_fovs'),
            )
            .outerjoin(models.CellLine.fovs)
            .outerjoin(models.MicroscopyFOV.annotation)
            .group_by(models.CellLine.id)
            .all()
        )

        payload = [
            payloads.generate_cell_line_payload(line, included_fields) for line in lines
        ]
        return flask.jsonify(payload)


class CellLineResource(Resource):

    def parse_listlike_arg(self, name, allowed_values, sep=','):
        '''
        Parse and validate a list-like URL parameter
        '''
        error = None
        arg = flask.request.args.get(name)
        values = arg.split(sep) if arg else []
        if not set(values).issubset(allowed_values):
            error = flask.abort(404, 'Invalid value passed to the %s parameter' % name)
        return values, error

    @staticmethod
    def get_cell_line(cell_line_id):
        return (
            flask.current_app.Session.query(models.CellLine)
            .filter(models.CellLine.id == cell_line_id)
            .one_or_none()
        )


class CellLine(CellLineResource):

    def get(self, cell_line_id):
        line = self.get_cell_line(cell_line_id)
        optional_fields, error = self.parse_listlike_arg('fields', allowed_values=['best-fov'])
        if error:
            return error
        payload = payloads.generate_cell_line_payload(line, optional_fields)
        return flask.jsonify(payload)


class Interactor(Resource):

    def get(self, ensg_id):

        payload = {}

        uniprot_metadata = (
            flask.current_app.Session.query(models.UniprotMetadata)
            .filter(models.UniprotMetadata.ensg_id == ensg_id)
            .all()
        )
        if not uniprot_metadata:
            return flask.abort(404, 'There is no uniprot metadata for ENSG ID %s' % ensg_id)

        # all of the uniprot_ids associated with this ensg_id
        uniprot_ids = [row.uniprot_id for row in uniprot_metadata]

        # TODO: better way to pick the best uniprot entry from which to construct the metadata
        # (that is, the gene names and function annotation)
        uniprot_metadata = uniprot_metadata[0]

        payload['uniprot_metadata'] = {
            'uniprot_id': uniprot_metadata.uniprot_id,
            'gene_names': uniprot_metadata.gene_names.split(' '),
            'protein_name': uniprot_utils.prettify_uniprot_protein_name(
                uniprot_metadata.protein_names
            ),
            'annotation': uniprot_utils.prettify_uniprot_annotation(
                uniprot_metadata.annotation
            ),
        }

        # get the opencell targets in whose pulldowns this interactor appears as a hit
        interacting_pulldowns = (
            flask.current_app.Session.query(models.MassSpecPulldown)
            .join(models.MassSpecHit)
            .join(models.MassSpecProteinGroup)
            .join(models.ProteinGroupUniprotMetadataAssociation)
            .filter(db.or_(
                models.MassSpecPulldown.manual_display_flag == None,  # noqa
                models.MassSpecPulldown.manual_display_flag == True  # noqa
            ))
            .filter(
                models.ProteinGroupUniprotMetadataAssociation.uniprot_id.in_(uniprot_ids)
            )
            .filter(db.or_(
                models.MassSpecHit.is_minor_hit == True,  # noqa
                models.MassSpecHit.is_significant_hit == True  # noqa
            ))
            .all()
        )

        payload['cell_lines'] = [
            payloads.generate_cell_line_payload(pulldown.cell_line, included_fields=[])
            for pulldown in interacting_pulldowns
        ]

        return flask.jsonify(payload)




class FACSDataset(CellLineResource):

    def get(self, cell_line_id):
        line = self.get_cell_line(cell_line_id)
        if not line.facs_dataset:
            return flask.abort(404)
        payload = payloads.generate_facs_payload(line.facs_dataset)
        return flask.jsonify(payload)


class MicroscopyFOVMetadata(CellLineResource):
    '''
    Metadata for all of the FOVs associated with a cell line
    '''
    def get(self, cell_line_id):

        only_annotated = flask.request.args.get('annotatedonly') == 'true'

        included_fields, error = self.parse_listlike_arg(
            name='fields', allowed_values=['rois', 'thumbnails']
        )
        if error:
            return error

        line = self.get_cell_line(cell_line_id)
        query = (
            flask.current_app.Session.query(models.MicroscopyFOV)
            .options(
                db.orm.joinedload(models.MicroscopyFOV.dataset, innerjoin=True),
                db.orm.joinedload(models.MicroscopyFOV.results, innerjoin=True),
                db.orm.joinedload(models.MicroscopyFOV.annotation)
            )
            .filter(models.MicroscopyFOV.cell_line_id == line.id)
        )

        if only_annotated:
            query = query.filter(models.MicroscopyFOV.annotation != None)  # noqa

        if 'rois' in included_fields:
            query = query.options(
                db.orm.joinedload(models.MicroscopyFOV.rois, innerjoin=True)
            )

        if 'thumbnails' in included_fields:
            query = query.options(
                db.orm.joinedload(models.MicroscopyFOV.thumbnails, innerjoin=False)
            )

        fovs = query.all()
        if not fovs:
            return flask.abort(404, 'There are no FOVs associated with the cell line')

        payload = [
            payloads.generate_fov_payload(
                fov,
                include_rois=('rois' in included_fields),
                include_thumbnails=('thumbnails' in included_fields)
            )
            for fov in fovs
        ]

        # sort by FOV score (unscored FOVs last)
        payload = sorted(payload, key=lambda row: row['metadata'].get('score') or -2)[::-1]
        return flask.jsonify(payload)


class PulldownResource(CellLineResource):

    @staticmethod
    def get_pulldown(pulldown_id):
        pulldown = (
            flask.current_app.Session.query(models.MassSpecPulldown)
            .filter(models.MassSpecPulldown.id == pulldown_id)
            .one_or_none()
        )
        if not pulldown:
            return flask.abort(404, 'Pulldown %d does not exist' % pulldown_id)
        return pulldown


class PulldownHits(PulldownResource):
    '''
    The mass spec pulldown and its associated hits for a cell line
    '''
    def get(self, pulldown_id):
        Session = flask.current_app.Session
        pulldown = self.get_pulldown(pulldown_id)
        if not pulldown.hits:
            return flask.abort(404, 'Pulldown %s does not have any hits' % pulldown_id)

        significant_hits = pulldown.get_significant_hits()

        # we need only the pval and enrichment for the non-significant hits
        nonsignificant_hits = (
            Session.query(models.MassSpecHit.pval, models.MassSpecHit.enrichment)
            .filter(models.MassSpecHit.pulldown_id == pulldown.id)
            .filter(models.MassSpecHit.is_minor_hit == False)  # noqa
            .filter(models.MassSpecHit.is_significant_hit == False)  # noqa
            .all()
        )

        # construct the JSON payload from the pulldown and hit instances
        payload = payloads.generate_pulldown_hits_payload(
            pulldown, significant_hits, nonsignificant_hits
        )
        return flask.jsonify(payload)


class PulldownInteractions(PulldownResource):
    '''
    The interaction network for a cell line
    This consists of
    1) the direct interactors of the target
        (these include both the target's own hits and other targets
        in whose pulldowns the target appears as a hit),
    2) the observed interactions between the direct interactors
       (when one direct interactor appears in the pulldown of another direct interactor)
    3) the inferred interactions betweens direct interactors
       (these exist when the protein groups of two interactors appear in similar sets of pulldowns)
    '''

    @staticmethod
    def protein_group_to_node(protein_group):
        node = payloads.generate_protein_group_payload(protein_group)
        node['id'] = protein_group.id
        node.pop('is_bait')
        return node

    @cache.cached(timeout=3600, key_prefix=cache_key)
    def get(self, pulldown_id):

        args = flask.request.args
        analysis_type = args.get('analysis_type')
        subcluster_type = args.get('subcluster_type')

        # 'original' clustering
        if analysis_type == 'original':
            analysis_type = 'clusterone_d05_o01_mcl_i7_haircut'

        # clustering from 2020-09-24 with subclusters and core complexes
        if analysis_type == 'new':
            analysis_type = (
                'primary:mcl_i2.0_haircut:keepcore_subcluster:newman_eigen_corecomplex:newman_eigen'
            )

        if subcluster_type == 'subclusters':
            subcluster_id_column = 'subcluster_id'
        if subcluster_type == 'core-complexes':
            subcluster_id_column = 'core_complex_id'

        clusters = pd.read_sql(
            f'''
            select protein_group_id, cluster_id, subcluster_id, core_complex_id
            from mass_spec_cluster_heatmap heatmap
            inner join mass_spec_hit hit on hit.id = heatmap.hit_id
            where analysis_type = '{analysis_type}'
            ''',
            flask.current_app.Session.get_bind()
        )

        # cluster memberships are the same for all hits with the same protein group (by design)
        clusters = clusters.groupby(['protein_group_id']).first().reset_index()

        pulldown = self.get_pulldown(pulldown_id)
        direct_hits = pulldown.get_significant_hits()
        interacting_pulldowns = pulldown.get_interacting_pulldowns()

        # the list of nodes (direct interactors)
        nodes = []

        # create a node to represent the target
        bait_hit = pulldown.get_bait_hit(only_one=True)
        bait_node = {'type': 'bait', 'pulldown': pulldown}
        if bait_hit:
            bait_node.update(self.protein_group_to_node(bait_hit.protein_group))

        # if the target does not appear in its own pulldown as a hit,
        # manually fill in the attributes populated by self.protein_group_to_node
        else:
            bait_node.update({
                'id': 'bait-placeholder',
                'uniprot_gene_names': [],
                'opencell_target_names': [pulldown.cell_line.crispr_design.target_name],
            })
        nodes.append(bait_node)

        # create nodes to represent the hits in the target's pulldown
        for direct_hit in direct_hits:
            if bait_hit and bait_hit.protein_group.id == direct_hit.protein_group.id:
                continue
            node = self.protein_group_to_node(direct_hit.protein_group)
            node['hit'] = direct_hit
            node['type'] = 'hit'
            nodes.append(node)

        # create nodes to represent the pulldowns in which the target appears as a hit
        for interacting_pulldown in interacting_pulldowns:
            interacting_bait_hit = interacting_pulldown.get_bait_hit(only_one=True)

            # if the bait was not found in the interacting pulldown,
            # we cannot create a node to represent the pulldown
            if not interacting_bait_hit:
                continue

            protein_group = interacting_bait_hit.protein_group
            node = self.protein_group_to_node(protein_group)
            node['pulldown'] = interacting_pulldown
            node['type'] = 'pulldown'
            nodes.append(node)

        all_node_ids = [node['id'] for node in nodes]

        # create dict of cluster_ids keyed by protein_group_id
        # (used only to determine whether edges are inter- or intra-cluster)
        # (hack: takes the first cluster_id when a protein group has more than one)
        node_ids_to_cluster_ids = {}
        for protein_group_id in all_node_ids:
            _clusters = clusters.loc[clusters.protein_group_id == protein_group_id]
            if not _clusters.shape[0]:
                continue
            node_ids_to_cluster_ids[protein_group_id] = _clusters.iloc[0].cluster_id

        # the node id and cluster id of the bait node
        # bait_node_id = [node['id'] for node in nodes if node['type'] == 'bait'][0]

        # generate the edges between direct nodes
        edges = []
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

            node_cluster_id = node_ids_to_cluster_ids.get(node['id'])
            for indirect_hit in indirect_hits:
                indirect_node_id = indirect_hit.protein_group.id

                # if the hit of the node is not among the nodes, we don't need to create an edge
                if indirect_node_id not in all_node_ids or indirect_node_id == node['id']:
                    continue

                # if the edge is between nodes in the same cluster
                edge_type = 'intercluster'
                if (
                    node_cluster_id is not None
                    and node_cluster_id == node_ids_to_cluster_ids.get(indirect_node_id)
                ):
                    edge_type = 'intracluster'

                # create the edge between the two direct interactors
                edges.append({
                    'id': '%s-%s' % (node['id'], indirect_node_id),
                    'source': node['id'],
                    'target': indirect_node_id,
                    'type': edge_type,
                })

        # all clusters in which more than one node appears
        clusters = clusters.loc[clusters.protein_group_id.isin(all_node_ids)]
        cluster_sizes = clusters.groupby('cluster_id').count().reset_index()
        clusters = clusters.loc[
            clusters.cluster_id.isin(
                cluster_sizes.loc[cluster_sizes.protein_group_id > 1].cluster_id.values
            )
        ]

        # append cluster ids and parent node ids
        for node in nodes:
            row = clusters.loc[clusters.protein_group_id == node['id']]
            if len(row):
                row = row.iloc[0]
                node['cluster_id'] = int(row.cluster_id) if not pd.isna(row.cluster_id) else None
                node['subcluster_id'] = (
                    int(row[subcluster_id_column]) if not pd.isna(row[subcluster_id_column]) else None
                )

            if node.get('subcluster_id'):
                node['parent'] = '%s-%s' % (node.get('cluster_id'), node.get('subcluster_id'))
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

        # create the lists of cluster members required by the CiSE cytoscape layout
        cluster_defs = []
        cluster_groups = clusters.groupby('cluster_id').groups
        for cluster_id, cluster_index in cluster_groups.items():
            _clusters = clusters.loc[cluster_index]
            cluster_defs.append({
                'cluster_id': int(cluster_id),
                'subcluster_ids': [
                    int(_id) for _id in _clusters[subcluster_id_column].unique() if not pd.isna(_id)
                ],
                'protein_group_ids': _clusters.protein_group_id.tolist(),
            })

        # drop the pulldown and hit instances from the node dicts
        for node in nodes:
            node.pop('hit', None)
            node.pop('pulldown', None)

        payload = {
            'parent_nodes': [{'data': node} for node in parent_nodes],
            'nodes': [{'data': node} for node in nodes],
            'edges': [{'data': edge} for edge in edges],
            'metadata': pulldown.as_dict(),
            'clusters': cluster_defs,
        }
        return flask.jsonify(payload)


class PulldownClusters(PulldownResource):
    '''
    The cluster heatmap(s) in which a cell line's pulldown appears

    The cluster heatmap represents a
    '''
    def get(self, pulldown_id):
        Session = flask.current_app.Session
        pulldown = self.get_pulldown(pulldown_id)

        # get the cluster_ids of all clusters in which the pulldown appears
        rows = (
            Session.query(db.distinct(models.MassSpecClusterHeatmap.cluster_id))
            .join(models.MassSpecClusterHeatmap.hit)
            .join(models.MassSpecHit.pulldown)
            .filter(models.MassSpecPulldown.id == pulldown.id)
            .all()
        )
        cluster_ids = [row[0] for row in rows]

        if not cluster_ids:
            return flask.abort(404, 'Pulldown %s does not appear in any clusters' % pulldown_id)

        # for now, if there are multiple clusters, pick the first one
        cluster_id = cluster_ids[0]

        # get the cluster heatmap tiles
        # (one row of the ClusterHeatmap table corresponds to one tile)
        rows = (
            Session.query(
                models.MassSpecClusterHeatmap.hit_id,
                models.MassSpecClusterHeatmap.row_index,
                models.MassSpecClusterHeatmap.col_index,
                models.MassSpecHit.pval,
                models.MassSpecHit.enrichment,
                models.MassSpecHit.interaction_stoich,
                models.MassSpecHit.abundance_stoich,
            )
            .join(models.MassSpecClusterHeatmap.hit)
            .filter(models.MassSpecClusterHeatmap.cluster_id == cluster_id)
            .all()
        )
        heatmap_tiles = pd.DataFrame(data=rows)

        # pick an arbitrary hit_id from each column and each row of the heatmap
        # we will use these hit_ids to retrieve the pulldown and protein group metadata
        # for the columns and rows, respectively, since we know/assume that all of the hits
        # in each column correspond to the same pulldown, and all of the hits in each row
        # correspond to the same protein group
        heatmap_row_metadata = heatmap_tiles.groupby('row_index').first().reset_index()
        heatmap_column_metadata = heatmap_tiles.groupby('col_index').first().reset_index()

        # the pulldowns corresponding to the heatmap columns
        heatmap_column_pulldowns = (
            Session.query(
                models.MassSpecHit.id.label('hit_id'),
                models.MassSpecHit.pulldown_id,
                models.CellLine.id.label('cell_line_id'),
                models.CrisprDesign.target_name
            )
            .join(models.MassSpecHit.pulldown)
            .join(models.MassSpecPulldown.cell_line)
            .join(models.CrisprDesign)
            .filter(
                models.MassSpecHit.id.in_(heatmap_column_metadata.hit_id.astype(int).tolist())
            )
            .all()
        )

        # merge the col_index with the pulldown metadata
        heatmap_column_metadata = pd.merge(
            heatmap_column_metadata[['hit_id', 'col_index']],
            pd.DataFrame(data=heatmap_column_pulldowns),
            on='hit_id'
        )

        # the protein groups corresponding to the heatmap rows
        # (the hits are included so that we can use the hit_id to merge the protein group metadata
        # with heatmap_row_metadata dataframe)
        heatmap_rows = (
            Session.query(models.MassSpecHit, models.MassSpecProteinGroup)
            .join(models.MassSpecProteinGroup.hits)
            .filter(models.MassSpecHit.id.in_(heatmap_row_metadata.hit_id.astype(int).tolist()))
            .all()
        )

        # construct the protein group metadata
        protein_group_metadata = []
        for hit, protein_group in heatmap_rows:
            metadata = payloads.generate_protein_group_payload(protein_group)
            metadata['hit_id'] = hit.id
            protein_group_metadata.append(metadata)

        # merge the row_index with the protein group metadata
        heatmap_row_metadata = pd.merge(
            heatmap_row_metadata[['hit_id', 'row_index']],
            pd.DataFrame(data=protein_group_metadata),
            on='hit_id'
        )

        # drop the now-useless hit_id column from the row and column metadata
        heatmap_row_metadata.drop(labels='hit_id', axis=1, inplace=True)
        heatmap_column_metadata.drop(labels='hit_id', axis=1, inplace=True)

        payload = {
            'metadata': {'cluster_id': cluster_id},
            'tiles': json.loads(heatmap_tiles.to_json(orient='records')),
            'rows': json.loads(heatmap_row_metadata.to_json(orient='records')),
            'columns': json.loads(heatmap_column_metadata.to_json(orient='records')),
        }
        return flask.jsonify(payload)


class MicroscopyFOV(Resource):

    def get(self, fov_id, kind, channel):
        '''
        Return the specified kind of processed data
        for a single FOV using Flask's send_file method

        kind : the kind of image data (projection, thumbnail, z-stack, etc)
        channel : one of '405', '488', or 'rgb'
        '''
        if kind != 'proj':
            flask.abort(404, 'Invalid kind')

        fov = (
            flask.current_app.Session.query(models.MicroscopyFOV)
            .filter(models.MicroscopyFOV.id == fov_id)
            .one_or_none()
        )
        if not fov:
            flask.abort(404, 'Invalid fov_id')

        processor = FOVProcessor.from_database(fov)
        dst_root = flask.current_app.config.get('OPENCELL_MICROSCOPY_DIR')
        filepath_405 = processor.dst_filepath(dst_root, kind='proj', channel='405', ext='tif')
        filepath_488 = processor.dst_filepath(dst_root, kind='proj', channel='488', ext='tif')

        if channel == '405':
            im = tifffile.imread(filepath_405)[..., None]
            im = utils.autoscale(im, p=1)
        elif channel == '488':
            im = tifffile.imread(filepath_488)[..., None]
            im = utils.autoscale(im, p=1)
        elif channel == 'rgb':
            im = processor.make_rgb(
                tifffile.imread(filepath_405)[..., None],
                tifffile.imread(filepath_488)[..., None]
            )

        file = io.BytesIO()
        imageio.imsave(file, im, format='jpg', quality=90)
        file.seek(0)

        filename = 'FOV%04d_%s-%s.jpg' % (fov_id, kind.upper(), channel.upper())
        return flask.send_file(file, as_attachment=True, attachment_filename=filename)


class MicroscopyFOVROI(Resource):

    def get(self, roi_id, roi_kind, channel):
        '''
        Get the image data for a given ROI

        roi_kind : the kind of ROI data to return
            'proj' returns a z-projection
            'lqtile' and 'hqtile' return low- and high-quality versions of the z-stack
            (as a one-dimensional tiled array of z-slices)
        channel : one of '405' or '488'

        '''
        if roi_kind not in ['proj', 'lqtile', 'hqtile']:
            flask.abort(404, 'Invalid ROI kind %s' % roi_kind)

        roi = (
            flask.current_app.Session.query(models.MicroscopyFOVROI)
            .filter(models.MicroscopyFOVROI.id == roi_id)
            .one_or_none()
        )
        if not roi:
            flask.abort(404, 'Invalid roi_id %s' % roi_id)

        microscopy_dir = flask.current_app.config.get('OPENCELL_MICROSCOPY_DIR')
        processor = FOVProcessor.from_database(roi.fov)
        filepath = processor.dst_filepath(
            dst_root=microscopy_dir,
            kind='roi',
            roi_id=roi_id,
            roi_kind=roi_kind,
            channel=channel,
            ext='jpg'
        )

        if microscopy_dir.startswith('http'):
            return flask.redirect(filepath)
        else:
            return flask.send_file(
                open(filepath, 'rb'),
                as_attachment=True,
                attachment_filename=filepath.split(os.sep)[-1]
            )


class CellLineAnnotation(CellLineResource):
    '''
    Get or create/update the manual annotation for a cell line
    '''
    def get(self, cell_line_id):

        line = self.get_cell_line(cell_line_id)
        if line.annotation is not None:
            return flask.jsonify({
                'comment': line.annotation.comment,
                'categories': line.annotation.categories,
                'client_metadata': line.annotation.client_metadata,
            })
        flask.abort(404)


    def put(self, cell_line_id):

        data = flask.request.get_json()
        line = self.get_cell_line(cell_line_id)
        annotation = line.annotation
        if annotation is None:
            annotation = models.CellLineAnnotation(cell_line_id=cell_line_id)

        annotation.comment = data.get('comment')
        annotation.categories = data.get('categories')
        annotation.client_metadata = data.get('client_metadata')

        try:
            db_utils.add_and_commit(
                flask.current_app.Session,
                annotation,
                errors='raise'
            )
        except Exception as error:
            flask.abort(500, str(error))

        return flask.jsonify(annotation.as_dict())


class MicroscopyFOVAnnotation(Resource):

    @staticmethod
    def get_fov(fov_id):
        return (
            flask.current_app.Session.query(models.MicroscopyFOV)
            .filter(models.MicroscopyFOV.id == fov_id)
            .one_or_none()
        )


    def get(self, fov_id):
        fov = self.get_fov(fov_id)
        if fov.annotation is not None:
            return flask.jsonify(fov.annotation.as_dict())
        flask.abort(404, 'FOV %s does not have an annotation' % fov_id)


    def put(self, fov_id):

        data = flask.request.get_json()
        fov = self.get_fov(fov_id)
        annotation = fov.annotation
        if annotation is None:
            annotation = models.MicroscopyFOVAnnotation(fov_id=fov_id)

        annotation.categories = data.get('categories')
        annotation.client_metadata = data.get('client_metadata')
        annotation.roi_position_top = data.get('roi_position_top')
        annotation.roi_position_left = data.get('roi_position_left')

        try:
            db_utils.add_and_commit(
                flask.current_app.Session,
                annotation,
                errors='raise'
            )
        except Exception as error:
            flask.abort(500, str(error))
        return flask.jsonify(annotation.as_dict())


    def delete(self, fov_id):

        fov = self.get_fov(fov_id)
        if fov.annotation is None:
            return flask.abort(404, 'FOV %s does not have an annotation' % fov_id)

        try:
            db_utils.delete_and_commit(flask.current_app.Session, fov.annotation)
        except Exception as error:
            flask.abort(500, str(error))
        return ('', 204)


class PulldownNetwork(PulldownResource):
    '''
    Cached manually-edited cytoscape layout for a cell line
    '''
    def get(self, pulldown_id):
        pulldown = self.get_pulldown(pulldown_id)
        if pulldown.network is not None:
            return flask.jsonify({
                'cytoscape_json': pulldown.network.cytoscape_json,
                'last_modified': pulldown.network.last_modified,
            })
        return flask.abort(
            404, 'Pulldown %s does not have a cached cytoscape network' % pulldown_id
        )

    def put(self, pulldown_id):
        data = flask.request.get_json()
        pulldown = self.get_pulldown(pulldown_id)
        network = pulldown.network
        if network is None:
            network = models.MassSpecPulldownNetwork(pulldown_id=pulldown_id)

        network.cytoscape_json = data.get('cytoscape_json')
        network.client_metadata = data.get('client_metadata')

        try:
            db_utils.add_and_commit(
                flask.current_app.Session,
                network,
                errors='raise'
            )
        except Exception as error:
            flask.abort(500, str(error))
        return flask.jsonify(network.as_dict())

    def delete(self, pulldown_id):
        pulldown = self.get_pulldown(pulldown_id)
        if pulldown.network is None:
            return flask.abort(
                404, 'Pulldown %s does not have a cached cytoscape network' % pulldown_id
            )
        try:
            db_utils.delete_and_commit(flask.current_app.Session, pulldown.network)
        except Exception as error:
            flask.abort(500, str(error))
        return ('', 204)
