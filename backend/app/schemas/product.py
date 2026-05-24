from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    product_id: int
    name: str | None
    brand: str | None
    category: str | None
    subcategory: str | None = None
    size: str | None = None

    description: str | None = None
    description_lang: str | None = Field(
        default=None,
        description='ISO-639-1 language code of `description`. "en", "fr", or null.',
    )
    image_url: str | None = None

    price: Decimal | None = Field(default=None, description="OCS MSRP")

    thc_min: Decimal | None = None
    thc_max: Decimal | None = None
    cbd_min: Decimal | None = None
    cbd_max: Decimal | None = None

    model_config = ConfigDict(from_attributes=True)


class ProductWithMarketPrices(ProductBase):
    """Product summary plus min/max observed retail price across all stores."""

    min_retail_price: Decimal | None = None
    max_retail_price: Decimal | None = None
    min_sale_price: Decimal | None = None
    stores_carrying: int = 0
    stores_on_sale: int = 0


class StorePriceForProduct(BaseModel):
    """One row of the 'available at N stores' table on the product detail page."""

    store_id: int
    store_name: str | None
    address: str | None
    distance_km: float | None = Field(
        default=None,
        description="Crow-flies distance from a reference store (optional, populated when ?from_store_id= used)",
    )
    regular_price: Decimal | None
    sale_price: Decimal | None
    discount_percent: Decimal | None
    in_stock: bool | None
    promo_first_seen: date | None
    promo_last_seen: date | None
    promo_duration_days: int | None

    model_config = ConfigDict(from_attributes=True)


class ProductDetail(ProductBase):
    available_at: list[StorePriceForProduct]
    stores_carrying: int = 0


class NewArrival(BaseModel):
    launch_id: int
    product_id: int
    launch_date: date
    name: str | None
    brand: str | None
    category: str | None
    ocs_price: Decimal | None
    url: str | None
    image_url: str | None = None

    model_config = ConfigDict(from_attributes=True)
