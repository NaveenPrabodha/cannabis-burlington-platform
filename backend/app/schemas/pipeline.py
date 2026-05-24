from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PipelineRun(BaseModel):
    run_id: int
    job_name: str
    status: str = Field(..., examples=["success", "failure", "running"])
    started_at: datetime
    finished_at: datetime | None
    duration_s: Decimal | None
    rows_processed: int | None
    error_message: str | None = None
    metadata_json: dict | None = Field(default=None, alias="metadata_json")

    model_config = ConfigDict(from_attributes=True)


class PipelineFreshness(BaseModel):
    job_name: str
    last_success_at: datetime | None
    last_run_at: datetime | None
    last_run_status: str | None
    last_rows_processed: int | None
    minutes_since_success: float | None = Field(
        default=None,
        description="How long ago the last successful run finished, in minutes.",
    )
