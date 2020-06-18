import os
import io
import flask
import urllib
import imageio
import tifffile
import pandas as pd
import sqlalchemy as db
from flask_restful import Resource, reqparse

from opencell.imaging import utils
from opencell.api.cache import cache
from opencell.database import models, operations, payloads
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

        args = flask.request.args
        plate_id = args.get('plate')
        target_name = args.get('target')
        included_ids = args.get('ids')
        optional_fields = args.get('fields')

        optional_fields = optional_fields.split(',') if optional_fields else []
        included_ids = [int(_id) for _id in included_ids.split(',')] if included_ids else []

        query = (
            flask.current_app.Session.query(models.CrisprDesign)
            .options(db.orm.joinedload(models.CrisprDesign.cell_lines))
            .options(db.orm.joinedload(models.CrisprDesign.uniprot_metadata))
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
        ids = []
        [ids.extend([line.id for line in design.cell_lines]) for design in query.all()]

        # retain only the cell_line_ids that were included in the URL (if any)
        if len(included_ids):
            ids = list(set(ids).intersection(included_ids))

        lines = (
            flask.current_app.Session.query(models.CellLine)
            .options(
                db.orm.joinedload(models.CellLine.crispr_design, innerjoin=True),
                db.orm.joinedload(models.CellLine.facs_dataset),
                db.orm.joinedload(models.CellLine.sequencing_dataset),
                db.orm.joinedload(models.CellLine.annotation),
                (
                    db.orm.joinedload(models.CellLine.fovs)
                    .joinedload(models.MicroscopyFOV.annotation, innerjoin=True)
                ),
            )
            .filter(models.CellLine.id.in_(ids))
            .all()
        )

        # limit the number of lines in dev mode (to speed things up)
        if flask.current_app.config['ENV'] == 'dev':
            lines = lines[::1]

        payload = [payloads.cell_line_payload(line, optional_fields) for line in lines]
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

    def get(self, cell_line_id):
        ...

    def put(self, cell_line_id):
        ...

    def delete(self, cell_line_id):
        ...


class CellLine(CellLineResource):

    def get(self, cell_line_id):
        line = self.get_cell_line(cell_line_id)
        optional_fields, error = self.parse_listlike_arg('fields', allowed_values=['best-fov'])
        if error:
            return error
        payload = payloads.cell_line_payload(line, optional_fields)
        return flask.jsonify(payload)


class FACSDataset(CellLineResource):

    def get(self, cell_line_id):
        line = self.get_cell_line(cell_line_id)
        if not line.facs_dataset:
            return flask.abort(404)
        payload = payloads.facs_payload(line.facs_dataset)
        return flask.jsonify(payload)


class CellLineFOVs(CellLineResource):
    '''
    The MicroscopyFOVs associated with a cell line
    '''
    def get(self, cell_line_id):

        line = self.get_cell_line(cell_line_id)
        if not line.fovs:
            return flask.abort(404, 'There are no FOVs associated with the cell line')

        optional_fields, error = self.parse_listlike_arg(
            name='fields', allowed_values=['rois', 'thumbnails']
        )
        if error:
            return error

        payload = [payloads.fov_payload(fov, optional_fields) for fov in line.fovs]

        # sort by FOV score (unscored FOVs last)
        payload = sorted(payload, key=lambda row: row['metadata'].get('score') or -2)[::-1]
        return flask.jsonify(payload)


class CellLinePulldown(CellLineResource):
    '''
    The mass spec pulldown and associated hits for a given cell line
    Note that there is always one 'good' pulldown per cell line,
    from the perspective of the API and the public-facing frontend
    (though there may be multiple pulldowns per cell line in the database)
    '''
    def get(self, cell_line_id):
        line = self.get_cell_line(cell_line_id)
        if not line.pulldowns:
            return flask.abort(
                404, 'There are no pulldowns associated with cell line %d' % cell_line_id
            )

        # TODO: logic to determine which pulldown is the 'good' one
        # for now, we take the first pulldown with hits
        pulldown_id = line.pulldowns[0].id
        if len(line.pulldowns) > 1:
            for pulldown in line.pulldowns:
                if pulldown.hits:
                    pulldown_id = pulldown.id
                    break

        pulldown = (
            flask.current_app.Session.query(models.MassSpecPulldown)
            .options(
                db.orm.joinedload(models.MassSpecPulldown.hits)
                .joinedload(models.MassSpecHit.protein_group)
                .joinedload(models.MassSpecProteinGroup.crispr_designs),
                db.orm.joinedload(models.MassSpecPulldown.hits)
                .joinedload(models.MassSpecHit.protein_group)
                .joinedload(models.MassSpecProteinGroup.uniprot_metadata),
            )
            .filter(models.MassSpecPulldown.id == pulldown_id)
            .one()
        )

        if not pulldown.hits:
            return flask.abort(
                404, 'No pulldown with hits found for cell line %s' % cell_line_id
            )

        payload = payloads.pulldown_payload(pulldown)
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
        dst_root = flask.current_app.config.get('OPENCELL_MICROSCOPY_DIRPATH')
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

    def get(self, roi_id, kind, channel):
        '''
        Get the image data for a given ROI

        kind : the kind of image data
            Currently, only 'crop' is implemented (returns a z-stack as a tiled JPG)
        channel : one of '405', '488', or 'rgb'
            Note that 'rgb' does not work for kind='crop',
            because z-stacks are constructed separately for each channel
        '''
        if kind != 'crop':
            flask.abort(404, 'Invalid kind')

        roi = (
            flask.current_app.Session.query(models.MicroscopyFOVROI)
            .filter(models.MicroscopyFOVROI.id == roi_id)
            .one_or_none()
        )
        if not roi:
            flask.abort(404, 'Invalid roi_id')

        processor = FOVProcessor.from_database(roi.fov)
        filepath = processor.dst_filepath(
            dst_root=flask.current_app.config.get('OPENCELL_MICROSCOPY_DIRPATH'),
            roi_id=roi_id,
            channel=channel,
            kind='crop',
            ext='jpg'
        )

        file = flask.send_file(
            open(filepath, 'rb'),
            as_attachment=True,
            attachment_filename=filepath.split(os.sep)[-1]
        )
        return file


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
