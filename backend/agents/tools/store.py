"""Bounded, scoped event reads. Never imports the schema-initializing writer."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3

from ..contracts import EventFilters, TrustedAccessScope

TABLE_COLUMNS = {
    "footfall": ("track_id", "direction"),
    "zone_dwell": ("track_id", "role", "dwell_s"),
    "interactions": ("employee_track_id", "customer_track_id", "duration_s", "verdict"),
    "tracks": ("track_id", "role"),
    "pipeline_health": ("fps", "frozen_or_dark"),
    "unattended_episodes": ("customer_track_id", "waited_s", "helped"),
}
COMMON = ("event_id", "run_id", "store_id", "camera_id", "zone_id", "ts_start", "ts_end")
SCAN_LIMIT = 100_000


class SourceUnavailable(Exception):
    """A bounded read could not provide a trustworthy source."""


def utc(value):
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise SourceUnavailable("Source timestamps must include a timezone")
    return stamp.astimezone(timezone.utc)


class ReadSession:
    def __init__(self, conn):
        self.conn = conn

    def rows(self, table, scope, filters, window=None, *, camera_wide=False):
        if table not in TABLE_COLUMNS:
            raise ValueError("Unsupported fixed event source")
        try:
            available = {r[1] for r in self.conn.execute(f"PRAGMA table_info({table})")}
            columns = COMMON + TABLE_COLUMNS[table]
            if not set(columns) <= available:
                raise SourceUnavailable(f"Missing {table} table or required columns")
            scope.validate_filters(filters)
            clauses, params = ["store_id = ?"], [scope.store_id]
            for column, permitted in (("run_id", scope.allowed_run_ids), ("camera_id", scope.allowed_camera_ids),
                                      ("zone_id", None if camera_wide else scope.allowed_zone_ids)):
                selected = getattr(filters, column)
                if column == "zone_id" and camera_wide:
                    selected = None
                if selected is not None:
                    clauses.append(f"{column} = ?")
                    params.append(selected)
                if permitted is not None:
                    clauses.append(f"{column} IN ({','.join('?' for _ in permitted)})")
                    params.extend(permitted)
            if window:
                # Broad SQL prefilter (julianday has millisecond resolution), then
                # exact UTC/microsecond selection below. Never compare ISO text lexically.
                clauses += ["julianday(ts_start) <= julianday(?)", "julianday(ts_end) >= julianday(?)"]
                params += [(window.end + timedelta(seconds=1)).isoformat(),
                           (window.start - timedelta(seconds=1)).isoformat()]
            query = f"SELECT {','.join(columns)} FROM {table} WHERE {' AND '.join(clauses)} LIMIT ?"
            data = [dict(row) for row in self.conn.execute(query, params + [SCAN_LIMIT + 1])]
            if len(data) > SCAN_LIMIT:
                raise SourceUnavailable(f"{table} exceeds the 100000-row scan budget; narrow the scope/window")
            for row in data:
                row['_start'], row['_end'] = utc(row['ts_start']), utc(row['ts_end'])
                if row['_end'] < row['_start']:
                    raise SourceUnavailable(f"Invalid {table} event interval")
            if window:
                data = [row for row in data if (
                    window.start <= row['_start'] < window.end if row['_start'] == row['_end']
                    else row['_start'] < window.end and row['_end'] > window.start)]
            return sorted(data, key=lambda row: (row['_start'], row['event_id']))
        except sqlite3.Error as exc:
            raise SourceUnavailable(f"Cannot read {table} from the event database") from exc
        except (ValueError, TypeError, OverflowError) as exc:
            raise SourceUnavailable(f"Invalid {table} source data") from exc


@contextmanager
def read_session(path):
    conn = None
    try:
        uri = Path(path).resolve().as_uri() + "?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=3)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only = ON")
        conn.execute("BEGIN")  # All dependent reads share one snapshot.
        yield ReadSession(conn)
    except sqlite3.Error as exc:
        raise SourceUnavailable("Event database unavailable for a read-only snapshot") from exc
    finally:
        if conn is not None:
            conn.close()
