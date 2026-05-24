from typing import Annotated

from fastapi import APIRouter, Query

from app.crud import pipeline as pipeline_crud
from app.deps import DbDep
from app.schemas import PipelineFreshness, PipelineRun

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])


@router.get(
    "/runs",
    response_model=list[PipelineRun],
    summary="Recent pipeline runs (audit trail)",
)
async def list_runs(
    db: DbDep,
    job_name: Annotated[str | None, Query(description="Filter by job name")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
):
    return await pipeline_crud.list_recent_runs(db, job_name=job_name, limit=limit)


@router.get(
    "/freshness",
    response_model=list[PipelineFreshness],
    summary="Per-job data freshness (last success, minutes elapsed)",
)
async def freshness(db: DbDep):
    return await pipeline_crud.get_freshness(db)
