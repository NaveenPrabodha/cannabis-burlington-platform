from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query

from app.crud import products as products_crud
from app.deps import DbDep, PaginationDep
from app.schemas import (
    NewArrival,
    PaginatedResponse,
    ProductDetail,
    ProductWithMarketPrices,
    StorePriceForProduct,
)

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=PaginatedResponse[ProductWithMarketPrices], summary="List products")
async def list_products(
    db: DbDep,
    pagination: PaginationDep,
    category: Annotated[str | None, Query()] = None,
    brand: Annotated[str | None, Query()] = None,
    min_price: Annotated[float | None, Query(ge=0)] = None,
    max_price: Annotated[float | None, Query(ge=0)] = None,
    on_sale: Annotated[bool | None, Query()] = None,
    q: Annotated[str | None, Query()] = None,
    sort: Annotated[
        Literal["name", "-name", "price", "-price", "stores"],
        Query(description="Sort key. Prefix with '-' for descending."),
    ] = "name",
    available_locally: Annotated[
        bool,
        Query(description="If true, hide products no Burlington store currently carries."),
    ] = True,
    lang: Annotated[
        Literal["en", "fr"] | None,
        Query(description="Description language filter; null disables it."),
    ] = "en",
    include_no_image: Annotated[
        bool,
        Query(description="If false (default), hide products with no image_url."),
    ] = False,
):
    items, total = await products_crud.list_products(
        db,
        category=category,
        brand=brand,
        min_price=min_price,
        max_price=max_price,
        on_sale=on_sale,
        q=q,
        sort=sort,
        offset=pagination.offset,
        limit=pagination.limit,
        available_locally=available_locally,
        lang=lang,
        include_no_image=include_no_image,
    )
    return pagination.build_response(items, total)


@router.get("/new-arrivals", response_model=list[NewArrival], summary="Recent OCS launches")
async def new_arrivals(
    db: DbDep,
    days: Annotated[int, Query(ge=1, le=365, description="Window in days")] = 30,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
):
    return await products_crud.list_new_arrivals(db, days=days, limit=limit)


@router.get("/{product_id}", response_model=ProductDetail, summary="Product detail")
async def get_product(product_id: int, db: DbDep):
    prod = await products_crud.get_product_detail(db, product_id)
    if not prod:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return prod


@router.get(
    "/{product_id}/stores",
    response_model=list[StorePriceForProduct],
    summary="Stores carrying a product",
)
async def stores_for_product(product_id: int, db: DbDep):
    prod = await products_crud.get_product_detail(db, product_id)
    if not prod:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return prod["available_at"]
