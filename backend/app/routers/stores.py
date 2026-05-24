from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.crud import stores as stores_crud
from app.deps import DbDep, PaginationDep
from app.schemas import (
    PaginatedResponse,
    ProductWithMarketPrices,
    StoreDetail,
    StoreSummary,
)

router = APIRouter(prefix="/stores", tags=["Stores"])


@router.get("", response_model=PaginatedResponse[StoreSummary], summary="List stores")
async def list_stores(
    db: DbDep,
    pagination: PaginationDep,
    q: Annotated[str | None, Query(description="Free-text search on name/address")] = None,
):
    items, total = await stores_crud.list_stores(
        db, q=q, offset=pagination.offset, limit=pagination.limit
    )
    return pagination.build_response(items, total)


@router.get("/{store_id}", response_model=StoreDetail, summary="Get store details")
async def get_store(store_id: int, db: DbDep):
    store = await stores_crud.get_store(db, store_id)
    if not store:
        raise HTTPException(status_code=404, detail=f"Store {store_id} not found")
    return store


@router.get(
    "/{store_id}/products",
    response_model=PaginatedResponse[ProductWithMarketPrices],
    summary="Products carried at a store",
)
async def list_products_at_store(
    store_id: int,
    db: DbDep,
    pagination: PaginationDep,
    category: Annotated[str | None, Query()] = None,
    brand: Annotated[str | None, Query()] = None,
    on_sale: Annotated[bool | None, Query()] = None,
    in_stock: Annotated[bool | None, Query()] = None,
    q: Annotated[str | None, Query()] = None,
):
    store = await stores_crud.get_store(db, store_id)
    if not store:
        raise HTTPException(status_code=404, detail=f"Store {store_id} not found")

    items, total = await stores_crud.list_products_at_store(
        db,
        store_id,
        category=category,
        brand=brand,
        on_sale=on_sale,
        in_stock=in_stock,
        q=q,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    return pagination.build_response(items, total)
