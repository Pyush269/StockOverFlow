import logging
from datetime import datetime, timezone

from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..errors import DomainError
from ..models import MAX_QUANTITY, Product, StockMovement
from ..schemas import MovementCreate, ProductWrite

logger = logging.getLogger(__name__)


def find_product(db: Session, product_id: int, *, lock: bool = False) -> Product:
    query = select(Product).where(Product.id == product_id)
    if lock:
        query = query.with_for_update()
    product = db.scalar(query)
    if product is None:
        raise DomainError(404, "product_not_found", "Product not found")
    return product


def _raise_write_error(exc: IntegrityError) -> None:
    constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
    if constraint == "uq_products_sku":
        raise DomainError(409, "duplicate_sku", "A product with this SKU already exists") from exc
    raise exc


def create_product(db: Session, payload: ProductWrite) -> Product:
    try:
        with db.begin():
            product = Product(**payload.model_dump(), quantity=0)
            db.add(product)
            db.flush()
    except IntegrityError as exc:
        _raise_write_error(exc)
    return product


def update_product(db: Session, product_id: int, payload: ProductWrite) -> Product:
    try:
        with db.begin():
            product = find_product(db, product_id, lock=True)
            for key, value in payload.model_dump().items():
                setattr(product, key, value)
            product.updated_at = datetime.now(timezone.utc)
            db.flush()
    except IntegrityError as exc:
        _raise_write_error(exc)
    return product


def delete_product(db: Session, product_id: int) -> None:
    with db.begin():
        product = find_product(db, product_id, lock=True)
        if db.scalar(select(exists().where(StockMovement.product_id == product_id))):
            raise DomainError(409, "product_has_history", "Products with movement history cannot be deleted")
        db.delete(product)


def record_movement(db: Session, product_id: int, payload: MovementCreate) -> tuple[Product, StockMovement]:
    # All quantity changes and deletes take the same product row lock. PostgreSQL
    # holds it through commit, so a competing issue sees the committed quantity.
    with db.begin():
        product = find_product(db, product_id, lock=True)
        if payload.movement_type == "OUT":
            if payload.quantity > product.quantity:
                raise DomainError(409, "insufficient_stock", "Requested quantity exceeds available stock")
            product.quantity -= payload.quantity
        else:
            if product.quantity > MAX_QUANTITY - payload.quantity:
                raise DomainError(409, "stock_limit_exceeded", "Stock would exceed the supported quantity")
            product.quantity += payload.quantity
        product.updated_at = datetime.now(timezone.utc)
        movement = StockMovement(product_id=product_id, **payload.model_dump())
        db.add(movement)
        # Flush both writes inside the transaction. An insert failure also rolls
        # back the quantity change; nothing is committed in a finally block.
        db.flush()
    logger.info("Stock movement recorded product_id=%s type=%s quantity=%s", product_id, payload.movement_type, payload.quantity)
    return product, movement
