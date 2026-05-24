from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PipelineRun


async def list_recent_runs(
    db: AsyncSession, job_name: str | None, limit: int
) -> list[PipelineRun]:
    stmt = select(PipelineRun).order_by(desc(PipelineRun.started_at)).limit(limit)
    if job_name:
        stmt = stmt.where(PipelineRun.job_name == job_name)
    rows = await db.execute(stmt)
    return list(rows.scalars().all())


async def get_freshness(db: AsyncSession) -> list[dict]:
    """
    For each known job_name, returns the most recent run + most recent
    successful run + freshness in minutes.
    """
    # Distinct job names in the table
    job_names = (
        await db.execute(select(PipelineRun.job_name).distinct())
    ).scalars().all()

    out: list[dict] = []
    for job in job_names:
        last_any = (
            await db.execute(
                select(PipelineRun)
                .where(PipelineRun.job_name == job)
                .order_by(desc(PipelineRun.started_at))
                .limit(1)
            )
        ).scalar_one_or_none()
        last_ok = (
            await db.execute(
                select(PipelineRun)
                .where(PipelineRun.job_name == job, PipelineRun.status == "success")
                .order_by(desc(PipelineRun.finished_at))
                .limit(1)
            )
        ).scalar_one_or_none()
        minutes_since = None
        if last_ok and last_ok.finished_at:
            now = await db.scalar(select(func.now()))
            if now is not None:
                minutes_since = round((now - last_ok.finished_at).total_seconds() / 60, 2)
        out.append(
            {
                "job_name": job,
                "last_success_at": last_ok.finished_at if last_ok else None,
                "last_run_at": last_any.started_at if last_any else None,
                "last_run_status": last_any.status if last_any else None,
                "last_rows_processed": last_ok.rows_processed if last_ok else None,
                "minutes_since_success": minutes_since,
            }
        )
    out.sort(key=lambda r: r["job_name"])
    return out
