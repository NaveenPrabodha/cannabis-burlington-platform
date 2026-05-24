from typing import Annotated, Literal

from fastapi import APIRouter, Query

from app.crud import search as search_crud
from app.deps import DbDep
from app.schemas import SearchResults

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("", response_model=SearchResults, summary="Unified search")
async def search(
    db: DbDep,
    q: Annotated[str, Query(min_length=1, description="Search query")],
    type: Annotated[
        Literal["all", "products", "stores"], Query(description="Scope of search")
    ] = "all",
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
):
    return await search_crud.unified_search(db, q=q, type_=type, limit=limit)
