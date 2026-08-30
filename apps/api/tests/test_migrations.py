import sqlite3

from alembic import command
from sqlalchemy import create_engine, inspect

from hubgit_api.config import Settings
from hubgit_api.migrate import _config, upgrade_database


def settings_for(path) -> Settings:
    return Settings(
        database_url=f"sqlite+aiosqlite:///{path}",
        seed_mock_user=False,
    )


def test_clean_database_migrates_to_schema_metadata(tmp_path):
    config = settings_for(tmp_path / "clean.db")
    upgrade_database(config)

    sync_engine = create_engine(config.database_url.replace("+aiosqlite", ""))
    with sync_engine.connect() as connection:
        inspector = inspect(connection)
        tables = set(inspector.get_table_names())
        password = next(
            column
            for column in inspector.get_columns("users")
            if column["name"] == "password_hash"
        )
        revision = connection.exec_driver_sql(
            "SELECT version_num FROM alembic_version"
        ).scalar_one()
    sync_engine.dispose()

    assert {"users", "oauth_states", "provider_identities"}.issubset(tables)
    assert password["nullable"] is True
    assert revision == "0002_github"
    command.check(_config(config))


def test_pre_alembic_database_is_baselined_and_upgraded_without_data_loss(tmp_path):
    database_path = tmp_path / "legacy.db"
    config = settings_for(database_path)
    upgrade_database(config, "0001_legacy")
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO users
                (login, display_name, email, password_hash, role, avatar_url, bio, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "legacy-user",
                "Legacy User",
                "legacy@example.test",
                "old-password-hash",
                "member",
                "",
                "",
                "2026-08-30 00:00:00",
            ),
        )
        connection.execute("DROP TABLE alembic_version")

    upgrade_database(config)

    with sqlite3.connect(database_path) as connection:
        login = connection.execute("SELECT login FROM users").fetchone()[0]
        revision = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()[0]
        oauth_table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='oauth_states'"
        ).fetchone()
    assert login == "legacy-user"
    assert revision == "0002_github"
    assert oauth_table == ("oauth_states",)
