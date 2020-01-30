
import os
import sys


class Config(object):
    '''
    Common configuration
    '''

    APP_DIR = os.path.abspath(os.path.dirname(__file__))

    # project root is two directory levels up
    PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir, os.pardir))

    CORS_ORIGINS = [
        'http://localhost:8000',
        'http://localhost:8080',
        'http://localhost:8081',
        'http://localhost:8082',
        'http://localhost:8083',
        'http://cap.czbiohub.org:8001',
        'http://opencell.czbiohub.org',
    ]


class DevConfig(Config):
    '''
    Development configuration
    '''

    ENV = 'dev'
    DEBUG = True

    # settings for flask-caching (timeout time in seconds)
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300

    DB_CREDENTIALS_FILEPATH = os.path.join(Config.PROJECT_ROOT, 'test_credentials.json')


class ProdConfig(Config):
    '''
    Production configuration
    '''

    ENV = 'prod'
    # TODO: determine how to retrieve database credentials
    # TODO: figure out caching
