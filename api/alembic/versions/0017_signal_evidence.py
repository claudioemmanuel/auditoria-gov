"""Add signal_evidence table for structured per-field evidence rows.

Revision ID: 0017
Revises: 0016
Create Date: 2026-03-10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0017"
down_revision: Union[str, None] = "0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "signal_evidence",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "signal_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("risk_signal.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("dataset", sa.Text(), nullable=False),
        sa.Column("record_id", sa.Text(), nullable=False),
        sa.Column("field_name", sa.Text(), nullable=True),
        sa.Column("field_value", sa.Text(), nullable=True),
        sa.Column("reference_url", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_signal_evidence_signal", "signal_evidence", ["signal_id"])


def downgrade() -> None:
    op.drop_index("ix_signal_evidence_signal", table_name="signal_evidence")
    op.drop_table("signal_evidence")
