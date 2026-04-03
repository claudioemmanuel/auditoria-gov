"""Add ingest_state and coverage_registry tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-01
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ingest_state",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("connector", sa.String(100), nullable=False),
        sa.Column("job", sa.String(100), nullable=False),
        sa.Column("last_cursor", sa.String(255)),
        sa.Column("last_run_at", sa.DateTime(timezone=True)),
        sa.Column("last_run_id", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("connector", "job", name="uq_ingest_state_connector_job"),
    )

    op.create_table(
        "coverage_registry",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("connector", sa.String(100), nullable=False),
        sa.Column("job", sa.String(100), nullable=False),
        sa.Column("domain", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
        sa.Column("freshness_lag_hours", sa.Float),
        sa.Column("total_items", sa.BigInteger, server_default="0"),
        sa.Column("period_start", sa.DateTime(timezone=True)),
        sa.Column("period_end", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("connector", "job", name="uq_coverage_registry_connector_job"),
    )


def downgrade() -> None:
    op.drop_table("coverage_registry")
    op.drop_table("ingest_state")
