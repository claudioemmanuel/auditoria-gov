"""Add typology_run_log table for per-run execution metrics

Tracks when each typology last ran, how many candidates it evaluated,
and what happened to them (created, deduped, blocked, errored).
Enables analytical coverage transparency: users can distinguish
"typology ran and found nothing" from "typology couldn't run."

Revision ID: 0009
Revises: 0008
Create Date: 2026-03-02
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "typology_run_log",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("typology_code", sa.String(10), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("candidates", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("signals_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("signals_deduped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("signals_blocked", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text()),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_typology_run_log_code_started",
        "typology_run_log",
        ["typology_code", "started_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_typology_run_log_code_started", table_name="typology_run_log")
    op.drop_table("typology_run_log")
