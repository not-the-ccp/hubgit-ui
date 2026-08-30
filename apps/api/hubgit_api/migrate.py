"""Alembic runner with a one-time baseline for pre-migration alpha databases."""

from __future__ import annotations

import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

from .config import Settings


def _config(settings: Settings) -> Config:
    config = Config()
    config.set_main_option(
        "script_location", str(Path(__file__).with_name("migrations"))
    )
    config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
    return config


async def _table_names(database_url: str) -> set[str]:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            return set(
                await connection.run_sync(
                    lambda sync_connection: inspect(sync_connection).get_table_names()
                )
            )
    finally:
        await engine.dispose()


def upgrade_database(settings: Settings, revision: str = "head") -> None:
    """Upgrade a database and recognize the schema shipped before Alembic."""
    config = _config(settings)
    tables = asyncio.run(_table_names(settings.database_url))
    if "users" in tables and "alembic_version" not in tables:
        baseline = (
            "0002_github"
            if {"oauth_states", "provider_identities"}.issubset(tables)
            else "0001_legacy"
        )
        command.stamp(config, baseline)
    command.upgrade(config, revision)
