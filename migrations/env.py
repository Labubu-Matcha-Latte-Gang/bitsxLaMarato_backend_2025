from __future__ import annotations

import logging
import os
from logging.config import fileConfig
from pathlib import Path
import sys

from alembic import context
from sqlalchemy import engine_from_config, pool

# AÑADIDO: meter el directorio raíz del proyecto en sys.path
BASE_DIR = Path(__file__).resolve().parent.parent  # /app
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# this is the Alembic Config object, which provides access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name and os.path.exists(config.config_file_name):
    fileConfig(config.config_file_name)
else:
    logging.basicConfig()

target_metadata = None


def _get_app_and_metadata():
    """
    Fetch SQLAlchemy metadata from the Flask app's db instance.
    """
    global target_metadata
    # Import inside the function to avoid circular imports on Alembic startup.
    from app import app          # ahora 'app' se puede encontrar
    from db import db            # idem

    if target_metadata is None:
        with app.app_context():
            target_metadata = db.metadata
    return app, target_metadata



def run_migrations_offline():
    """
    Run migrations in 'offline' mode.
    """
    app, metadata = _get_app_and_metadata()
    url = app.config.get("SQLALCHEMY_DATABASE_URI")
    context.configure(
        url=url,
        target_metadata=metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """
    Run migrations in 'online' mode.
    """
    app, metadata = _get_app_and_metadata()
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        url=app.config["SQLALCHEMY_DATABASE_URI"],
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
