-- Event schema v1 (docs/fyp2-plan, shared contract 1). Every row: a stable event_id, the run that wrote it,
-- store/camera/zone, and a UTC ISO-8601 time span (ts_end = ts_start for instants). Rows are rewritten per run_id.

CREATE TABLE IF NOT EXISTS tracks (
  event_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, store_id TEXT NOT NULL, camera_id TEXT NOT NULL,
  zone_id TEXT NOT NULL, ts_start TIMESTAMPTZ NOT NULL, ts_end TIMESTAMPTZ NOT NULL,
  track_id INTEGER NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('employee', 'customer', 'unknown')),
  employee_score DOUBLE PRECISION,
  frames_observed INTEGER NOT NULL
);

-- One row per held role segment of a track; several segments on one track expose an ID swap.
CREATE TABLE IF NOT EXISTS role_decisions (
  event_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, store_id TEXT NOT NULL, camera_id TEXT NOT NULL,
  zone_id TEXT NOT NULL, ts_start TIMESTAMPTZ NOT NULL, ts_end TIMESTAMPTZ NOT NULL,
  track_id INTEGER NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('employee', 'customer', 'unknown')),
  frames INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS interactions (
  event_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, store_id TEXT NOT NULL, camera_id TEXT NOT NULL,
  zone_id TEXT NOT NULL, ts_start TIMESTAMPTZ NOT NULL, ts_end TIMESTAMPTZ NOT NULL,
  employee_track_id INTEGER NOT NULL,
  customer_track_id INTEGER NOT NULL,
  duration_s DOUBLE PRECISION NOT NULL,
  verdict TEXT NOT NULL  -- interaction (pose judge confirmed) | unverified (proximity only)
);

CREATE TABLE IF NOT EXISTS zone_dwell (
  event_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, store_id TEXT NOT NULL, camera_id TEXT NOT NULL,
  zone_id TEXT NOT NULL, ts_start TIMESTAMPTZ NOT NULL, ts_end TIMESTAMPTZ NOT NULL,
  track_id INTEGER NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('employee', 'customer', 'unknown')),
  dwell_s DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS footfall (
  event_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, store_id TEXT NOT NULL, camera_id TEXT NOT NULL,
  zone_id TEXT NOT NULL, ts_start TIMESTAMPTZ NOT NULL, ts_end TIMESTAMPTZ NOT NULL,
  track_id INTEGER NOT NULL,
  direction TEXT NOT NULL CHECK (direction IN ('in', 'out'))
);

CREATE TABLE IF NOT EXISTS queue_samples (
  event_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, store_id TEXT NOT NULL, camera_id TEXT NOT NULL,
  zone_id TEXT NOT NULL, ts_start TIMESTAMPTZ NOT NULL, ts_end TIMESTAMPTZ NOT NULL,
  queue_length INTEGER NOT NULL,
  est_wait_s DOUBLE PRECISION
);

-- Derived, never written by the CV stages: a customer who waited over N seconds before any confirmed interaction.
CREATE TABLE IF NOT EXISTS unattended_episodes (
  event_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, store_id TEXT NOT NULL, camera_id TEXT NOT NULL,
  zone_id TEXT NOT NULL, ts_start TIMESTAMPTZ NOT NULL, ts_end TIMESTAMPTZ NOT NULL,
  customer_track_id INTEGER NOT NULL,
  waited_s DOUBLE PRECISION NOT NULL,
  helped INTEGER NOT NULL  -- 1 when an interaction ended the wait, 0 when the customer left unhelped
);

-- Per camera per minute.
CREATE TABLE IF NOT EXISTS pipeline_health (
  event_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, store_id TEXT NOT NULL, camera_id TEXT NOT NULL,
  zone_id TEXT NOT NULL, ts_start TIMESTAMPTZ NOT NULL, ts_end TIMESTAMPTZ NOT NULL,
  fps DOUBLE PRECISION NOT NULL,
  mean_confidence DOUBLE PRECISION,           -- NULL when no detections in the minute
  unknown_role_share DOUBLE PRECISION,
  id_churn INTEGER NOT NULL,      -- track IDs first seen in this minute
  frozen_or_dark INTEGER          -- NULL until the frame check (B4.5) runs
);

-- Additive to v1: foot-point counts per camera per wall-clock hour, cells = JSON rows x cols grid over the frame.
CREATE TABLE IF NOT EXISTS heatmaps (
  event_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, store_id TEXT NOT NULL, camera_id TEXT NOT NULL,
  zone_id TEXT NOT NULL, ts_start TIMESTAMPTZ NOT NULL, ts_end TIMESTAMPTZ NOT NULL,
  cols INTEGER NOT NULL,
  rows INTEGER NOT NULL,
  cells TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS tracks_szt ON tracks(store_id, zone_id, ts_start);
CREATE INDEX IF NOT EXISTS role_decisions_szt ON role_decisions(store_id, zone_id, ts_start);
CREATE INDEX IF NOT EXISTS interactions_szt ON interactions(store_id, zone_id, ts_start);
CREATE INDEX IF NOT EXISTS zone_dwell_szt ON zone_dwell(store_id, zone_id, ts_start);
CREATE INDEX IF NOT EXISTS footfall_szt ON footfall(store_id, zone_id, ts_start);
CREATE INDEX IF NOT EXISTS queue_samples_szt ON queue_samples(store_id, zone_id, ts_start);
CREATE INDEX IF NOT EXISTS unattended_episodes_szt ON unattended_episodes(store_id, zone_id, ts_start);
CREATE INDEX IF NOT EXISTS pipeline_health_szt ON pipeline_health(store_id, zone_id, ts_start);
CREATE INDEX IF NOT EXISTS heatmaps_szt ON heatmaps(store_id, zone_id, ts_start);
CREATE INDEX IF NOT EXISTS tracks_run ON tracks(run_id);

CREATE INDEX IF NOT EXISTS role_decisions_run ON role_decisions(run_id);
CREATE INDEX IF NOT EXISTS interactions_run ON interactions(run_id);
CREATE INDEX IF NOT EXISTS zone_dwell_run ON zone_dwell(run_id);
CREATE INDEX IF NOT EXISTS footfall_run ON footfall(run_id);
CREATE INDEX IF NOT EXISTS queue_samples_run ON queue_samples(run_id);
CREATE INDEX IF NOT EXISTS unattended_episodes_run ON unattended_episodes(run_id);
CREATE INDEX IF NOT EXISTS pipeline_health_run ON pipeline_health(run_id);
CREATE INDEX IF NOT EXISTS heatmaps_run ON heatmaps(run_id);
