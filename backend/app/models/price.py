from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Computed, Date, DateTime, ForeignKey, Integer, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Price(Base):
    """
    Current (latest) price snapshot per (store, product).
    Updated daily by the hibuddy pipeline; promo_first_seen / promo_last_seen
    track promotion duration based on observed sale_price activity.
    """

    __tablename__ = "fct_prices"
    __table_args__ = (
        UniqueConstraint("store_id", "product_id", name="uq_fct_prices_store_product"),
    )

    fact_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    store_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("dim_stores.store_id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("dim_products.product_id", ondelete="CASCADE"), index=True
    )

    scraped_date: Mapped[date | None] = mapped_column(Date, index=True)

    regular_price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    sale_price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    discount_percent: Mapped[float | None] = mapped_column(Numeric(10, 2))
    typical_nearby: Mapped[float | None] = mapped_column(Numeric(10, 2))

    in_stock: Mapped[bool | None] = mapped_column(Boolean)

    promo_first_seen: Mapped[date | None] = mapped_column(Date)
    promo_last_seen: Mapped[date | None] = mapped_column(Date)
    promo_duration_days: Mapped[int | None] = mapped_column(
        Integer,
        Computed("(promo_last_seen - promo_first_seen)", persisted=True),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    store = relationship("Store", back_populates="prices", lazy="joined")
    product = relationship("Product", back_populates="prices", lazy="joined")


class PriceHistory(Base):
    """
    Append-only daily price snapshot. Never updated. Enables point-in-time queries
    and promo-duration computation. Per the architecture in the previous report.
    """

    __tablename__ = "fct_price_history"
    __table_args__ = (
        UniqueConstraint(
            "store_id", "product_id", "scraped_date", name="uq_fct_price_history_grain"
        ),
    )

    history_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    store_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("dim_stores.store_id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("dim_products.product_id", ondelete="CASCADE"), index=True
    )

    scraped_date: Mapped[date] = mapped_column(Date, index=True)
    regular_price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    sale_price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    in_stock: Mapped[bool | None] = mapped_column(Boolean)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
