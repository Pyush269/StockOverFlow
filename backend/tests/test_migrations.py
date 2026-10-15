import pytest
from alembic import command
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from conftest import run_migration


@pytest.mark.integration
def test_migration_upgrade_downgrade_and_model_parity(engine):
    try:
        run_migration(engine, command.downgrade, "base")
        assert "products" not in inspect(engine).get_table_names()
        assert "stock_movements" not in inspect(engine).get_table_names()
        run_migration(engine, command.upgrade, "head")
        assert {"products", "stock_movements"} <= set(inspect(engine).get_table_names())
        run_migration(engine, command.check)
    finally:
        run_migration(engine, command.upgrade, "head")


@pytest.mark.integration
def test_database_enforces_nonnegative_inventory(engine, product_factory):
    product = product_factory()
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(text("UPDATE products SET quantity = -1 WHERE id = :id"), {"id": product["id"]})


@pytest.mark.integration
@pytest.mark.parametrize("kind,quantity", [("IN", 0), ("BAD", 1)])
def test_database_enforces_movement_constraints(engine, product_factory, kind, quantity):
    product = product_factory()
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO stock_movements (product_id, movement_type, quantity) VALUES (:id, :kind, :quantity)"), {"id": product["id"], "kind": kind, "quantity": quantity})


@pytest.mark.integration
def test_database_protects_product_with_history(engine, product_factory, client):
    product = product_factory()
    client.post(f'/api/products/{product["id"]}/movements', json={"movement_type": "IN", "quantity": 1})
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM products WHERE id = :id"), {"id": product["id"]})
