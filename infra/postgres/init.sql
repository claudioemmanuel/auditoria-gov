CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Aggressive autovacuum for high-churn raw_source table.
-- This runs as an init script; raw_source may not exist yet on first boot.
-- The ALTER TABLE will apply on subsequent restarts after Alembic creates the table.
-- If the table does not exist, the DO block silently succeeds.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'raw_source') THEN
        EXECUTE 'ALTER TABLE raw_source SET (
            autovacuum_vacuum_scale_factor = 0.01,
            autovacuum_analyze_scale_factor = 0.005,
            autovacuum_vacuum_cost_delay = 2
        )';
    END IF;
END
$$;
