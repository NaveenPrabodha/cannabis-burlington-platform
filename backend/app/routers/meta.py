from fastapi import APIRouter
from sqlalchemy import text

from app.config import get_settings
from app.crud import products as products_crud
from app.deps import DbDep
from app.schemas import CountedItem, HealthResponse

router = APIRouter(tags=["Meta"])


@router.get("/health", response_model=HealthResponse, summary="Service health")
async def health(db: DbDep):
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    settings = get_settings()
    return {
        "status": "ok" if db_ok else "degraded",
        "db_ok": db_ok,
        "version": settings.app_version,
        "env": settings.env,
    }


@router.get(
    "/categories",
    response_model=list[CountedItem],
    summary="Categories with product counts",
)
async def categories(db: DbDep):
    return await products_crud.list_categories(db)


@router.get(
    "/brands", response_model=list[CountedItem], summary="Brands with product counts"
)
async def brands(db: DbDep):
    return await products_crud.list_brands(db)
