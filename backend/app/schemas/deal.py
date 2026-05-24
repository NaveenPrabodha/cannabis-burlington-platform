from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class Deal(BaseModel):
    """A product currently on sale at one specific store."""

    fact_id: int
    store_id: int
    store_name: str | None
    product_id: int
    product_name: str | None
    brand: str | None
    category: str | None
    image_url: str | None

    regular_price: Decimal | None
    sale_price: Decimal | None
    discount_percent: Decimal | None
    promo_first_seen: date | None
    promo_last_seen: date | None
    promo_duration_days: int | None
    in_stock: bool | None

    model_config = ConfigDict(from_attributes=True)
