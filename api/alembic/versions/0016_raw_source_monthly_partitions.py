"""Convert raw_source to monthly-partitioned table for fast purge via DROP PARTITION.

Revision ID: 0016
Revises: 0015
Create Date: 2026-03-09

# WHY THIS MIGRATION EXISTS
#
# raw_source is a high-churn staging table: ingest writes millions of rows,
# normalize deletes them.  The current setup uses DELETE + VACUUM, which is
# slow and leaves bloat.  A partitioned table enables:
#
#   DROP TABLE raw_source_2026_03;  -- instant, no bloat
#
# instead of:
#
#   DELETE FROM raw_source WHERE created_at < '2026-04-01';  -- minutes + bloat
#
# APPROACH: Declarative partitioning by RANGE on created_at (monthly partitions).
# Partitions are pre-created 1 month ahead by a maintenance task.
# Old partitions (> retention window) are dropped atomically.
#
# CUTOVER PROCEDURE (safe, zero-downtime):
#
#   1. Pause ingest workers (set disk:throttle=1 in Redis temporarily).
#   2. Run this migration:
#      a. Rename raw_source → raw_source_legacy
#      b. Create raw_source_partitioned (partitioned by created_at)
#      c. Create initial partitions for current month + ±1 month buffer
#      d. Copy rows from raw_source_legacy → raw_source_partitioned (in batches)
#      e. Rename raw_source_partitioned → raw_source
#      f. DROP raw_source_legacy (or keep for rollback window)
#   3. Resume ingest workers.
#   4. Update purge logic to DROP PARTITION instead of DELETE.
#
# CURRENT STATUS: STUB — not yet executed.
# This file documents the planned migration.  Run only after:
#   - Testing the cutover in a staging environment
#   - Verifying all FK references to raw_source are compatible with partitioned tables
#   - Confirming entity_raw_source and event_raw_source FK behavior with partitions
#   - Scheduling a maintenance window (cutover takes ~10-30 min for current data)
#
# POSTGRES LIMITATION: Foreign keys referencing partitioned tables require PG ≥ 12
# and FK must reference the partition key OR the whole table.
# Check: entity_raw_source.raw_source_id → raw_source.id
#        event_raw_source.raw_source_id → raw_source.id
# These should work in PG 17 (our version).
"""


# revision identifiers, used by Alembic.
revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # STUB: Not executed automatically.
    # Full implementation below is provided as reference DDL only.
    #
    # See docstring above for safe cutover procedure.
    pass

    # ── Reference DDL (do NOT run directly via Alembic without the cutover procedure) ──
    #
    # -- Step 1: Create new partitioned table
    # CREATE TABLE raw_source_partitioned (
    #     id UUID NOT NULL,
    #     run_id UUID NOT NULL,
    #     connector VARCHAR(100) NOT NULL,
    #     job VARCHAR(100) NOT NULL,
    #     raw_id VARCHAR(255) NOT NULL,
    #     raw_data JSONB NOT NULL,
    #     normalized BOOLEAN DEFAULT FALSE,
    #     created_at TIMESTAMPTZ DEFAULT NOW(),
    #     updated_at TIMESTAMPTZ DEFAULT NOW(),
    #     PRIMARY KEY (id, created_at)  -- partition key must be in PK
    # ) PARTITION BY RANGE (created_at);
    #
    # -- Step 2: Create initial monthly partitions
    # CREATE TABLE raw_source_2026_02 PARTITION OF raw_source_partitioned
    #     FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
    # CREATE TABLE raw_source_2026_03 PARTITION OF raw_source_partitioned
    #     FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
    # CREATE TABLE raw_source_2026_04 PARTITION OF raw_source_partitioned
    #     FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
    # CREATE TABLE raw_source_default PARTITION OF raw_source_partitioned DEFAULT;
    #
    # -- Step 3: Recreate indexes on partitioned table
    # CREATE INDEX ON raw_source_partitioned (connector, job);
    # CREATE INDEX ON raw_source_partitioned (connector, raw_id);
    # CREATE INDEX ON raw_source_partitioned (run_id, normalized);
    #
    # -- Step 4: Maintenance task to create future partitions and drop old ones
    # -- Add to worker/tasks/maintenance_tasks.py: create_monthly_partition()
    # -- Schedule monthly via Beat.
    #
    # -- Step 5: Purge becomes DROP PARTITION
    # DROP TABLE IF EXISTS raw_source_2026_01;  -- instant, no VACUUM needed


def downgrade() -> None:
    # STUB: No downgrade needed since upgrade is a no-op.
    pass
