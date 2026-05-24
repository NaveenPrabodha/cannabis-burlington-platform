from fastapi import APIRouter

from app.crud import deals as deals_crud
from app.crud import products as products_crud
from app.deps import DbDep
from app.schemas import Deal, NewArrival

router = APIRouter(tags=["Featured"])


@router.get(
    "/featured",
    response_model=dict,
    summary="Homepage featured content (top deals + new arrivals)",
)
async def featured(db: DbDep):
    top_deals, _ = await deals_crud.list_deals(
        db, category=None, min_discount=20, offset=0, limit=8
    )
    new_arrivals = await products_crud.list_new_arrivals(db, days=14, limit=8)
    return {
        "top_deals": top_deals,
        "new_arrivals": new_arrivals,
    }
