from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.products import list_products
from app.crud.stores import list_stores


async def unified_search(
    db: AsyncSession,
    q: str,
    type_: str,
    limit: int,
) -> dict:
    """Return matched products + stores for one query."""
    products, total_products = ([], 0)
    stores, total_stores = ([], 0)

    if type_ in ("all", "products"):
        products, total_products = await list_products(
            db,
            category=None,
            brand=None,
            min_price=None,
            max_price=None,
            on_sale=None,
            q=q,
            sort="name",
            offset=0,
            limit=limit,
        )
    if type_ in ("all", "stores"):
        stores, total_stores = await list_stores(db, q=q, offset=0, limit=limit)

    return {
        "query": q,
        "products": products,
        "stores": stores,
        "total_products": total_products,
        "total_stores": total_stores,
    }
