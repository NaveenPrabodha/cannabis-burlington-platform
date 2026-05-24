from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Price, Product, Store


async def list_stores(
    db: AsyncSession,
    q: str | None,
    offset: int,
    limit: int,
) -> tuple[list[dict], int]:
    base = select(Store)
    if q:
        like = f"%{q.lower()}%"
        base = base.where(
            or_(
                func.lower(Store.store_name).like(like),
                func.lower(Store.address).like(like),
            )
        )

    total = await db.scalar(select(func.count()).select_from(base.subquery()))

    # product counts subquery
    pc_subq = (
        select(Price.store_id, func.count(func.distinct(Price.product_id)).label("pc"))
        .group_by(Price.store_id)
        .subquery()
    )

    rows = (
        await db.execute(
            base.add_columns(func.coalesce(pc_subq.c.pc, 0).label("product_count"))
            .outerjoin(pc_subq, Store.store_id == pc_subq.c.store_id)
            .order_by(Store.store_name)
            .offset(offset)
            .limit(limit)
        )
    ).all()

    items = []
    for store, product_count in rows:
        d = {c.name: getattr(store, c.name) for c in Store.__table__.columns}
        d["product_count"] = int(product_count or 0)
        items.append(d)
    return items, int(total or 0)


async def get_store(db: AsyncSession, store_id: int) -> dict | None:
    store = await db.get(Store, store_id)
    if not store:
        return None

    pc_q = select(func.count(func.distinct(Price.product_id))).where(Price.store_id == store_id)
    dc_q = select(func.count()).where(
        and_(Price.store_id == store_id, Price.sale_price.is_not(None))
    )

    product_count = await db.scalar(pc_q) or 0
    deals_count = await db.scalar(dc_q) or 0

    d = {c.name: getattr(store, c.name) for c in Store.__table__.columns}
    d["product_count"] = int(product_count)
    d["deals_count"] = int(deals_count)
    return d


async def list_products_at_store(
    db: AsyncSession,
    store_id: int,
    category: str | None,
    brand: str | None,
    on_sale: bool | None,
    in_stock: bool | None,
    q: str | None,
    offset: int,
    limit: int,
) -> tuple[list[dict], int]:
    base = (
        select(Product, Price)
        .join(Price, Price.product_id == Product.product_id)
        .where(Price.store_id == store_id)
    )
    if category:
        base = base.where(Product.category == category)
    if brand:
        base = base.where(Product.brand == brand)
    if on_sale is True:
        base = base.where(Price.sale_price.is_not(None))
    if on_sale is False:
        base = base.where(Price.sale_price.is_(None))
    if in_stock is True:
        base = base.where(Price.in_stock.is_(True))
    if q:
        like = f"%{q.lower()}%"
        base = base.where(
            or_(
                func.lower(Product.name).like(like),
                func.lower(Product.brand).like(like),
            )
        )

    total = await db.scalar(select(func.count()).select_from(base.subquery()))

    rows = (
        await db.execute(
            base.order_by(Product.name).offset(offset).limit(limit)
        )
    ).all()

    out = []
    for prod, price in rows:
        d = {c.name: getattr(prod, c.name) for c in Product.__table__.columns}
        d["regular_price"] = price.regular_price
        d["sale_price"] = price.sale_price
        d["discount_percent"] = price.discount_percent
        d["in_stock"] = price.in_stock
        d["promo_first_seen"] = price.promo_first_seen
        d["promo_last_seen"] = price.promo_last_seen
        d["promo_duration_days"] = price.promo_duration_days
        out.append(d)
    return out, int(total or 0)
