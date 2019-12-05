
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
from opencell.database import utils
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



def create_app():

    app = Flask(__name__)
    app.config.from_object(settings.DevConfig)
    CORS(app, origins=app.config['CORS_ORIGINS'])

    cache.init_app(app)

    api = Api()
    api.add_resource(resources.Plates, '/plates')
    api.add_resource(resources.Plate, '/plates/<string:plate_id>')
    api.add_resource(resources.Electroporations, '/electroporations')
    api.add_resource(resources.PolyclonalLines, '/polyclonallines')
    api.add_resource(resources.FACSHistograms, '/facshistograms/<int:cell_line_id>')
    api.init_app(app)


    url = utils.url_from_credentials(
        app.config['DB_CREDENTIALS_FILEPATH'])

    # create an instance of sqlalchemy's scoped_session registry
    app.Session = create_session_registry(url)

    # required to close the session instance when a request is completed
    @app.teardown_appcontext
    def remove_session(error=None):
        app.Session.remove()

    app.run(debug=True)


if __name__=='__main__':
    create_app()
    