from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OCSLaunch(Base):
    """
    Tracks new product launches on the Ontario Cannabis Store. Feeds the
    'New Arrivals' frontend section + competitive intel reporting.
    """

    __tablename__ = "fct_ocs_launches"

    launch_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("dim_products.product_id", ondelete="CASCADE"), index=True
    )

    launch_date: Mapped[date] = mapped_column(Date, index=True)
    name: Mapped[str | None] = mapped_column(String)
    brand: Mapped[str | None] = mapped_column(String)
    category: Mapped[str | None] = mapped_column(String, index=True)
    ocs_price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    url: Mapped[str | None] = mapped_column(String)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
