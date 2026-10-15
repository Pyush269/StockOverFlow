import itertools
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    raise pytest.UsageError("Set TEST_DATABASE_URL to the isolated stockflow_test PostgreSQL database; see README.md")
test_url = make_url(TEST_DATABASE_URL)
if test_url.drivername != "postgresql+psycopg" or test_url.database != "stockflow_test":
    raise pytest.UsageError("Refusing destructive fixtures: TEST_DATABASE_URL must use PostgreSQL database stockflow_test")
# Set before importing the app; never inherit the development DATABASE_URL.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from fastapi.testclient import TestClient
from app.config import Settings
from app.db import build_engine
from app.main import create_app

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def run_migration(engine, operation, revision=None):
    configuration = Config(str(BACKEND_ROOT / "alembic.ini"))
    with engine.begin() as connection:
        configuration.attributes["connection"] = connection
        if revision is None:
            operation(configuration)
        else:
            operation(configuration, revision)


@pytest.fixture(scope="session")
def engine():
    database_engine = build_engine(TEST_DATABASE_URL)
    run_migration(database_engine, command.upgrade, "head")
    yield database_engine
    database_engine.dispose()


@pytest.fixture(autouse=True)
def clean_database(engine):
    # Only the explicitly checked disposable test DB may be truncated.
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE stock_movements, products RESTART IDENTITY"))
    yield
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE stock_movements, products RESTART IDENTITY"))


@pytest.fixture
def application(engine):
    settings = Settings(database_url=TEST_DATABASE_URL, cors_origins=["http://localhost:5173"], _env_file=None)
    return create_app(settings, engine=engine)


@pytest.fixture
def client(application):
    with TestClient(application) as test_client:
        yield test_client


@pytest.fixture
def product_factory(client):
    identifiers = itertools.count(1)

    def create(**changes):
        payload = {"sku": f"SKU-{next(identifiers)}", "name": "USB-C Hub", "category": "Electronics", "unit_price": "19.99", "reorder_level": 5}
        payload.update(changes)
        response = client.post("/api/products", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    return create
