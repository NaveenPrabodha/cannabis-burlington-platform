"""add pipeline_runs table

Revision ID: cb81f67950cd
Revises: 40b52a808c1d
Create Date: 2026-05-23 16:00:06.544995

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'cb81f67950cd'
down_revision: str | None = '40b52a808c1d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pipeline_runs",
        sa.Column("run_id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("job_name", sa.String(length=64), nullable=False, index=True),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            comment="running | success | failure",
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "duration_s",
            sa.Numeric(10, 2),
            nullable=True,
            comment="seconds; finished_at - started_at",
        ),
        sa.Column(
            "rows_processed",
            sa.Integer(),
            nullable=True,
            comment="rows scraped or inserted, scraper-defined",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            sa.JSON(),
            nullable=True,
            comment="job-specific stats: pages, matches, etc.",
        ),
    )
    op.create_index(
        "ix_pipeline_runs_job_started",
        "pipeline_runs",
        ["job_name", sa.text("started_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_pipeline_runs_job_started", table_name="pipeline_runs")
    op.drop_table("pipeline_runs")
