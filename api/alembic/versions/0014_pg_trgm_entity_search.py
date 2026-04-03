"""Add pg_trgm extension and trigram index on entity.name_normalized for fuzzy search.

Revision ID: 0014
Revises: 0013
Create Date: 2026-03-04
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_entity_name_normalized_trgm
        ON entity USING gin (name_normalized gin_trgm_ops)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_entity_name_normalized_trgm")
