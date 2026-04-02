"""Add legal_violation_hypothesis table for AI-generated legal analysis per case.

Revision ID: 0018
Revises: 0017
Create Date: 2026-03-10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY

revision: str = "0018"
down_revision: Union[str, None] = "0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "legal_violation_hypothesis",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "case_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("case.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "signal_cluster",
            ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("law_name", sa.Text(), nullable=False),
        sa.Column("article", sa.Text(), nullable=True),
        sa.Column("violation_type", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "case_id", "law_name", "article", name="uq_legal_hypothesis_case_law"
        ),
    )
    op.create_index(
        "ix_legal_hypothesis_case", "legal_violation_hypothesis", ["case_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_legal_hypothesis_case", table_name="legal_violation_hypothesis")
    op.drop_table("legal_violation_hypothesis")
