
import os
import sys


def get_config(mode):

    if mode == 'dev':
        config = DevConfig
    elif mode == 'test':
        config = TestConfig
    elif mode == 'staging':
        config = StagingConfig
    elif mode == 'prod':
        config = ProdConfig
    elif mode == 'remote-prod':
        config = RemoteProdConfig
    elif mode == 'aws':
        config = AWSConfig
    else:
        raise ValueError('Invalid value %s for mode' % mode)
    return config


class Config(object):
    '''
    Common configuration
    '''
    APP_DIR = os.path.abspath(os.path.dirname(__file__))

    # project root is two directory levels up
    PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir, os.pardir))

    # this string identifies the mass-spec clustering results to display
    # (used in cytoscape_networks.construct_compound_nodes)
    MS_CLUSTERING_TYPE = 'primary:mcl_i3.0_haircut:keepcore_subcluster:mcl_hybrid_stoichs_2.0_2'


class DevConfig(Config):

    ENV = 'dev'
    DEBUG = True

    # settings for flask-caching (timeout time in seconds)
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300

    DB_CREDENTIALS_FILEPATH = os.path.join(Config.PROJECT_ROOT, 'db-credentials-dev.json')

    PLATE_MICROSCOPY_DIR = '/Volumes/ml_group/PlateMicroscopy/'
    PLATE_MICROSCOPY_CACHE_DIR = '/Volumes/ml_group/opencell-microscopy/cache/'
    RAW_PIPELINE_MICROSCOPY_DIR = '/Volumes/ml_group/raw-pipeline-microscopy/'

    # the mountpoint of the ML_group ESS partition (assumes a mac)
    OPENCELL_MICROSCOPY_DIR = '/Volumes/ml_group/opencell-microscopy/'

    CORS_ORIGINS = [
        'http://localhost:8080',
    ]


class TestConfig(Config):

    ENV = 'test'
    DEBUG = True

    # settings for flask-caching (timeout time in seconds)
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300

    DB_CREDENTIALS_FILEPATH = os.path.join(Config.PROJECT_ROOT, 'db-credentials-test.json')

    PLATE_MICROSCOPY_DIR = '/Users/keith.cheveralls/opencell-test/PlateMicroscopy/'
    PLATE_MICROSCOPY_CACHE_DIR = '/Users/keith.cheveralls/opencell-test/opencell-microscopy/cache/'
    RAW_PIPELINE_MICROSCOPY_DIR = '/Users/keith.cheveralls/opencell-test/raw-pipeline-microscopy/'
    OPENCELL_MICROSCOPY_DIR = '/Users/keith.cheveralls/opencell-test/opencell-microscopy/'

    CORS_ORIGINS = [
        'http://localhost:8080',
    ]


class StagingConfig(Config):

    ENV = 'staging'
    DEBUG = False

    DB_CREDENTIALS_FILEPATH = os.path.join(Config.PROJECT_ROOT, 'db-credentials-docker.json')

    PLATE_MICROSCOPY_DIR = '/gpfsML/ML_group/PlateMicroscopy/'
    RAW_PIPELINE_MICROSCOPY_DIR = '/gpfsML/ML_group/raw-pipeline-microscopy/'
    OPENCELL_MICROSCOPY_DIR = '/gpfsML/ML_group/opencell-microscopy-staging/'


class ProdConfig(Config):

    # TODO: determine how to retrieve database credentials
    # TODO: figure out caching

    ENV = 'prod'
    DEBUG = False

    DB_CREDENTIALS_FILEPATH = os.path.join(Config.PROJECT_ROOT, 'db-credentials-docker.json')

    PLATE_MICROSCOPY_DIR = '/gpfsML/ML_group/PlateMicroscopy/'
    PLATE_MICROSCOPY_CACHE_DIR = '/gpfsML/ML_group/opencell-microscopy/cache/'
    RAW_PIPELINE_MICROSCOPY_DIR = '/gpfsML/ML_group/raw-pipeline-microscopy/'
    OPENCELL_MICROSCOPY_DIR = '/gpfsML/ML_group/opencell-microscopy/'


class RemoteProdConfig(Config):

    ENV = 'prod'
    DEBUG = False

    DB_CREDENTIALS_FILEPATH = os.path.join(Config.PROJECT_ROOT, 'db-credentials-cap.json')

    PLATE_MICROSCOPY_DIR = '/Volumes/ml_group/PlateMicroscopy/'
    PLATE_MICROSCOPY_CACHE_DIR = '/Volumes/ml_group/opencell-microscopy/cache/'
    RAW_PIPELINE_MICROSCOPY_DIR = '/Volumes/ml_group/raw-pipeline-microscopy/'
    OPENCELL_MICROSCOPY_DIR = '/Volumes/ml_group/opencell-microscopy/'
    CORS_ORIGINS = [
        'http://localhost:8080',
    ]


class AWSConfig(Config):

    ENV = 'prod'
    DEBUG = False

    DB_CREDENTIALS_FILEPATH = '/home/ubuntu/db-credentials.json'
    OPENCELL_MICROSCOPY_DIR = 'http://opencell.czbiohub.org/data/'
