"""Add reference_data table for dimension keys and static lookups

Stores IBGE municipalities, SIAPE organs, CNAE codes, etc.
Used by dimension-keyed ingest jobs (pt_servidores_remuneracao, pt_beneficios)
to iterate over external dimension keys without runtime API dependencies.

Revision ID: 0010
Revises: 0009
Create Date: 2026-03-03
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reference_data",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("parent_code", sa.String(50), nullable=True),
        sa.Column("attrs", JSONB, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("category", "code", name="uq_reference_data_category_code"),
    )

    op.create_index("ix_reference_data_category", "reference_data", ["category"])


def downgrade() -> None:
    op.drop_index("ix_reference_data_category", table_name="reference_data")
    op.drop_table("reference_data")
