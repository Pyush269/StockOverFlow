from decimal import Decimal

import pytest


def test_create_product_normalizes_sku_and_starts_empty(client):
    response = client.post("/api/products", json={"sku": "  cable-01 ", "name": " USB cable ", "unit_price": "12.30"})
    assert response.status_code == 201
    data = response.json()
    assert data["sku"] == "CABLE-01"
    assert data["name"] == "USB cable"
    assert data["quantity"] == 0
    assert Decimal(data["unit_price"]) == Decimal("12.30")
    assert data["created_at"].endswith("Z")


def test_duplicate_sku_is_conflict(client, product_factory):
    product_factory(sku="USB-01")
    response = client.post("/api/products", json={"sku": "usb-01", "name": "Duplicate"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "duplicate_sku"
    assert client.get("/api/products").json()["total"] == 1


def test_list_detail_filter_and_pagination(client, product_factory):
    first = product_factory(sku="HUB-01", name="Travel hub", category="Electronics")
    product_factory(sku="DESK-01", name="Standing desk", category="Office")
    product_factory(sku="HUB-02", name="Desktop hub", category="Electronics")
    page = client.get("/api/products", params={"q": "hub", "category": "electronics", "limit": 1, "offset": 1}).json()
    assert page["total"] == 2
    assert len(page["items"]) == 1
    assert page["items"][0]["sku"] == "HUB-02"
    assert client.get(f'/api/products/{first["id"]}').json()["name"] == "Travel hub"


def test_search_treats_sql_wildcards_as_literal(client, product_factory):
    product_factory(name="100% cotton")
    product_factory(name="Cotton shirt")
    assert client.get("/api/products", params={"q": "%"}).json()["total"] == 1


def test_put_replaces_metadata_without_changing_stock(client, product_factory):
    product = product_factory()
    client.post(f'/api/products/{product["id"]}/movements', json={"movement_type": "IN", "quantity": 10})
    response = client.put(f'/api/products/{product["id"]}', json={"sku": "UPDATED-01", "name": "Updated hub", "unit_price": "20.50", "category": "Adapters", "reorder_level": 3})
    assert response.status_code == 200
    assert response.json()["quantity"] == 10
    assert response.json()["sku"] == "UPDATED-01"
    assert Decimal(response.json()["unit_price"]) == Decimal("20.50")


def test_update_to_duplicate_sku_preserves_original(client, product_factory):
    first = product_factory(sku="FIRST")
    product_factory(sku="SECOND")
    response = client.put(f'/api/products/{first["id"]}', json={"sku": "second", "name": "Should roll back"})
    assert response.status_code == 409
    saved = client.get(f'/api/products/{first["id"]}').json()
    assert saved["sku"] == "FIRST"
    assert saved["name"] == first["name"]


def test_unused_product_delete_returns_empty_204(client, product_factory):
    product = product_factory()
    response = client.delete(f'/api/products/{product["id"]}')
    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f'/api/products/{product["id"]}').status_code == 404


def test_product_with_ledger_cannot_be_deleted(client, product_factory):
    product = product_factory()
    for kind in ["IN", "OUT"]:
        assert client.post(f'/api/products/{product["id"]}/movements', json={"movement_type": kind, "quantity": 1}).status_code == 201
    response = client.delete(f'/api/products/{product["id"]}')
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "product_has_history"
    assert client.get(f'/api/products/{product["id"]}/movements').json()["total"] == 2


@pytest.mark.parametrize("changes", [
    {"name": "   "}, {"sku": "bad sku"}, {"unit_price": "-0.01"},
    {"unit_price": "1.001"}, {"unit_price": "NaN"}, {"reorder_level": -1},
    {"reorder_level": True}, {"quantity": 100},
])
def test_invalid_product_fields_are_rejected(client, changes):
    response = client.post("/api/products", json={"sku": "VALID-01", "name": "Valid", **changes})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_put_cannot_bypass_ledger(client, product_factory):
    product = product_factory()
    response = client.put(f'/api/products/{product["id"]}', json={"sku": product["sku"], "name": "Attempt", "quantity": 500})
    assert response.status_code == 422
    assert client.get(f'/api/products/{product["id"]}').json()["quantity"] == 0


@pytest.mark.parametrize("method,path,payload", [
    ("GET", "/api/products/999999", None),
    ("PUT", "/api/products/999999", {"sku": "NEW", "name": "Missing"}),
    ("DELETE", "/api/products/999999", None),
    ("GET", "/api/products/999999/movements", None),
    ("POST", "/api/products/999999/movements", {"movement_type": "IN", "quantity": 1}),
])
def test_missing_product_is_404(client, method, path, payload):
    response = client.request(method, path, **({"json": payload} if payload is not None else {}))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "product_not_found"


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
def test_pagination_bounds(client, params):
    assert client.get("/api/products", params=params).status_code == 422
