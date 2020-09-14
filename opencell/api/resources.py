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
from opencell.database import models, operations
from opencell.database import utils as db_utils
from opencell.imaging.processors import FOVProcessor


# copied from https://stackoverflow.com/questions/24816799/how-to-use-flask-cache-with-flask-restful
def cache_key():
    args = flask.request.args
    key = flask.request.path + '?' + urllib.parse.urlencode([
        (k, v) for k in sorted(args) for v in sorted(args.getlist(k))
    ])
    return key


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
        plate_id = args.get('plate')
        target_name = args.get('target')

        included_fields = args.get('fields')
        included_fields = included_fields.split(',') if included_fields else []

        cell_line_ids = args.get('ids')
        cell_line_ids = [int(_id) for _id in cell_line_ids.split(',')] if cell_line_ids else []

        query = (
            Session.query(models.CrisprDesign)
            .options(db.orm.joinedload(models.CrisprDesign.cell_lines, innerjoin=True))
        )

        # filter crispr designs by plate_id
        if plate_id:
            query = query.filter(models.CrisprDesign.plate_design_id == plate_id)

        # filter crispr designs by target name
        if target_name:
            # check for an exact match to the target name
            exact_query = query.filter(
                db.func.lower(models.CrisprDesign.target_name) == target_name.lower()
            )
            # if no exact match, filter by startswith
            if not exact_query.all():
                query = query.filter(
                    db.func.lower(models.CrisprDesign.target_name)
                    .startswith(target_name.lower())
                )
            else:
                query = exact_query

        # retrieve all of the cell lines corresponding to the filtered crispr designs
        all_ids = []
        [all_ids.extend([line.id for line in design.cell_lines]) for design in query.all()]

        # retain only the cell_line_ids that were included in the URL (if any)
        if len(cell_line_ids):
            all_ids = list(set(all_ids).intersection(cell_line_ids))

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
            )
            .filter(models.CellLine.id.in_(all_ids))
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
    def get_pulldown(cell_line_id):
        '''
        Get the 'good' pulldown associated with the cell line
        '''
        line = (
            flask.current_app.Session.query(models.CellLine)
            .options(db.orm.joinedload(models.CellLine.pulldowns, innerjoin=True))
            .filter(models.CellLine.id == cell_line_id)
            .one_or_none()
        )
        if not line or not line.pulldowns:
            return flask.abort(
                404, 'There are no pulldowns associated with cell line %d' % cell_line_id
            )
        return line.get_best_pulldown()



class PulldownHits(PulldownResource):
    '''
    The mass spec pulldown and its associated hits for a cell line
    '''
    def get(self, cell_line_id):
        Session = flask.current_app.Session
        pulldown = self.get_pulldown(cell_line_id)
        if not pulldown.hits:
            return flask.abort(
                404, 'The pulldown for cell line %s does not have any hits' % cell_line_id
            )

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
    1) the direct interactions (between the cell line's target and the pulldown's hits),
    2) the observed interactions between direct interactors (e.g., hits)
       (these are observed when hits correspond to other opencell targets)
    3) the inferred interactions betweens direct interactors
       (these are inferred when the protein groups of two hits appear in similar sets of pulldowns)
    '''

    def get(self, cell_line_id):

        pulldown = self.get_pulldown(cell_line_id)
        direct_hits = pulldown.get_significant_hits()
        # interacting_pulldowns = pulldown.get_interacting_pulldowns()

        direct_node_ids = [hit.protein_group.id for hit in direct_hits]
        nodes = {}
        edges = []

        for direct_hit in direct_hits:

            # create a node for the direct hit
            node_id = direct_hit.protein_group.id
            node = payloads.generate_protein_group_payload(
                direct_hit.protein_group, pulldown.cell_line.crispr_design.id
            )
            node['id'] = node_id
            nodes[node_id] = node

            # if the hit is the bait itself,
            # or if the hit does not correspond to any opencell targets,
            # or if the hit corresponds to multiple distinct opencell targets,
            # we do not need to generate edges between the hit and the other hits
            designs = direct_hit.protein_group.crispr_designs
            num_distinct_designs = len(set([d.uniprot_id for d in designs]))
            if node['is_bait'] or not designs or num_distinct_designs > 1:
                continue

            # if the hit does correspond to an opencell target,
            # find the best cell line corresponding to the hit's protein group
            # note that this is complicated because there may be more than one crispr design
            # for a given protein group, and because there may be more than one cell line per design
            # (e.g., for resorted targets)
            direct_hit_pulldown = None
            for design in designs:
                line = design.get_best_cell_line()
                if line:
                    direct_hit_pulldown = line.get_best_pulldown()
                    if direct_hit_pulldown:
                        break

            # if none of the hit's target's cell lines have pulldowns, we can't do anything
            if not direct_hit_pulldown:
                continue

            # the hit's target's hits
            indirect_hits = direct_hit_pulldown.get_significant_hits()
            for indirect_hit in indirect_hits:
                indirect_node_id = indirect_hit.protein_group.id

                # if the hit of the hit is not among the direct hits, we don't include it
                if indirect_node_id not in direct_node_ids or indirect_node_id == node_id:
                    continue

                # create the edge between the two direct hits
                edges.append({
                    'data': {
                        'id': '%s-%s' % (node_id, indirect_node_id),
                        'source': node_id,
                        'target': indirect_node_id,
                        'type': 'prey-prey',
                    }
                })

        # create a node for the bait if the bait was not found among the hits
        bait_hit_exists = True in [node['is_bait'] for node in nodes.values()]
        if not bait_hit_exists:
            node_id = 'bait-placeholder'
            nodes[node_id] = {
                'id': node_id,
                'uniprot_gene_names': [],
                'opencell_target_names': pulldown.cell_line.crispr_design.target_name,
                'is_bait': True,
            }

        # create the edges between the bait and its interactors
        bait_node_id = [node['id'] for node in nodes.values() if node['is_bait']][0]
        for hit in direct_hits:
            node_id = hit.protein_group.id
            node = nodes[node_id]
            if node['is_bait']:
                continue
            edges.append({
                'data': {
                    'id': '%s-%s' % (bait_node_id, node_id),
                    'source': bait_node_id,
                    'target': node_id,
                    'type': 'bait-prey',
                }
            })

        payload = {
            'nodes': [{'data': node} for node in nodes.values()],
            'edges': edges,
        }
        return flask.jsonify(payload)


class PulldownClusters(PulldownResource):
    '''
    The cluster heatmap(s) in which a cell line's pulldown appears

    The cluster heatmap represents a
    '''
    def get(self, cell_line_id):
        Session = flask.current_app.Session
        pulldown = self.get_pulldown(cell_line_id)

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
            return flask.abort(
                404, 'The pulldown for cell line %s does not appear in any clusters' % cell_line_id
            )

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
                errors='raise')
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
