"""Add yield_requested column to ingest_state

Revision ID: 0015
Revises: 0014
Create Date: 2026-03-06
"""

import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ingest_state",
        sa.Column("yield_requested", sa.Boolean(), server_default="false", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("ingest_state", "yield_requested")
