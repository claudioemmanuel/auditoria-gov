"""Add case_type and case_category columns to case table.

Revision ID: 0019
Revises: 0018
Create Date: 2026-03-10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0019"
down_revision: Union[str, None] = "0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("case", sa.Column("case_type", sa.String(50), nullable=True))
    op.add_column("case", sa.Column("case_category", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("case", "case_category")
    op.drop_column("case", "case_type")
