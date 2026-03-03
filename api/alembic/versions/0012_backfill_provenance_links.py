"""Backfill provenance link tables from existing data.

Populates event_raw_source, entity_raw_source, signal_event, signal_entity
by joining existing tables. All statements use ON CONFLICT DO NOTHING
so this migration is idempotent and safe to re-run.

Revision ID: 0012
Revises: 0011
Create Date: 2026-03-03
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. event_raw_source: JOIN event to raw_source on (source_connector, raw_id)
    op.execute("""
        INSERT INTO event_raw_source (event_id, raw_source_id)
        SELECT DISTINCT e.id, rs.id
        FROM event e
        JOIN raw_source rs ON rs.connector = e.source_connector
                          AND rs.raw_id = e.source_id
        ON CONFLICT ON CONSTRAINT uq_event_raw_source DO NOTHING;
    """)

    # 2. entity_raw_source: JOIN through event_participant + event_raw_source
    op.execute("""
        INSERT INTO entity_raw_source (entity_id, raw_source_id)
        SELECT DISTINCT ep.entity_id, ers.raw_source_id
        FROM event_participant ep
        JOIN event_raw_source ers ON ers.event_id = ep.event_id
        ON CONFLICT ON CONSTRAINT uq_entity_raw_source DO NOTHING;
    """)

    # 3. signal_event: Extract from risk_signal.event_ids JSONB array
    op.execute("""
        INSERT INTO signal_event (signal_id, event_id)
        SELECT rs.id, (elem::text)::uuid
        FROM risk_signal rs,
             jsonb_array_elements(rs.event_ids) AS elem
        WHERE jsonb_typeof(rs.event_ids) = 'array'
          AND jsonb_array_length(rs.event_ids) > 0
        ON CONFLICT ON CONSTRAINT uq_signal_event DO NOTHING;
    """)

    # 4. signal_entity: Extract from risk_signal.entity_ids JSONB array
    op.execute("""
        INSERT INTO signal_entity (signal_id, entity_id)
        SELECT rs.id, (elem::text)::uuid
        FROM risk_signal rs,
             jsonb_array_elements(rs.entity_ids) AS elem
        WHERE jsonb_typeof(rs.entity_ids) = 'array'
          AND jsonb_array_length(rs.entity_ids) > 0
        ON CONFLICT ON CONSTRAINT uq_signal_entity DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("TRUNCATE event_raw_source, entity_raw_source, signal_event, signal_entity;")
