
import argparse
import sqlalchemy as sa
from flask import Flask
from flask_cors import CORS
from flask_restful import Api
from sqlalchemy import create_engine
from sqlalchemy.orm import (
    scoped_session,
    sessionmaker
)

from opencell.api import resources
from opencell.api import settings
from opencell.database import models, utils
from opencell.api.cache import cache


def create_session_registry(url):
    '''
    Create an sqlalchemy scoped session registry

    This registry is the `Session` object below.
    Note that, although this object is a 'registry' that manages session instances,
    it also proxies session-bound methods (like query), so that the registry
    itself can be treated like a session instance, enabling lines like
    `Session.query(models.SomeModel)`
    '''
    engine = create_engine(url)
    session_factory = sessionmaker(bind=engine)
    Session = scoped_session(session_factory)

    cell_line_metadata_view = sa.Table(
        'cell_line_metadata',
        models.Base.metadata,
        autoload=True,
        autoload_with=engine)

    fov_rank_view = sa.Table(
        'fov_rank',
        models.Base.metadata,
        autoload=True,
        autoload_with=engine)

    views = {
        'cell_line_metadata': cell_line_metadata_view,
        'fov_rank': fov_rank_view
    }

    return Session, views


def create_app(args):

    app = Flask(__name__)
    app.config.from_object(settings.DevConfig)
    CORS(app, origins=app.config['CORS_ORIGINS'])

    cache.init_app(app)

    api = Api()
    api.add_resource(resources.Plates, '/plates')
    api.add_resource(resources.Plate, '/plates/<string:plate_id>/')

    api.add_resource(resources.PolyclonalLines, '/lines')
    api.add_resource(resources.PolyclonalLine, '/lines/<int:cell_line_id>')
    api.add_resource(resources.CellLineAnnotation, '/annotations/<int:cell_line_id>')

    api.add_resource(resources.MicroscopyFOV, '/fovs/<string:channel>/<string:kind>/<int:fov_id>')
    api.add_resource(resources.MicroscopyFOVROI, '/rois/<string:channel>/<string:kind>/<int:roi_id>')
    api.add_resource(resources.MicroscopyFOVAnnotation, '/fov_annotations/<int:fov_id>')

    api.init_app(app)

    if args.credentials:
        credentials = args.credentials
    else:
        credentials = app.config['DB_CREDENTIALS_FILEPATH']

    if args.opencell_microscopy_root:
        app.config['opencell_microscopy_root'] = args.opencell_microscopy_root

    # create an instance of sqlalchemy's scoped_session registry
    url = utils.url_from_credentials(credentials)
    app.Session, app.views = create_session_registry(url)

    # required to close the session instance when a request is completed
    @app.teardown_appcontext
    def remove_session(error=None):
        app.Session.remove()

    app.run(host='0.0.0.0', debug=True)


def parse_args():

    parser = argparse.ArgumentParser()
    parser.add_argument('--credentials', dest='credentials')
    parser.add_argument('--opencell-microscopy-root', dest='opencell_microscopy_root')

    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    create_app(args)
