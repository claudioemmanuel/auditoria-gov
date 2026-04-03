"""contestation_extend

Revision ID: 0024
Revises: 0023
Create Date: 2026-03-23 16:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "contestation",
        sa.Column("entity_id", sa.UUID(as_uuid=True), sa.ForeignKey("entity.id"), nullable=True),
    )
    op.add_column(
        "contestation",
        sa.Column("report_type", sa.String(50), nullable=False, server_default="signal_error"),
    )
    op.add_column(
        "contestation",
        sa.Column("evidence_url", sa.String(2048), nullable=True),
    )
    op.create_index("ix_contestation_entity_status", "contestation", ["entity_id", "status"])
    op.create_check_constraint(
        "ck_contestation_has_target",
        "contestation",
        "signal_id IS NOT NULL OR entity_id IS NOT NULL",
    )
    op.create_check_constraint(
        "ck_contestation_report_type",
        "contestation",
        "report_type IN ('signal_error','entity_error','duplicate','other')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_contestation_report_type", "contestation")
    op.drop_constraint("ck_contestation_has_target", "contestation")
    op.drop_index("ix_contestation_entity_status", "contestation")
    op.drop_column("contestation", "evidence_url")
    op.drop_column("contestation", "report_type")
    op.drop_column("contestation", "entity_id")
