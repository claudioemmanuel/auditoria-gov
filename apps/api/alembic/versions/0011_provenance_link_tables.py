"""Add provenance link tables: event_raw_source, entity_raw_source,
signal_event, signal_entity.

These M2M tables enable full provenance tracing:
  Signal → Events → RawSources (original API JSON)
  Signal → Entities → RawSources

Also adds composite index on raw_source(connector, raw_id) for
efficient joins during backfill.

Revision ID: 0011
Revises: 0010
Create Date: 2026-03-03
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── event_raw_source ─────────────────────────────────────────────
    op.create_table(
        "event_raw_source",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "event_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("event.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "raw_source_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("raw_source.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("event_id", "raw_source_id", name="uq_event_raw_source"),
    )
    op.create_index("ix_event_raw_source_event", "event_raw_source", ["event_id"])
    op.create_index(
        "ix_event_raw_source_raw_source", "event_raw_source", ["raw_source_id"]
    )

    # ── entity_raw_source ────────────────────────────────────────────
    op.create_table(
        "entity_raw_source",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "entity_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("entity.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "raw_source_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("raw_source.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "entity_id", "raw_source_id", name="uq_entity_raw_source"
        ),
    )
    op.create_index("ix_entity_raw_source_entity", "entity_raw_source", ["entity_id"])
    op.create_index(
        "ix_entity_raw_source_raw_source", "entity_raw_source", ["raw_source_id"]
    )

    # ── signal_event ─────────────────────────────────────────────────
    op.create_table(
        "signal_event",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "signal_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("risk_signal.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "event_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("event.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("signal_id", "event_id", name="uq_signal_event"),
    )
    op.create_index("ix_signal_event_signal", "signal_event", ["signal_id"])
    op.create_index("ix_signal_event_event", "signal_event", ["event_id"])

    # ── signal_entity ────────────────────────────────────────────────
    op.create_table(
        "signal_entity",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "signal_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("risk_signal.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "entity_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("entity.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("signal_id", "entity_id", name="uq_signal_entity"),
    )
    op.create_index("ix_signal_entity_signal", "signal_entity", ["signal_id"])
    op.create_index("ix_signal_entity_entity", "signal_entity", ["entity_id"])

    # ── Composite index on raw_source for provenance joins ───────────
    op.create_index(
        "ix_raw_source_connector_raw_id",
        "raw_source",
        ["connector", "raw_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_raw_source_connector_raw_id", table_name="raw_source")

    op.drop_index("ix_signal_entity_entity", table_name="signal_entity")
    op.drop_index("ix_signal_entity_signal", table_name="signal_entity")
    op.drop_table("signal_entity")

    op.drop_index("ix_signal_event_event", table_name="signal_event")
    op.drop_index("ix_signal_event_signal", table_name="signal_event")
    op.drop_table("signal_event")

    op.drop_index("ix_entity_raw_source_raw_source", table_name="entity_raw_source")
    op.drop_index("ix_entity_raw_source_entity", table_name="entity_raw_source")
    op.drop_table("entity_raw_source")

    op.drop_index("ix_event_raw_source_raw_source", table_name="event_raw_source")
    op.drop_index("ix_event_raw_source_event", table_name="event_raw_source")
    op.drop_table("event_raw_source")
