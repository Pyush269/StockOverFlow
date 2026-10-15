from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import MAX_QUANTITY

NonnegativeInt = Annotated[int, Field(strict=True, ge=0, le=MAX_QUANTITY)]
PositiveQuantity = Annotated[int, Field(strict=True, ge=1, le=MAX_QUANTITY)]
Money = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2, allow_inf_nan=False)]


class ProductWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    sku: str = Field(min_length=1, max_length=64, pattern=r"^[A-Z0-9][A-Z0-9._-]*$")
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    category: str = Field(default="General", min_length=1, max_length=80)
    unit_price: Money = Decimal("0.00")
    reorder_level: NonnegativeInt = 5

    @field_validator("sku", mode="before")
    @classmethod
    def normalize_sku(cls, value):
        return value.strip().upper() if isinstance(value, str) else value


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str
    description: str
    category: str
    unit_price: Decimal
    quantity: int
    reorder_level: int
    created_at: datetime
    updated_at: datetime


class ProductPage(BaseModel):
    items: list[ProductOut]
    total: int
    limit: int
    offset: int


class MovementCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    movement_type: Literal["IN", "OUT"]
    quantity: PositiveQuantity
    note: str = Field(default="", max_length=500)


class MovementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    movement_type: Literal["IN", "OUT"]
    quantity: int
    note: str
    created_at: datetime


class MovementResult(BaseModel):
    product: ProductOut
    movement: MovementOut


class MovementPage(BaseModel):
    items: list[MovementOut]
    total: int
    limit: int
    offset: int


class RecentMovement(MovementOut):
    product_sku: str
    product_name: str


class DashboardOut(BaseModel):
    total_products: int
    total_units: int
    low_stock_count: int
    inventory_value: Decimal
    low_stock_products: list[ProductOut]
    recent_movements: list[RecentMovement]
