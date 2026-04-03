"""Add robustness foundations: evidence packages, completeness, edge verification, contestations.

Revision ID: 0007
Revises: 0006
Create Date: 2026-03-02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "evidence_package",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("source_url", sa.Text),
        sa.Column("source_hash", sa.String(128)),
        sa.Column("captured_at", sa.DateTime(timezone=True)),
        sa.Column("parser_version", sa.String(100)),
        sa.Column("model_version", sa.String(100)),
        sa.Column("raw_snapshot_uri", sa.Text),
        sa.Column("normalized_snapshot_uri", sa.Text),
        sa.Column("signature", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_evidence_package_captured_at",
        "evidence_package",
        ["captured_at"],
    )
    op.create_index(
        "ix_evidence_package_signature",
        "evidence_package",
        ["signature"],
    )

    op.add_column(
        "risk_signal",
        sa.Column("completeness_score", sa.Float(), server_default="0", nullable=False),
    )
    op.add_column(
        "risk_signal",
        sa.Column("completeness_status", sa.String(20), server_default="insufficient", nullable=False),
    )
    op.add_column(
        "risk_signal",
        sa.Column("evidence_package_id", UUID(as_uuid=True), sa.ForeignKey("evidence_package.id"), nullable=True),
    )
    op.create_index(
        "ix_risk_signal_completeness",
        "risk_signal",
        ["completeness_status", "completeness_score"],
    )

    op.add_column(
        "graph_edge",
        sa.Column("edge_strength", sa.String(20), server_default="weak", nullable=False),
    )
    op.add_column("graph_edge", sa.Column("verification_method", sa.String(100), nullable=True))
    op.add_column("graph_edge", sa.Column("verification_confidence", sa.Float(), nullable=True))
    op.create_index("ix_graph_edge_strength", "graph_edge", ["edge_strength"])

    op.create_table(
        "contestation",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("signal_id", UUID(as_uuid=True), sa.ForeignKey("risk_signal.id"), nullable=True),
        sa.Column("status", sa.String(20), server_default="open", nullable=False),
        sa.Column("requester_name", sa.String(255), nullable=False),
        sa.Column("requester_email", sa.String(255), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("details", JSONB, server_default="{}", nullable=False),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_contestation_signal_status",
        "contestation",
        ["signal_id", "status"],
    )
    op.create_index("ix_contestation_created_at", "contestation", ["created_at"])

    # Remove transitional server defaults while keeping values for existing rows.
    op.alter_column("risk_signal", "completeness_score", server_default=None)
    op.alter_column("risk_signal", "completeness_status", server_default=None)
    op.alter_column("graph_edge", "edge_strength", server_default=None)
    op.alter_column("contestation", "status", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_contestation_created_at", table_name="contestation")
    op.drop_index("ix_contestation_signal_status", table_name="contestation")
    op.drop_table("contestation")

    op.drop_index("ix_graph_edge_strength", table_name="graph_edge")
    op.drop_column("graph_edge", "verification_confidence")
    op.drop_column("graph_edge", "verification_method")
    op.drop_column("graph_edge", "edge_strength")

    op.drop_index("ix_risk_signal_completeness", table_name="risk_signal")
    op.drop_column("risk_signal", "evidence_package_id")
    op.drop_column("risk_signal", "completeness_status")
    op.drop_column("risk_signal", "completeness_score")

    op.drop_index("ix_evidence_package_signature", table_name="evidence_package")
    op.drop_index("ix_evidence_package_captured_at", table_name="evidence_package")
    op.drop_table("evidence_package")
