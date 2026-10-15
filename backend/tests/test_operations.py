from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.config import Settings
from app.main import create_app


def test_health_ready_docs_and_metrics(client):
    assert client.get("/health").json() == {"status": "UP"}
    assert client.get("/ready").json() == {"status": "READY"}
    assert client.get("/docs").status_code == 200
    assert client.get("/api/dashboard").status_code == 200
    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "http_requests_total" in metrics.text
    assert "text/plain" in metrics.headers["content-type"]


def test_health_remains_up_when_database_unreachable():
    settings = Settings(database_url="postgresql+psycopg://unavailable:unavailable@127.0.0.1:1/unavailable", _env_file=None)
    with TestClient(create_app(settings)) as offline:
        assert offline.get("/health").status_code == 200
        response = offline.get("/ready")
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "database_not_ready"
        assert "unavailable@" not in response.text


def test_stale_migration_revision_is_not_ready(client, engine):
    with engine.begin() as connection:
        connection.execute(text("UPDATE alembic_version SET version_num = 'stale_revision'"))
    try:
        response = client.get("/ready")
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "schema_not_ready"
        assert client.get("/health").status_code == 200
    finally:
        with engine.begin() as connection:
            connection.execute(text("UPDATE alembic_version SET version_num = '0001_inventory'"))


def test_empty_dashboard_has_zero_totals(client):
    data = client.get("/api/dashboard").json()
    assert data["total_products"] == data["total_units"] == data["low_stock_count"] == 0
    assert Decimal(data["inventory_value"]) == 0
    assert data["low_stock_products"] == data["recent_movements"] == []


def test_dashboard_totals_include_threshold_boundary(client, product_factory):
    low = product_factory(sku="LOW", name="Low stock", unit_price="2.50", reorder_level=3)
    full = product_factory(sku="FULL", unit_price="10.00", reorder_level=2)
    for product, quantity in [(low, 3), (full, 8)]:
        assert client.post(f'/api/products/{product["id"]}/movements', json={"movement_type": "IN", "quantity": quantity}).status_code == 201
    data = client.get("/api/dashboard").json()
    assert data["total_products"] == 2
    assert data["total_units"] == 11
    assert data["low_stock_count"] == 1
    assert Decimal(data["inventory_value"]) == Decimal("87.50")
    assert data["low_stock_products"][0]["sku"] == "LOW"
    assert {item["product_sku"] for item in data["recent_movements"]} == {"LOW", "FULL"}


def test_cors_allows_only_configured_development_origin(client):
    allowed = client.options("/api/products", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"})
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    denied = client.options("/api/products", headers={"Origin": "https://untrusted.example", "Access-Control-Request-Method": "POST"})
    assert denied.status_code == 400
    assert "access-control-allow-origin" not in denied.headers
