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
from opencell.database import models, metadata_operations, uniprot_utils, cytoscape_networks
from opencell.database import utils as db_utils
from opencell.imaging.processors import FOVProcessor


# copied from https://stackoverflow.com/questions/24816799/how-to-use-flask-cache-with-flask-restful
def cache_key():
    args = flask.request.args
    key = flask.request.path + '?' + urllib.parse.urlencode([
        (k, v) for k in sorted(args) for v in sorted(args.getlist(k))
    ])
    return key


class ClearCache(Resource):
    def get(self):
        with flask.current_app.app_context():
            cache.clear()
        return flask.jsonify({'result': 'cache cleared'})


class Search(Resource):
    def get(self, search_string):

        payload = {}
        search_string = search_string.upper()
        publication_ready_only = flask.request.args.get('publication_ready') == 'true'

        # search for opencell targets
        query = (
            flask.current_app.Session.query(models.CellLine).join(models.CellLine.crispr_design)
            .filter(db.func.upper(models.CrisprDesign.target_name) == search_string)
        )

        if publication_ready_only:
            cell_line_ids = metadata_operations.get_lines_by_annotation(
                engine=flask.current_app.Session.get_bind(), annotation='publication_ready'
            )
            query = query.filter(models.CellLine.id.in_(cell_line_ids))

        # hack for the positive controls
        if search_string in ['CLTA', 'BCAP31']:
            query = query.filter(models.CrisprDesign.plate_design_id == 'P0001')

        targets = query.all()

        # use a zero-padded 11-digit number to match ENSG ID format
        if targets:
            payload['oc_ids'] = ['OPCT%011d' % target.id for target in targets]

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
        publication_ready_only = args.get('publication_ready') == 'true'

        included_fields = args.get('fields')
        included_fields = included_fields.split(',') if included_fields else []

        cell_line_ids = args.get('ids')
        cell_line_ids = [int(_id) for _id in cell_line_ids.split(',')] if cell_line_ids else []

        if publication_ready_only:
            cell_line_ids = metadata_operations.get_lines_by_annotation(
                engine=flask.current_app.Session.get_bind(), annotation='publication_ready'
            )

        # cell line query with the eager-loading required by generate_cell_line_payload
        query = (
            Session.query(models.CellLine)
            .join(models.CellLine.crispr_design)
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
        )

        if plate_id:
            query = query.filter(models.CrisprDesign.plate_design_id == plate_id)
        if cell_line_ids:
            query = query.filter(models.CellLine.id.in_(cell_line_ids))

        if 'best-fov' in included_fields:
            query = query.options(
                (
                    db.orm.joinedload(models.CellLine.fovs, innerjoin=True)
                    .joinedload(models.MicroscopyFOV.rois, innerjoin=True)
                    .joinedload(models.MicroscopyFOVROI.thumbnails, innerjoin=True)
                ), (
                    db.orm.joinedload(models.CellLine.fovs, innerjoin=True)
                    .joinedload(models.MicroscopyFOV.annotation, innerjoin=True)
                )
            )

        lines = query.all()

        # a separate query for counting FOVs and annotated FOVs per cell line
        fov_counts_query = (
            Session.query(
                models.CellLine.id,
                db.func.count(models.MicroscopyFOV.id).label('num_fovs'),
                db.func.count(models.MicroscopyFOVAnnotation.id).label('num_annotated_fovs'),
            )
            .outerjoin(models.CellLine.fovs)
            .outerjoin(models.MicroscopyFOV.annotation)
            .filter(models.CellLine.id.in_([line.id for line in lines]))
            .group_by(models.CellLine.id)
        )
        fov_counts = pd.DataFrame(data=fov_counts_query.all())

        # hackish counting of the number of annotated FOVs from dragonfly-automation datasets
        # (the 'da' stands for dragonfly-automation)
        da_pmls = ['PML%04d' % ind for ind in range(196, 999)]
        fov_counts_query = fov_counts_query.filter(models.MicroscopyFOV.pml_id == db.any_(da_pmls))
        fov_counts_da = pd.DataFrame(data=fov_counts_query.all())
        fov_counts_da.rename(
            columns={column: '%s_da' % column for column in fov_counts_da.columns},
            inplace=True
        )
        fov_counts = pd.merge(
            fov_counts, fov_counts_da, left_on='id', right_on='id_da', how='left'
        )

        # the list of pulldown_ids with saved cytoscape networks
        pulldowns_with_saved_networks = [
            row[0] for row in Session.query(models.MassSpecPulldownNetwork.pulldown_id).all()
        ]

        cell_line_payloads = []
        for line in lines:
            payload = payloads.generate_cell_line_payload(line, included_fields)

            # append the FOV counts (for the internal version of the frontend)
            fov_count = fov_counts.loc[fov_counts.id == line.id].iloc[0]
            if fov_count.shape[0]:
                payload['fov_counts'] = json.loads(fov_count.to_json())

            # append a flag for the existence of a saved pulldown network
            pulldown_id = payload['best_pulldown']['id']
            if pulldown_id is not None:
                payload['best_pulldown']['has_saved_network'] = (
                    pulldown_id in pulldowns_with_saved_networks
                )

            cell_line_payloads.append(payload)

        return flask.jsonify(cell_line_payloads)


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
    '''
    The cell line metadata for a single cell line
    '''
    def get(self, cell_line_id):
        line = self.get_cell_line(cell_line_id)
        optional_fields, error = self.parse_listlike_arg('fields', allowed_values=['best-fov'])
        if error:
            return error
        payload = payloads.generate_cell_line_payload(line, optional_fields)
        return flask.jsonify(payload)


class InteractorResource(Resource):

    @staticmethod
    def get_uniprot_metadata(ensg_id):
        '''
        Get all of the uniprot metadata entries associated with an ENSG ID
        '''
        uniprot_metadata = (
            flask.current_app.Session.query(models.UniprotMetadata)
            .filter(models.UniprotMetadata.ensg_id == ensg_id)
            .all()
        )
        return uniprot_metadata

    @staticmethod
    def get_primary_protein_group(ensg_id):
        '''
        Get the 'primary' protein group for an ENSG ID
        '''
        protein_group = (
            flask.current_app.Session.query(models.MassSpecProteinGroup)
            .join(models.EnsgProteinGroupAssociation)
            .filter(models.EnsgProteinGroupAssociation.ensg_id == ensg_id)
            .options(db.orm.joinedload(models.MassSpecProteinGroup.uniprot_metadata))
            .one_or_none()
        )
        return protein_group

    @staticmethod
    def construct_ensg_metadata(protein_group):
        '''
        Generates the metadata object for an ENSG ID from its 'primary' protein group,
        following the schema of the cell line metadata (see payloads.generate_cell_line_payload)
        '''
        payload = {}

        # TODO: a better way to pick the best uniprot_id from which to construct the metadata
        # (that is, from which to take the gene names and function annotation)
        uniprot_metadata = protein_group.uniprot_metadata[0]

        # HACK: this is copied from the cell_line payload
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

        # generic ensg-level metadata (mimics the cell_line 'metadata' field)
        payload['metadata'] = {
            'ensg_id': uniprot_metadata.ensg_id,
            'target_name': payload['uniprot_metadata']['gene_names'][0]
        }
        return payload


class InteractorTargets(InteractorResource):
    '''
    The metadata and the list of interacting opencell targets for an 'interactor'
    (identified by an ensg_id)
    '''
    def get(self, ensg_id):

        primary_protein_group = self.get_primary_protein_group(ensg_id)
        if not primary_protein_group:
            return flask.abort(404, 'There is no primary protein group for ENSG ID %s' % ensg_id)

        payload = self.construct_ensg_metadata(primary_protein_group)
        interacting_pulldowns = primary_protein_group.get_pulldowns()

        payload['interacting_cell_lines'] = [
            payloads.generate_cell_line_payload(pulldown.cell_line, included_fields=[])
            for pulldown in interacting_pulldowns
        ]
        return flask.jsonify(payload)


class InteractorNetwork(InteractorResource):
    '''
    The cytoscape interaction network for an interactor (identified by an ensg_id)
    '''
    def get(self, ensg_id):

        primary_protein_group = self.get_primary_protein_group(ensg_id)
        if not primary_protein_group:
            return flask.abort(404, 'There is no primary protein group for ENSG ID %s' % ensg_id)

        interacting_pulldowns = primary_protein_group.get_pulldowns()
        nodes, edges = cytoscape_networks.construct_network(
            interacting_pulldowns=interacting_pulldowns,
            origin_protein_group=primary_protein_group,
        )

        # create compound nodes to represent superclusters and subclusters
        nodes, parent_nodes = cytoscape_networks.construct_compound_nodes(
            nodes,
            clustering_analysis_type=flask.request.args.get('clustering_analysis_type'),
            subcluster_type=flask.request.args.get('subcluster_type'),
            engine=flask.current_app.Session.get_bind()
        )
        payload = {
            'parent_nodes': [{'data': node} for node in parent_nodes],
            'nodes': [{'data': node} for node in nodes],
            'edges': [{'data': edge} for edge in edges],
            'metadata': self.construct_ensg_metadata(primary_protein_group)
        }
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
    The metadata and hits for a pulldown
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


class PulldownNetwork(PulldownResource):
    '''
    The cytoscape interaction network for a pulldown
    (see comments in cytoscape_networks.construct_network for details)
    '''
    @cache.cached(timeout=3600, key_prefix=cache_key)
    def get(self, pulldown_id):

        pulldown = self.get_pulldown(pulldown_id)

        # determine the primary protein group to represent the target;
        # if the target appears in its own pulldown, this is easy
        bait_hit = pulldown.get_bait_hit(only_one=True)
        if bait_hit:
            bait_protein_group = bait_hit.protein_group

        # if the target does not appear in its own pulldown, we must use the protein group
        # for the ENSG ID associated with the target's crispr design
        else:
            bait_protein_group = InteractorResource.get_primary_protein_group(
                pulldown.cell_line.crispr_design.uniprot_metadata.ensg_id
            )

        # create nodes to represent direct hits and/or interacting pulldowns,
        # and the edges between them
        nodes, edges = cytoscape_networks.construct_network(
            target_pulldown=pulldown, origin_protein_group=bait_protein_group
        )

        # create compound nodes to represent superclusters and subclusters
        nodes, parent_nodes = cytoscape_networks.construct_compound_nodes(
            nodes,
            clustering_analysis_type=flask.request.args.get('clustering_analysis_type'),
            subcluster_type=flask.request.args.get('subcluster_type'),
            engine=flask.current_app.Session.get_bind()
        )

        payload = {
            'parent_nodes': [{'data': node} for node in parent_nodes],
            'nodes': [{'data': node} for node in nodes],
            'edges': [{'data': edge} for edge in edges],
            'metadata': pulldown.as_dict(),
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
        '''
        Create or modify the FOV annotation and, if an annotation already exists,
        delete its corresponding ROI

        Note: we delete the ROI because we assume that if it already exists,
        it will need to be recreated to reflect the changes to the annotation
        '''
        data = flask.request.get_json()
        fov = self.get_fov(fov_id)

        annotation = fov.annotation
        if annotation is None:
            annotation = models.MicroscopyFOVAnnotation(fov_id=fov_id)
        else:
            db_utils.delete_and_commit(flask.current_app.Session, fov.rois)

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
        '''
        Delete both the annotation and its corresponding ROI (if one exists)

        Note: to delete the annotation's ROI, we assume that the only ROI associated with the FOV
        is the one associated with its annotation, so we can simply delete fov.rois entirely
        (this is a useful shortcut because there is currently no direct relationship
        between the annotation and its corresponding annotated ROI)
        '''
        fov = self.get_fov(fov_id)
        if fov.annotation is None:
            return flask.abort(404, 'FOV %s does not have an annotation' % fov_id)
        try:
            db_utils.delete_and_commit(flask.current_app.Session, fov.annotation)
            db_utils.delete_and_commit(flask.current_app.Session, fov.rois)
        except Exception as error:
            flask.abort(500, str(error))
        return ('', 204)


class SavedPulldownNetwork(PulldownResource):
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


class EmbeddingPositions(Resource):

    def get(self, description):
        grid_size = int(flask.request.args.get('grid_size')) or 0
        n_neighbors = int(flask.request.args.get('n_neighbors'))
        min_dist = float(flask.request.args.get('min_dist'))

        # hack: construct the name of the embedding manually (and hard-code 'kind=umap')
        name = (
            '%s--kind=umap--n_neighbors=%d--min_dist=%0.1f' %
            (description, n_neighbors, min_dist)
        )

        embedding = (
            flask.current_app.Session.query(models.CellLineEmbedding)
            .filter(models.CellLineEmbedding.name == name)
            .filter(models.CellLineEmbedding.grid_size == grid_size)
            .options(db.orm.joinedload(models.CellLineEmbedding.positions))
            .one_or_none()
        )
        if not embedding:
            return flask.abort(404, "No embedding found for name '%s'" % name)

        payload = [
            {
                'x': position.position_x,
                'y': position.position_y,
                'cell_line_id': position.cell_line_id
            } for position in embedding.positions
        ]
        return flask.jsonify(payload)


class ThumbnailTileImage(Resource):

    def get(self):
        filename = flask.request.args.get('filename')
        microscopy_dir = flask.current_app.config.get('OPENCELL_MICROSCOPY_DIR')
        filepath = os.path.join(microscopy_dir, 'thumbnail-tiles', filename)
        if microscopy_dir.startswith('http'):
            return flask.redirect(filepath)
        else:
            return flask.send_file(
                open(filepath, 'rb'),
                as_attachment=True,
                attachment_filename=filepath.split(os.sep)[-1]
            )


class ThumbnailTilePositions(Resource):

    def get(self):

        filename = flask.request.args.get('filename')
        tile = (
            flask.current_app.Session.query(models.ThumbnailTile)
            .filter(models.ThumbnailTile.filename == filename)
            .options(db.orm.joinedload(models.ThumbnailTile.positions))
            .one_or_none()
        )
        if not tile:
            return flask.abort(404, "No tile found with filename '%s'" % filename)

        payload = [
            {
                'row': position.tile_row,
                'col': position.tile_column,
                'cell_line_id': position.cell_line_id
            } for position in tile.positions
        ]
        return flask.jsonify(payload)
