from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class StoreBase(BaseModel):
    store_id: int
    store_name: str | None
    address: str | None
    phone: str | None
    website: str | None

    latitude: Decimal | None = None
    longitude: Decimal | None = None

    hibuddy_slug: str | None = None
    agco_licence_number: str | None = None
    is_active: bool = True

    hours_json: dict | None = Field(
        default=None,
        description='Weekly hours; null when not yet sourced. Shape: {"mon":"10:00-21:00",...}',
        examples=[{"mon": "10:00-21:00", "sun": "11:00-19:00"}],
    )

    owner_name: str | None = None
    owner_company: str | None = None

    last_scraped_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class StoreSummary(StoreBase):
    """Listed-view: omits heavy fields. Used in /stores."""

    product_count: int = Field(0, description="Number of distinct products carried by this store")


class StoreDetail(StoreBase):
    """Single-store detail. Used in /stores/{id}."""

    product_count: int = 0
    deals_count: int = Field(0, description="Number of products currently on sale at this store")
