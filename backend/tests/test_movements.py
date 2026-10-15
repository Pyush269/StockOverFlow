from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from time import monotonic, sleep

import pytest
from sqlalchemy import event, select, text

from app.models import MAX_QUANTITY, Product, StockMovement


def move(client, product_id, kind, quantity, **extra):
    return client.post(f"/api/products/{product_id}/movements", json={"movement_type": kind, "quantity": quantity, **extra})


def test_receive_issue_reject_and_history(client, product_factory):
    product = product_factory()
    product_id = product["id"]
    received = move(client, product_id, "IN", 10, note="Opening stock")
    assert received.status_code == 201
    assert received.json()["product"]["quantity"] == 10
    issued = move(client, product_id, "OUT", 3, note="Customer order")
    assert issued.status_code == 201
    assert issued.json()["product"]["quantity"] == 7
    rejected = move(client, product_id, "OUT", 8)
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "insufficient_stock"
    assert client.get(f"/api/products/{product_id}").json()["quantity"] == 7
    history = client.get(f"/api/products/{product_id}/movements", params={"limit": 1}).json()
    assert history["total"] == 2
    assert history["items"][0]["movement_type"] == "OUT"
    assert history["items"][0]["note"] == "Customer order"


@pytest.mark.parametrize("quantity", [0, -1, 1.5, True, "3", MAX_QUANTITY + 1])
def test_invalid_movement_quantities(client, product_factory, quantity):
    product = product_factory()
    assert move(client, product["id"], "IN", quantity).status_code == 422
    assert client.get(f'/api/products/{product["id"]}/movements').json()["total"] == 0


def test_invalid_movement_type(client, product_factory):
    product = product_factory()
    assert move(client, product["id"], "ADJUST", 1).status_code == 422


def test_quantity_overflow_is_controlled_conflict(client, product_factory):
    product = product_factory()
    assert move(client, product["id"], "IN", MAX_QUANTITY).status_code == 201
    response = move(client, product["id"], "IN", 1)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "stock_limit_exceeded"
    assert client.get(f'/api/products/{product["id"]}').json()["quantity"] == MAX_QUANTITY
    assert client.get(f'/api/products/{product["id"]}/movements').json()["total"] == 1


@pytest.mark.integration
def test_failed_ledger_insert_rolls_back_quantity(client, product_factory, engine):
    product = product_factory()
    product_id = product["id"]
    assert move(client, product_id, "IN", 10).status_code == 201
    observed_pending_quantity = []

    def fail_after_insert(mapper, connection, target):
        observed_pending_quantity.append(connection.scalar(select(Product.quantity).where(Product.id == product_id)))
        raise RuntimeError("Injected failure before transaction commit")

    event.listen(StockMovement, "after_insert", fail_after_insert)
    try:
        with pytest.raises(RuntimeError, match="Injected failure"):
            move(client, product_id, "IN", 5)
    finally:
        event.remove(StockMovement, "after_insert", fail_after_insert)
    assert observed_pending_quantity == [15]
    assert client.get(f"/api/products/{product_id}").json()["quantity"] == 10
    assert client.get(f"/api/products/{product_id}/movements").json()["total"] == 1


@pytest.mark.integration
def test_concurrent_issues_wait_for_lock_and_cannot_oversell(client, product_factory, engine):
    product = product_factory()
    product_id = product["id"]
    assert move(client, product_id, "IN", 7).status_code == 201
    start = Barrier(2)

    def issue():
        start.wait(timeout=5)
        return move(client, product_id, "OUT", 5)

    with ThreadPoolExecutor(max_workers=2) as executor:
        # Hold the product first so both requests must actually contend for it.
        with engine.begin() as holder:
            holder.execute(select(Product.id).where(Product.id == product_id).with_for_update())
            pending = [executor.submit(issue), executor.submit(issue)]
            deadline = monotonic() + 5
            waiting = 0
            while monotonic() < deadline:
                with engine.connect() as observer:
                    waiting = observer.scalar(text("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND wait_event_type = 'Lock' AND query LIKE '%FOR UPDATE%' AND pid <> pg_backend_pid()"))
                if waiting >= 2:
                    break
                sleep(0.02)
            assert waiting >= 2, "Both requests should wait for the PostgreSQL row lock"
        results = [future.result(timeout=10) for future in pending]
    assert sorted(response.status_code for response in results) == [201, 409]
    assert client.get(f"/api/products/{product_id}").json()["quantity"] == 2
    history = client.get(f"/api/products/{product_id}/movements").json()
    assert history["total"] == 2
    assert sum(item["movement_type"] == "OUT" for item in history["items"]) == 1
