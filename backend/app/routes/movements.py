from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import StockMovement
from ..schemas import MovementCreate, MovementPage, MovementResult
from ..services.inventory import find_product, record_movement

router = APIRouter(prefix="/api/products", tags=["Stock movements"])
Database = Annotated[Session, Depends(get_db)]
ProductID = Annotated[int, Path(gt=0)]


@router.post("/{product_id}/movements", response_model=MovementResult, status_code=status.HTTP_201_CREATED)
def create_movement(product_id: ProductID, payload: MovementCreate, db: Database):
    product, movement = record_movement(db, product_id, payload)
    return {"product": product, "movement": movement}


@router.get("/{product_id}/movements", response_model=MovementPage)
def list_movements(
    product_id: ProductID,
    db: Database,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    find_product(db, product_id)
    total = db.scalar(select(func.count()).select_from(StockMovement).where(StockMovement.product_id == product_id))
    items = db.scalars(
        select(StockMovement).where(StockMovement.product_id == product_id)
        .order_by(StockMovement.created_at.desc(), StockMovement.id.desc())
        .limit(limit).offset(offset)
    ).all()
    return {"items": items, "total": total, "limit": limit, "offset": offset}
