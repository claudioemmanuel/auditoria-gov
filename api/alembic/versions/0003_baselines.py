"""Add baseline_snapshot table

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "baseline_snapshot",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("baseline_type", sa.String(50), nullable=False),
        sa.Column("scope_key", sa.String(255), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sample_size", sa.Integer, nullable=False),
        sa.Column("metrics", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "baseline_type", "scope_key", "window_start", "window_end",
            name="uq_baseline_snapshot",
        ),
    )


def downgrade() -> None:
    op.drop_table("baseline_snapshot")
