
import os
import sys
from alembic import context
from logging.config import fileConfig
from sqlalchemy import create_engine

from opencell.database import models
from opencell.database import utils as opencell_utils
from opencell.api import settings as opencell_settings


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
target_metadata = models.Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")


def get_uri():
    '''
    An opencell-specific method to get the database URI from alembic's `x` CLI argument

    This method implies or assumes that alembic commands are of the following form:
    `alembic -x mode=$mode upgrade head`
    where $mode is one of the modes defined in opencell.api.settings

    '''
    mode = context.get_x_argument(as_dictionary=True).get('mode')
    opencell_config = opencell_settings.get_config(mode)
    return opencell_utils.url_from_credentials(opencell_config.DB_CREDENTIALS_FILEPATH)


def run_migrations_offline():
    """Run migrations in 'offline' mode.
    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    context.configure(
        url=get_uri(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.
    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = create_engine(get_uri())
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, compare_type=True
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
