"""Add source veracity and compliance columns to coverage_registry.

All columns are nullable — safe for zero-downtime deploy.

Revision ID: 0013
Revises: 0012
Create Date: 2026-03-04
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("coverage_registry", sa.Column("veracity_score", sa.Float(), nullable=True))
    op.add_column("coverage_registry", sa.Column("veracity_label", sa.String(20), nullable=True))
    op.add_column("coverage_registry", sa.Column("domain_tier", sa.String(50), nullable=True))
    op.add_column(
        "coverage_registry",
        sa.Column("last_compliance_check_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("coverage_registry", sa.Column("compliance_status", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("coverage_registry", "compliance_status")
    op.drop_column("coverage_registry", "last_compliance_check_at")
    op.drop_column("coverage_registry", "domain_tier")
    op.drop_column("coverage_registry", "veracity_label")
    op.drop_column("coverage_registry", "veracity_score")
