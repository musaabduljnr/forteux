from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.config import get_settings


def test_migration_upgrade_and_downgrade(tmp_path, monkeypatch):
    database_path = tmp_path / "migration.sqlite"
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    get_settings.cache_clear()
    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "migrations"))
    try:
        command.upgrade(config, "head")
        engine = create_engine(f"sqlite:///{database_path}")
        assert {
            "users",
            "tenants",
            "memberships",
            "projects",
            "audits",
            "screen_assets",
            "audit_screens",
            "analysis_jobs",
            "findings",
            "audit_prompts",
            "prompt_versions",
            "knowledge_documents",
            "document_versions",
            "knowledge_chunks",
            "finding_evidence",
            "deletion_tasks",
        }.issubset(inspect(engine).get_table_names())
        engine.dispose()

        command.downgrade(config, "base")
        engine = create_engine(f"sqlite:///{database_path}")
        assert "projects" not in inspect(engine).get_table_names()
        engine.dispose()
    finally:
        get_settings.cache_clear()
