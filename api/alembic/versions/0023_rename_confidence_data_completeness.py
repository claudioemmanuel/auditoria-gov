"""rename_confidence_to_data_completeness

Revision ID: 0023
Revises: 0022
Create Date: 2026-03-23 15:00:00.000000
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("risk_signal", "confidence", new_column_name="data_completeness")


def downgrade() -> None:
    op.alter_column("risk_signal", "data_completeness", new_column_name="confidence")
