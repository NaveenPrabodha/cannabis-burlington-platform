from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Price, Product, Store


async def list_deals(
    db: AsyncSession,
    category: str | None,
    min_discount: float | None,
    offset: int,
    limit: int,
) -> tuple[list[dict], int]:
    base = (
        select(Price, Product, Store)
        .join(Product, Product.product_id == Price.product_id)
        .join(Store, Store.store_id == Price.store_id)
        .where(Price.sale_price.is_not(None))
    )
    if category:
        base = base.where(Product.category == category)
    if min_discount is not None:
        base = base.where(Price.discount_percent >= min_discount)

    total = await db.scalar(select(func.count()).select_from(base.subquery()))

    rows = (
        await db.execute(
            base.order_by(desc(Price.discount_percent).nulls_last()).offset(offset).limit(limit)
        )
    ).all()

    out = []
    for price, product, store in rows:
        out.append(
            {
                "fact_id": price.fact_id,
                "store_id": store.store_id,
                "store_name": store.store_name,
                "product_id": product.product_id,
                "product_name": product.name,
                "brand": product.brand,
                "category": product.category,
                "image_url": product.image_url,
                "regular_price": price.regular_price,
                "sale_price": price.sale_price,
                "discount_percent": price.discount_percent,
                "promo_first_seen": price.promo_first_seen,
                "promo_last_seen": price.promo_last_seen,
                "promo_duration_days": price.promo_duration_days,
                "in_stock": price.in_stock,
            }
        )
    return out, int(total or 0)
