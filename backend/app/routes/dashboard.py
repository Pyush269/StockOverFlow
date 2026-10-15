from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Product, StockMovement
from ..schemas import DashboardOut, MovementOut, RecentMovement

router = APIRouter(prefix="/api", tags=["Dashboard"])


@router.get("/dashboard", response_model=DashboardOut)
def get_dashboard(db: Annotated[Session, Depends(get_db)]):
    total_products, total_units, inventory_value = db.execute(select(
        func.count(Product.id),
        func.coalesce(func.sum(Product.quantity), 0),
        func.coalesce(func.sum(Product.quantity * Product.unit_price), Decimal("0.00")),
    )).one()
    low_stock_filter = Product.quantity <= Product.reorder_level
    low_stock_count = db.scalar(select(func.count()).select_from(Product).where(low_stock_filter))
    low_stock_products = db.scalars(
        select(Product).where(low_stock_filter).order_by(Product.quantity, Product.id).limit(10)
    ).all()
    recent_rows = db.execute(
        select(StockMovement, Product.sku, Product.name)
        .join(Product, Product.id == StockMovement.product_id)
        .order_by(StockMovement.created_at.desc(), StockMovement.id.desc()).limit(10)
    ).all()
    recent_movements = [
        RecentMovement(**MovementOut.model_validate(movement).model_dump(), product_sku=sku, product_name=name)
        for movement, sku, name in recent_rows
    ]
    return {
        "total_products": total_products,
        "total_units": total_units,
        "inventory_value": inventory_value,
        "low_stock_count": low_stock_count,
        "low_stock_products": low_stock_products,
        "recent_movements": recent_movements,
    }
