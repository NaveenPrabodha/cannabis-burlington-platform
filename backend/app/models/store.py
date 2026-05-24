from datetime import datetime

from sqlalchemy import Boolean, DateTime, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Store(Base):
    __tablename__ = "dim_stores"

    store_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    store_name: Mapped[str | None] = mapped_column(String)
    normalized_store_name: Mapped[str | None] = mapped_column(String)

    address: Mapped[str | None] = mapped_column(String)
    phone: Mapped[str | None] = mapped_column(String)
    website: Mapped[str | None] = mapped_column(String)

    hibuddy_store_id: Mapped[str | None] = mapped_column(String, index=True)
    hibuddy_slug: Mapped[str | None] = mapped_column(String, index=True)

    hours_json: Mapped[dict | None] = mapped_column(JSONB)

    owner_name: Mapped[str | None] = mapped_column(String)
    owner_company: Mapped[str | None] = mapped_column(String)
    agco_licence_number: Mapped[str | None] = mapped_column(String, index=True)

    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7))

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    last_scraped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    prices = relationship("Price", back_populates="store", lazy="raise")
