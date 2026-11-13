CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
INSERT INTO meta(key, value) VALUES ('schema_version', '1') ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  role TEXT NOT NULL CHECK (role IN ('Manager', 'Employee')),
  password_hash TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS invitations (
  id TEXT PRIMARY KEY,
  email TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('Manager', 'Employee')),
  token TEXT NOT NULL UNIQUE,
  expires_at TEXT NOT NULL,
  accepted_at TEXT,
  created_by TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY(created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS zones (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  type TEXT NOT NULL,
  capacity INTEGER NOT NULL,
  min_staff INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cameras (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  zone_id TEXT,
  role TEXT NOT NULL DEFAULT 'floor',
  source_type TEXT NOT NULL DEFAULT 'recording',
  source_url TEXT,
  online INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(zone_id) REFERENCES zones(id)
);

CREATE TABLE IF NOT EXISTS rosters (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  zone_id TEXT,
  shift TEXT NOT NULL,
  available INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(user_id) REFERENCES users(id),
  FOREIGN KEY(zone_id) REFERENCES zones(id)
);

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value_json TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alerts (
  id TEXT PRIMARY KEY,
  category TEXT NOT NULL,
  severity TEXT NOT NULL CHECK (severity IN ('high', 'medium', 'low')),
  title TEXT NOT NULL,
  context TEXT NOT NULL,
  href TEXT NOT NULL DEFAULT '/alerts',
  status TEXT NOT NULL CHECK (status IN ('active', 'resolved')) DEFAULT 'active',
  source TEXT NOT NULL DEFAULT 'orchestrator',
  evidence_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  resolved_at TEXT,
  resolved_by TEXT,
  FOREIGN KEY(resolved_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS orchestration_events (
  id TEXT PRIMARY KEY,
  event_type TEXT NOT NULL,
  source TEXT NOT NULL,
  zone_id TEXT,
  severity TEXT NOT NULL DEFAULT 'medium',
  title TEXT NOT NULL,
  evidence_json TEXT NOT NULL DEFAULT '{}',
  source_timestamp TEXT,
  created_at TEXT NOT NULL,
  dedupe_key TEXT,  -- idempotency key of an automatic event (CV episode id or adapter idempotencyKey); NULL for manual events
  FOREIGN KEY(zone_id) REFERENCES zones(id)
);
CREATE UNIQUE INDEX IF NOT EXISTS orchestration_events_dedupe ON orchestration_events(dedupe_key);

CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY,
  employee_id TEXT NOT NULL,
  target_zone_id TEXT,
  source_zone_id TEXT,
  instruction TEXT NOT NULL,
  state TEXT NOT NULL,
  trigger_alert_id TEXT,
  evidence_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  due_at TEXT,
  FOREIGN KEY(employee_id) REFERENCES users(id),
  FOREIGN KEY(target_zone_id) REFERENCES zones(id),
  FOREIGN KEY(source_zone_id) REFERENCES zones(id),
  FOREIGN KEY(trigger_alert_id) REFERENCES alerts(id)
);

CREATE TABLE IF NOT EXISTS dispatch_decisions (
  id TEXT PRIMARY KEY,
  event_id TEXT NOT NULL,
  alert_id TEXT,
  task_id TEXT,
  selected_employee_id TEXT,
  decision TEXT NOT NULL,
  reason TEXT NOT NULL,
  policy_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  FOREIGN KEY(event_id) REFERENCES orchestration_events(id),
  FOREIGN KEY(alert_id) REFERENCES alerts(id),
  FOREIGN KEY(task_id) REFERENCES tasks(id),
  FOREIGN KEY(selected_employee_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS task_events (
  id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL,
  state TEXT NOT NULL,
  actor_id TEXT,
  note TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY(task_id) REFERENCES tasks(id),
  FOREIGN KEY(actor_id) REFERENCES users(id)
);
