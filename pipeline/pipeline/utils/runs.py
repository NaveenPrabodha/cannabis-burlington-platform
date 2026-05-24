"""
`run_logged` context manager — writes every pipeline run to pipeline_runs.

Each scraper / job wraps its main logic in this manager so the backend can
expose data freshness in the UI and you have a queryable audit trail
regardless of which orchestrator triggered the run.

Usage:

    from pipeline.utils.runs import run_logged

    def main():
        with run_logged("ocs_new_arrivals") as run:
            recent = fetch_recent_products(days=30)
            upsert_products(recent)
            insert_launches(recent)
            run.rows_processed = len(recent)
            run.metadata = {"days_window": 30, "pages_fetched": 37}
"""

from __future__ import annotations

import json
import traceback
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from pipeline.db.connection import get_connection
from pipeline.utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class RunContext:
    job_name: str
    rows_processed: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def _insert_starting(job_name: str) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO pipeline_runs (job_name, status, started_at)
            VALUES (%s, %s, %s)
            RETURNING run_id
            """,
            (job_name, "running", datetime.now(timezone.utc)),
        )
        run_id = cur.fetchone()[0]
        return int(run_id)


def _update_completion(
    run_id: int,
    status: str,
    rows: int | None,
    metadata: dict | None,
    error: str | None,
    started_at_ts: float,
) -> None:
    duration = round(_now_ts() - started_at_ts, 2)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE pipeline_runs SET
                status = %s,
                finished_at = %s,
                duration_s = %s,
                rows_processed = %s,
                metadata = %s,
                error_message = %s
            WHERE run_id = %s
            """,
            (
                status,
                datetime.now(timezone.utc),
                duration,
                rows,
                json.dumps(metadata) if metadata else None,
                error,
                run_id,
            ),
        )


def _now_ts() -> float:
    return datetime.now(timezone.utc).timestamp()


@contextmanager
def run_logged(job_name: str):
    """
    Context manager that records the run in pipeline_runs.

    Yields a RunContext that the caller can populate with rows_processed
    and metadata. Failures are caught, logged, re-raised — the DB record
    captures the traceback either way.
    """
    started = _now_ts()
    run_id = _insert_starting(job_name)
    ctx = RunContext(job_name=job_name)
    log.info("pipeline_run_started", job=job_name, run_id=run_id)
    try:
        yield ctx
    except Exception as e:
        tb = traceback.format_exc()
        _update_completion(run_id, "failure", ctx.rows_processed, ctx.metadata, tb, started)
        log.error("pipeline_run_failed", job=job_name, run_id=run_id, error=str(e))
        raise
    else:
        _update_completion(run_id, "success", ctx.rows_processed, ctx.metadata, None, started)
        log.info(
            "pipeline_run_succeeded",
            job=job_name,
            run_id=run_id,
            duration_s=round(_now_ts() - started, 2),
            rows=ctx.rows_processed,
        )
