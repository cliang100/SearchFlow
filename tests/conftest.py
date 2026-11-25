import os

# Must be set before the app modules read their configuration.
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL", "postgresql://searchflow:test@localhost:55432/searchflow_test")
os.environ["REDIS_URL"] = os.getenv("TEST_REDIS_URL", "redis://localhost:56379/15")

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from src.searchflow import config
from src.searchflow.database.connection import engine
from src.searchflow.search import search


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    command.upgrade(Config("alembic.ini"), "head")


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE documents, search_logs RESTART IDENTITY"))
    search._engine = None
    monkeypatch.setattr(config, "ADMIN_TOKEN", "")
    monkeypatch.setattr(config, "CRAWL_DELAY", 0.0)
