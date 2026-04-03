"""Add dedup_key to risk_signal for signal deduplication

Prevents duplicate signals across runs for the same
(typology, entities, period) combination.

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "risk_signal",
        sa.Column("dedup_key", sa.String(64), nullable=True),
    )
    op.create_index(
        "uq_risk_signal_dedup_key",
        "risk_signal",
        ["dedup_key"],
        unique=True,
        postgresql_where=sa.text("dedup_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_risk_signal_dedup_key", table_name="risk_signal")
    op.drop_column("risk_signal", "dedup_key")
