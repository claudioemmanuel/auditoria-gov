"""Add performance indexes for hot worker paths

Converts O(n) sequential scans to O(log n) index lookups on upsert,
normalization, ER matching, and operational monitoring queries.

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-02
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── Event dedup (upsert_event_sync hot path) ─────────────────────
    op.create_unique_constraint(
        "uq_event_source",
        "event",
        ["source_connector", "source_id"],
    )

    # ── EventParticipant dedup (upsert_participant_sync hot path) ────
    op.create_unique_constraint(
        "uq_event_participant_triplet",
        "event_participant",
        ["event_id", "entity_id", "role"],
    )

    # ── EventParticipant queries by event+role (typology filtering) ──
    op.create_index(
        "ix_event_participant_event_role",
        "event_participant",
        ["event_id", "role"],
    )

    # ── Entity identifier lookups (ER matching on CPF / CPF hash) ────
    op.execute(
        "CREATE INDEX ix_entity_identifiers_cpf "
        "ON entity ((identifiers->>'cpf')) "
        "WHERE identifiers->>'cpf' IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX ix_entity_identifiers_cpf_hash "
        "ON entity ((identifiers->>'cpf_hash')) "
        "WHERE identifiers->>'cpf_hash' IS NOT NULL"
    )

    # ── Entity fallback name matching (org/company upsert) ───────────
    op.create_index(
        "ix_entity_type_name_norm",
        "entity",
        ["type", "name_normalized"],
    )

    # ── Entity cluster_id for ER queries ─────────────────────────────
    op.create_index(
        "ix_entity_cluster_id",
        "entity",
        ["cluster_id"],
        postgresql_where=sa.text("cluster_id IS NOT NULL"),
    )

    # ── RawSource: normalize_run fetches un-normalized items by run ──
    op.create_index(
        "ix_raw_source_run_normalized",
        "raw_source",
        ["run_id", "normalized"],
    )

    # ── RawSource: coverage metrics per connector/job ────────────────
    op.create_index(
        "ix_raw_source_connector_job",
        "raw_source",
        ["connector", "job"],
    )

    # ── RawRun: operational monitoring & stale detection ─────────────
    op.create_index(
        "ix_raw_run_connector_job_status",
        "raw_run",
        ["connector", "job", "status", sa.text("finished_at DESC")],
    )

    # ── GraphEdge: dedup (ER edge upsert) ────────────────────────────
    op.create_unique_constraint(
        "uq_graph_edge_triplet",
        "graph_edge",
        ["from_node_id", "to_node_id", "type"],
    )

    # ── Case: listing/filtering ──────────────────────────────────────
    op.create_index(
        "ix_case_status_severity",
        "case",
        ["status", "severity"],
    )

    # ── CaseItem: signal-to-case backlinks ───────────────────────────
    op.create_index(
        "ix_case_item_signal_id",
        "case_item",
        ["signal_id"],
    )

    # ── TextCorpus: evidence lookup ──────────────────────────────────
    op.create_index(
        "ix_text_corpus_source",
        "text_corpus",
        ["source_type", "source_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_text_corpus_source", table_name="text_corpus")
    op.drop_index("ix_case_item_signal_id", table_name="case_item")
    op.drop_index("ix_case_status_severity", table_name="case")
    op.drop_constraint("uq_graph_edge_triplet", "graph_edge", type_="unique")
    op.drop_index("ix_raw_run_connector_job_status", table_name="raw_run")
    op.drop_index("ix_raw_source_connector_job", table_name="raw_source")
    op.drop_index("ix_raw_source_run_normalized", table_name="raw_source")
    op.drop_index("ix_entity_cluster_id", table_name="entity")
    op.drop_index("ix_entity_type_name_norm", table_name="entity")
    op.execute("DROP INDEX IF EXISTS ix_entity_identifiers_cpf_hash")
    op.execute("DROP INDEX IF EXISTS ix_entity_identifiers_cpf")
    op.drop_index("ix_event_participant_event_role", table_name="event_participant")
    op.drop_constraint("uq_event_participant_triplet", "event_participant", type_="unique")
    op.drop_constraint("uq_event_source", "event", type_="unique")
