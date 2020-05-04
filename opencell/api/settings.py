
import os
import sys


class Config(object):
    '''
    Common configuration
    '''
    APP_DIR = os.path.abspath(os.path.dirname(__file__))

    # project root is two directory levels up
    PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir, os.pardir))


class DevConfig(Config):

    ENV = 'dev'
    DEBUG = True

    # settings for flask-caching (timeout time in seconds)
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300

    DB_CREDENTIALS_FILEPATH = os.path.join(Config.PROJECT_ROOT, 'db-credentials-dev.json')

    # the mountpoint of the ML_group ESS partition (assumes a mac)
    OPENCELL_MICROSCOPY_DIRPATH = os.path.join(os.sep, 'Volumes', 'ml_group', 'opencell-microscopy')

    CORS_ORIGINS = [
        'http://localhost:8080',
    ]


class ProdConfig(Config):

    # TODO: determine how to retrieve database credentials
    # TODO: figure out caching

    ENV = 'prod'
    DEBUG = False

    DB_CREDENTIALS_FILEPATH = os.path.join(Config.PROJECT_ROOT, 'db-credentials-docker.json')

    # the mount point of the ML_group ESS partition in the docker container
    OPENCELL_MICROSCOPY_DIRPATH = os.path.join(os.sep, 'gpfsML', 'ML_group', 'opencell-microscopy')
