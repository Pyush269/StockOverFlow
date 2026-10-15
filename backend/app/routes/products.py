from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Product
from ..schemas import ProductOut, ProductPage, ProductWrite
from ..services import inventory

router = APIRouter(prefix="/api/products", tags=["Products"])
Database = Annotated[Session, Depends(get_db)]
ProductID = Annotated[int, Path(gt=0)]


@router.get("", response_model=ProductPage)
def list_products(
    db: Database,
    q: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    category: Annotated[str | None, Query(min_length=1, max_length=80)] = None,
    stock_status: Annotated[Literal["healthy", "low", "out"] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    filters = []
    if q and q.strip():
        search = q.strip().lower()
        filters.append(or_(
            func.lower(Product.name).contains(search, autoescape=True),
            func.lower(Product.sku).contains(search, autoescape=True),
        ))
    if category:
        filters.append(func.lower(Product.category) == category.strip().lower())
    if stock_status == "healthy":
        filters.append(Product.quantity > Product.reorder_level)
    elif stock_status == "low":
        filters.append(Product.quantity <= Product.reorder_level)
    elif stock_status == "out":
        filters.append(Product.quantity == 0)
    total = db.scalar(select(func.count()).select_from(Product).where(*filters))
    items = db.scalars(select(Product).where(*filters).order_by(Product.id).limit(limit).offset(offset)).all()
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductWrite, db: Database):
    return inventory.create_product(db, payload)


@router.get("/categories", response_model=list[str])
def list_categories(db: Database):
    # The filter itself is case-insensitive; return one label per category,
    # including categories beyond the current catalog page.
    return db.scalars(
        select(func.min(Product.category))
        .group_by(func.lower(Product.category)).order_by(func.lower(Product.category))
    ).all()


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: ProductID, db: Database):
    return inventory.find_product(db, product_id)


@router.put("/{product_id}", response_model=ProductOut)
def update_product(product_id: ProductID, payload: ProductWrite, db: Database):
    # PUT replaces all editable metadata; quantity is never accepted here.
    return inventory.update_product(db, product_id, payload)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: ProductID, db: Database):
    inventory.delete_product(db, product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
