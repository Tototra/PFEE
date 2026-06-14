-- ============================================================================
-- Coach IA GTB — Schéma TimescaleDB
-- ============================================================================
-- À exécuter sur une instance PostgreSQL 16 + extension TimescaleDB.
-- Les tables relationnelles (sites, equipments, points, ...) sont créées par
-- SQLAlchemy / Alembic. Ce fichier configure UNIQUEMENT les hypertables
-- temporelles et les agrégats continus, qui ne sont pas gérés par l'ORM.
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- ─── Hypertable : measurements ──────────────────────────────────────────────
-- Stocke toutes les mesures GTB (températures, consignes, états, index...)
-- Partitionnement par chunk d'1 jour.

CREATE TABLE IF NOT EXISTS measurements (
    point_id  UUID NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    value     DOUBLE PRECISION NOT NULL,
    quality   VARCHAR(20) DEFAULT 'good',
    PRIMARY KEY (point_id, timestamp)
);

SELECT create_hypertable(
    'measurements',
    'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS ix_measurements_point_ts
    ON measurements (point_id, timestamp DESC);

-- ─── Hypertable : alarm_events ──────────────────────────────────────────────
-- Stocke l'historique des changements d'état des alarmes.

CREATE TABLE IF NOT EXISTS alarm_events (
    alarm_id   UUID NOT NULL,
    timestamp  TIMESTAMPTZ NOT NULL,
    event_type VARCHAR(50) NOT NULL,  -- 'triggered', 'acked', 'cleared'
    point_id   UUID,
    value      DOUBLE PRECISION,
    metadata   JSONB DEFAULT '{}'::jsonb,
    PRIMARY KEY (alarm_id, timestamp, event_type)
);

SELECT create_hypertable(
    'alarm_events',
    'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS ix_alarm_events_ts
    ON alarm_events (timestamp DESC);

-- ─── Politique de rétention ─────────────────────────────────────────────────
-- Brut : 90 jours
-- Agrégats : conservés 2 ans

SELECT add_retention_policy('measurements', INTERVAL '90 days', if_not_exists => TRUE);
SELECT add_retention_policy('alarm_events', INTERVAL '2 years', if_not_exists => TRUE);

-- ─── Continuous aggregate : moyennes horaires ───────────────────────────────
-- Optimise les requêtes de visualisation graphiques sur 7/30/365j.

CREATE MATERIALIZED VIEW IF NOT EXISTS measurements_hourly
WITH (timescaledb.continuous) AS
SELECT
    point_id,
    time_bucket(INTERVAL '1 hour', timestamp) AS bucket,
    AVG(value)  AS avg_value,
    MIN(value)  AS min_value,
    MAX(value)  AS max_value,
    COUNT(*)    AS n_samples
FROM measurements
GROUP BY point_id, bucket
WITH NO DATA;

SELECT add_continuous_aggregate_policy(
    'measurements_hourly',
    start_offset      => INTERVAL '7 days',
    end_offset        => INTERVAL '1 hour',
    schedule_interval => INTERVAL '30 minutes',
    if_not_exists     => TRUE
);

-- ─── Continuous aggregate : moyennes journalières ───────────────────────────

CREATE MATERIALIZED VIEW IF NOT EXISTS measurements_daily
WITH (timescaledb.continuous) AS
SELECT
    point_id,
    time_bucket(INTERVAL '1 day', timestamp) AS bucket,
    AVG(value)  AS avg_value,
    MIN(value)  AS min_value,
    MAX(value)  AS max_value,
    COUNT(*)    AS n_samples
FROM measurements
GROUP BY point_id, bucket
WITH NO DATA;

SELECT add_continuous_aggregate_policy(
    'measurements_daily',
    start_offset      => INTERVAL '90 days',
    end_offset        => INTERVAL '1 day',
    schedule_interval => INTERVAL '6 hours',
    if_not_exists     => TRUE
);

-- ─── Compression (économise stockage à long terme) ──────────────────────────

ALTER TABLE measurements SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'point_id',
    timescaledb.compress_orderby = 'timestamp DESC'
);

SELECT add_compression_policy('measurements', INTERVAL '7 days', if_not_exists => TRUE);
