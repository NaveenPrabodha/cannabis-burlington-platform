"""add description_lang

Revision ID: 40b52a808c1d
Revises: 62139a40f3be
Create Date: 2026-05-23 13:55:32.234804

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '40b52a808c1d'
down_revision: str | None = '62139a40f3be'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "dim_products",
        sa.Column("description_lang", sa.String(length=2), nullable=True),
    )
    op.create_index(
        "ix_dim_products_description_lang",
        "dim_products",
        ["description_lang"],
    )


def downgrade() -> None:
    op.drop_index("ix_dim_products_description_lang", table_name="dim_products")
    op.drop_column("dim_products", "description_lang")
