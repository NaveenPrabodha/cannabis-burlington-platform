from typing import Annotated

from fastapi import APIRouter, Query

from app.crud import deals as deals_crud
from app.deps import DbDep, PaginationDep
from app.schemas import Deal, PaginatedResponse

router = APIRouter(prefix="/deals", tags=["Deals"])


@router.get("", response_model=PaginatedResponse[Deal], summary="Active promotions")
async def list_deals(
    db: DbDep,
    pagination: PaginationDep,
    category: Annotated[str | None, Query()] = None,
    min_discount: Annotated[
        float | None, Query(ge=0, le=100, description="Minimum discount %")
    ] = None,
):
    items, total = await deals_crud.list_deals(
        db,
        category=category,
        min_discount=min_discount,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    return pagination.build_response(items, total)
