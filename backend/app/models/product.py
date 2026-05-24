from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Product(Base):
    __tablename__ = "dim_products"

    product_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)

    name: Mapped[str | None] = mapped_column(String)
    normalized_name: Mapped[str | None] = mapped_column(String, index=True)

    brand: Mapped[str | None] = mapped_column(String, index=True)
    normalized_brand: Mapped[str | None] = mapped_column(String, index=True)

    category: Mapped[str | None] = mapped_column(String, index=True)
    subcategory: Mapped[str | None] = mapped_column(String)

    size: Mapped[str | None] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String)
    description_lang: Mapped[str | None] = mapped_column(String(2), index=True)
    image_url: Mapped[str | None] = mapped_column(String)

    price: Mapped[float | None] = mapped_column(Numeric(10, 2))

    thc_min: Mapped[float | None] = mapped_column(Numeric(10, 2))
    thc_max: Mapped[float | None] = mapped_column(Numeric(10, 2))
    cbd_min: Mapped[float | None] = mapped_column(Numeric(10, 2))
    cbd_max: Mapped[float | None] = mapped_column(Numeric(10, 2))

    last_scraped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    prices = relationship("Price", back_populates="product", lazy="raise")
