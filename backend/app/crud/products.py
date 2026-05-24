from sqlalchemy import and_, asc, case, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OCSLaunch, Price, Product, Store


async def list_products(
    db: AsyncSession,
    category: str | None,
    brand: str | None,
    min_price: float | None,
    max_price: float | None,
    on_sale: bool | None,
    q: str | None,
    sort: str,
    offset: int,
    limit: int,
    available_locally: bool | None = None,
    lang: str | None = None,
    include_no_image: bool = False,
) -> tuple[list[dict], int]:
    """List products with min/max observed retail prices across all stores."""

    # Aggregated price subquery
    price_agg = (
        select(
            Price.product_id,
            func.min(Price.regular_price).label("min_retail_price"),
            func.max(Price.regular_price).label("max_retail_price"),
            func.min(Price.sale_price).label("min_sale_price"),
            func.count(func.distinct(Price.store_id)).label("stores_carrying"),
            func.sum(case((Price.sale_price.is_not(None), 1), else_=0)).label("stores_on_sale"),
        )
        .group_by(Price.product_id)
        .subquery()
    )

    base = select(Product, price_agg).outerjoin(price_agg, Product.product_id == price_agg.c.product_id)

    if category:
        base = base.where(Product.category == category)
    if brand:
        base = base.where(Product.brand == brand)
    if min_price is not None:
        base = base.where(price_agg.c.min_retail_price >= min_price)
    if max_price is not None:
        base = base.where(price_agg.c.max_retail_price <= max_price)
    if on_sale is True:
        base = base.where(price_agg.c.stores_on_sale > 0)
    if available_locally is True:
        base = base.where(price_agg.c.stores_carrying > 0)
    if not include_no_image:
        base = base.where(Product.image_url.is_not(None))
    if lang:
        # 'en' or 'fr' — match exact, but also include rows where lang is null
        # so we don't accidentally hide products that have no description at all
        from sqlalchemy import or_ as or_clause
        base = base.where(
            or_clause(Product.description_lang == lang, Product.description_lang.is_(None))
        )
    if q:
        like = f"%{q.lower()}%"
        base = base.where(
            or_(
                func.lower(Product.name).like(like),
                func.lower(Product.brand).like(like),
                func.lower(Product.category).like(like),
            )
        )

    # Sort — push NULL price/store counts to the end
    sort_map = {
        "name": asc(Product.name),
        "-name": desc(Product.name),
        "price": asc(price_agg.c.min_retail_price).nulls_last(),
        "-price": desc(price_agg.c.min_retail_price).nulls_last(),
        "stores": desc(price_agg.c.stores_carrying).nulls_last(),
    }
    base = base.order_by(sort_map.get(sort, asc(Product.name)))

    total = await db.scalar(select(func.count()).select_from(base.subquery()))

    rows = (await db.execute(base.offset(offset).limit(limit))).all()
    out = []
    for prod, *price_cols in rows:
        d = {c.name: getattr(prod, c.name) for c in Product.__table__.columns}
        # price_agg columns by position
        # ordering: product_id, min_retail, max_retail, min_sale, stores_carrying, stores_on_sale
        _, mn, mx, mns, sc, soc = price_cols
        d["min_retail_price"] = mn
        d["max_retail_price"] = mx
        d["min_sale_price"] = mns
        d["stores_carrying"] = int(sc or 0)
        d["stores_on_sale"] = int(soc or 0)
        out.append(d)
    return out, int(total or 0)


async def get_product_detail(db: AsyncSession, product_id: int) -> dict | None:
    prod = await db.get(Product, product_id)
    if not prod:
        return None

    rows = (
        await db.execute(
            select(Price, Store)
            .join(Store, Store.store_id == Price.store_id)
            .where(Price.product_id == product_id)
            .order_by(asc(Price.sale_price), asc(Price.regular_price))
        )
    ).all()

    available_at = []
    for price, store in rows:
        available_at.append(
            {
                "store_id": store.store_id,
                "store_name": store.store_name,
                "address": store.address,
                "distance_km": None,
                "regular_price": price.regular_price,
                "sale_price": price.sale_price,
                "discount_percent": price.discount_percent,
                "in_stock": price.in_stock,
                "promo_first_seen": price.promo_first_seen,
                "promo_last_seen": price.promo_last_seen,
                "promo_duration_days": price.promo_duration_days,
            }
        )

    d = {c.name: getattr(prod, c.name) for c in Product.__table__.columns}
    d["available_at"] = available_at
    d["stores_carrying"] = len(available_at)
    return d


async def list_categories(db: AsyncSession) -> list[dict]:
    rows = (
        await db.execute(
            select(Product.category, func.count().label("count"))
            .where(Product.category.is_not(None))
            .group_by(Product.category)
            .order_by(desc("count"))
        )
    ).all()
    return [{"name": c, "count": int(n)} for c, n in rows if c]


async def list_brands(db: AsyncSession) -> list[dict]:
    rows = (
        await db.execute(
            select(Product.brand, func.count().label("count"))
            .where(Product.brand.is_not(None))
            .group_by(Product.brand)
            .order_by(desc("count"))
            .limit(500)
        )
    ).all()
    return [{"name": b, "count": int(n)} for b, n in rows if b]


async def list_new_arrivals(db: AsyncSession, days: int, limit: int) -> list[dict]:
    from datetime import date, timedelta

    cutoff = date.today() - timedelta(days=days)
    rows = (
        await db.execute(
            select(OCSLaunch, Product.image_url)
            .outerjoin(Product, Product.product_id == OCSLaunch.product_id)
            .where(OCSLaunch.launch_date >= cutoff)
            .order_by(desc(OCSLaunch.launch_date))
            .limit(limit)
        )
    ).all()
    out = []
    for launch, image_url in rows:
        d = {c.name: getattr(launch, c.name) for c in OCSLaunch.__table__.columns}
        d["image_url"] = image_url
        out.append(d)
    return out
