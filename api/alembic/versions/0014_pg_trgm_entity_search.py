"""Add pg_trgm extension and trigram index on entity.name_normalized for fuzzy search.

Revision ID: 0014
Revises: 0013
Create Date: 2026-03-04
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_entity_name_normalized_trgm
        ON entity USING gin (name_normalized gin_trgm_ops)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_entity_name_normalized_trgm")
