import os
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
    return Session


def create_app(config=None):

    if not config:
        config = settings.get_config(os.environ.get('MODE'))

    app = Flask(__name__)
    app.config.from_object(config)
    if app.config.get('CORS_ORIGINS'):
        CORS(app, origins=app.config['CORS_ORIGINS'])

    cache.init_app(app)
    api = Api()

    # convenience endpoint to clear the cache
    api.add_resource(resources.ClearCache, '/clear_cache')

    # search by gene name, ENSG ID, etc
    api.add_resource(resources.Search, '/search/<string:search_string>')

    # plate designs
    api.add_resource(resources.Plate, '/plates/<string:plate_id>')

    # cell line metadata
    api.add_resource(resources.CellLines, '/lines')
    api.add_resource(resources.CellLine, '/lines/<int:cell_line_id>')

    # the metadata for opencell targets that interact with an ensg_id
    api.add_resource(resources.InteractorTargets, '/interactors/<string:ensg_id>')

    # the cytoscape network for a given interactor (identified by ensg_id)
    api.add_resource(resources.InteractorNetwork, '/interactors/<string:ensg_id>/network')

    # cell-line-related endpoints
    api.add_resource(resources.FACSDataset, '/lines/<int:cell_line_id>/facs')
    api.add_resource(resources.MicroscopyFOVMetadata, '/lines/<int:cell_line_id>/fovs')
    api.add_resource(resources.CellLineAnnotation, '/lines/<int:cell_line_id>/annotation')

    # pulldown-related endpoints
    api.add_resource(resources.PulldownHits, '/pulldowns/<int:pulldown_id>/hits')
    api.add_resource(resources.PulldownClusters, '/pulldowns/<int:pulldown_id>/clusters')
    api.add_resource(
        resources.PulldownNetwork, '/pulldowns/<int:pulldown_id>/network'
    )
    api.add_resource(
        resources.SavedPulldownNetwork, '/pulldowns/<int:pulldown_id>/saved_network'
    )

    # FOV and ROI image data (z-stacks and z-projections)
    api.add_resource(
        resources.MicroscopyFOV, '/fovs/<int:fov_id>/<string:kind>/<string:channel>'
    )
    api.add_resource(
        resources.MicroscopyFOVROI, '/rois/<int:roi_id>/<string:roi_kind>/<string:channel>'
    )

    # FOV annotations (always one annotation per FOV)
    api.add_resource(resources.MicroscopyFOVAnnotation, '/fovs/<int:fov_id>/annotation')

    api.init_app(app)

    # create an instance of sqlalchemy's scoped_session registry
    url = utils.url_from_credentials(app.config['DB_CREDENTIALS_FILEPATH'])
    app.Session = create_session_registry(url)

    # close the session instance when a request is completed
    @app.teardown_appcontext
    def remove_session(error=None):
        app.Session.remove()

    return app


def parse_args():
    '''
    CLI args for running the app via app.run (i.e., in non-production environments)
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', dest='mode', required=True)
    parser.add_argument('--credentials', dest='credentials_filepath')
    parser.add_argument('--opencell-microscopy-dir', dest='opencell_microscopy_dir')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    config = settings.get_config(args.mode)

    if args.credentials_filepath:
        config.DB_CREDENTIALS_FILEPATH = args.credentials_filepath

    if args.opencell_microscopy_dir:
        config.OPENCELL_MICROSCOPY_DIR = args.opencell_microscopy_dir

    app = create_app(config)
    app.run(host='0.0.0.0', debug=True)
