from logging.config import fileConfig

from alembic import context

from app.config import Settings
from app.db import Base, build_engine
from app import models  # noqa: F401 -- registers models in Alembic metadata

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name, disable_existing_loggers=False)
target_metadata = Base.metadata


def configure(connection):
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True, compare_server_default=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    url = config.get_main_option("sqlalchemy.url") or Settings().database_url
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()
elif config.attributes.get("connection") is not None:
    configure(config.attributes["connection"])
else:
    url = config.get_main_option("sqlalchemy.url") or Settings().database_url
    engine = build_engine(url)
    try:
        with engine.connect() as connection:
            configure(connection)
    finally:
        engine.dispose()
