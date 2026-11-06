from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.config.settings import settings


def _migration_config() -> Config:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    return config


def test_migrations_create_fresh_schema_and_preserve_existing_data(tmp_path):
    original_database_url = settings.database_url
    try:
        fresh_db = tmp_path / "fresh.db"
        settings.database_url = f"sqlite:///{fresh_db.as_posix()}"
        command.upgrade(_migration_config(), "head")

        fresh_engine = create_engine(settings.database_url)
        assert {
            "users",
            "projects",
            "bugs",
            "bug_analysis",
            "test_cases",
            "bug_attachments",
            "project_uploads",
            "source_chunks",
            "test_execution_history",
        } <= set(inspect(fresh_engine).get_table_names())
        assert {
            "project_id",
            "upload_id",
            "source_key",
        } <= {
            column["name"]
            for column in inspect(fresh_engine).get_columns("test_cases")
        }
        fresh_engine.dispose()

        legacy_db = tmp_path / "legacy.db"
        legacy_url = f"sqlite:///{legacy_db.as_posix()}"
        legacy_engine = create_engine(legacy_url)

        settings.database_url = legacy_url
        command.upgrade(_migration_config(), "657954b6d145")
        with legacy_engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO users "
                    "(name, email, password_hash, role, created_at) "
                    "VALUES ('Existing', 'existing@example.test', 'hash', "
                    "'DEVELOPER', CURRENT_TIMESTAMP)"
                )
            )
            connection.execute(text("DROP TABLE alembic_version"))

        command.upgrade(_migration_config(), "head")
        with legacy_engine.connect() as connection:
            email = connection.execute(
                text(
                    "SELECT email FROM users "
                    "WHERE email = 'existing@example.test'"
                )
            ).scalar_one()
            version = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            test_case_columns = {
                column["name"]
                for column in inspect(connection).get_columns("test_cases")
            }

        assert email == "existing@example.test"
        assert version == "a1b2c3d4e5f6"
        assert {"project_id", "upload_id", "source_key"} <= test_case_columns
        legacy_engine.dispose()
    finally:
        settings.database_url = original_database_url
