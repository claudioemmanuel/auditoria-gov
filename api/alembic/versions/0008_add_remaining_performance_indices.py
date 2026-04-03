"""Add remaining performance indices for hot queries

Adds indices not already covered by migration 0004 or ORM-defined
table_args.  Targets typology filtering, coverage map aggregation,
and monitoring hot paths.

NOTE: These indices use standard CREATE INDEX (not CONCURRENTLY)
because Alembic runs inside a transaction by default. For zero-
downtime production deploys, run the CONCURRENTLY variants manually
before applying this migration.

Revision ID: 0008
Revises: 0007
Create Date: 2026-03-02
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── EventParticipant: reverse-direction lookup (role, entity_id) ──
    # Existing ix_event_participant_entity_role is (entity_id, role);
    # this covers queries that filter by role first.
    op.create_index(
        "ix_event_participant_role_entity",
        "event_participant",
        ["role", "entity_id"],
    )

    # ── Event: covering index for typology time-range scans ──────────
    # Existing ix_event_type_occurred_at is (type, occurred_at);
    # adding id makes it a covering index for SELECT id queries.
    op.create_index(
        "ix_event_type_occurred_at_id",
        "event",
        ["type", "occurred_at", "id"],
    )

    # ── Event attrs: GIN index on JSONB for coverage map UF lookups ──
    op.execute(
        "CREATE INDEX ix_event_attrs_uf "
        "ON event ((attrs->>'uf')) "
        "WHERE attrs->>'uf' IS NOT NULL AND attrs->>'uf' != ''"
    )

    # ── RiskSignal: created_at descending for radar pagination ───────
    op.create_index(
        "ix_risk_signal_created_at_desc",
        "risk_signal",
        ["created_at"],
        postgresql_using="btree",
    )

    # ── CaseItem: case_id for case detail eager loading ──────────────
    op.create_index(
        "ix_case_item_case_id",
        "case_item",
        ["case_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_case_item_case_id", table_name="case_item")
    op.drop_index("ix_risk_signal_created_at_desc", table_name="risk_signal")
    op.execute("DROP INDEX IF EXISTS ix_event_attrs_uf")
    op.drop_index("ix_event_type_occurred_at_id", table_name="event")
    op.drop_index("ix_event_participant_role_entity", table_name="event_participant")
