"""signal_confidence_score

Revision ID: 0022
Revises: 0021
Create Date: 2026-03-23 14:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers
revision: str = "0022"
down_revision: Union[str, None] = "0021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "risk_signal",
        sa.Column(
            "signal_confidence_score",
            sa.Integer(),
            sa.CheckConstraint("signal_confidence_score BETWEEN 0 AND 100"),
            nullable=True,
        ),
    )
    op.add_column(
        "risk_signal",
        sa.Column("confidence_factors", JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("risk_signal", "confidence_factors")
    op.drop_column("risk_signal", "signal_confidence_score")
