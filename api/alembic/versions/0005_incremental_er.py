"""Add incremental ER support: entity.er_processed_at + er_run_state table

Allows entity resolution to only process entities that changed since the
last ER cycle, converting ER from O(all_entities) to O(delta_entities).

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Track when each entity was last processed by ER.
    op.add_column(
        "entity",
        sa.Column("er_processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_entity_er_processed_at",
        "entity",
        ["er_processed_at"],
    )

    # ER run state — persists watermark across runs.
    op.create_table(
        "er_run_state",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("entities_processed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("deterministic_matches", sa.Integer, nullable=False, server_default="0"),
        sa.Column("probabilistic_matches", sa.Integer, nullable=False, server_default="0"),
        sa.Column("clusters_formed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("edges_created", sa.Integer, nullable=False, server_default="0"),
        sa.Column("watermark_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("er_run_state")
    op.drop_index("ix_entity_er_processed_at", table_name="entity")
    op.drop_column("entity", "er_processed_at")
