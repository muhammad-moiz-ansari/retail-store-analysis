"""Import legacy RetailPulse files into an empty PostgreSQL database."""

import argparse
from contextlib import closing
from datetime import datetime
from pathlib import Path
import sqlite3

from psycopg import sql

from .database import connect, initialize
from .events.ingest import TABLES as EVENT_TABLES


APPLICATION_TABLES = (
    "users", "invitations", "zones", "cameras", "rosters", "settings", "alerts",
    "orchestration_events", "tasks", "dispatch_decisions", "task_events",
)


def import_files(conn, *, application=None, events=None, identities=None):
    sources = (
        (application, APPLICATION_TABLES),
        (events, EVENT_TABLES),
        (identities, ("documents",)),
    )
    tables = tuple(table for path, group in sources if path is not None for table in group)
    if not tables:
        raise ValueError("Choose at least one legacy database file.")
    counts = {}
    with conn.transaction():
        initialize(conn)
        identifiers = sql.SQL(", ").join(map(sql.Identifier, tables))
        conn.execute(sql.SQL("LOCK TABLE {} IN SHARE ROW EXCLUSIVE MODE").format(identifiers))
        for table in tables:
            if conn.execute(sql.SQL("SELECT 1 FROM {} LIMIT 1").format(sql.Identifier(table))).fetchone():
                raise ValueError(f"Destination table {table} already has records.")
        for path, group in sources:
            if path is None:
                continue
            uri = Path(path).resolve(strict=True).as_uri() + "?mode=ro"
            with closing(sqlite3.connect(uri, uri=True)) as source:
                source.execute("BEGIN")
                available = {row[0] for row in source.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
                for table in group:
                    if table == "heatmaps" and table not in available:
                        counts[table] = 0
                        continue
                    if table not in available:
                        raise ValueError(f"Legacy file is missing table {table}.")
                    counts[table] = copy_table(source, conn, table)
    return counts


def copy_table(source, destination, table):
    # The identifiers come from the fixed table lists. SQLite rowid preserves identity insertion order.
    order = " ORDER BY rowid" if table == "documents" else ""
    rows = source.execute(f"SELECT * FROM {table}{order}")
    columns = [column[0] for column in rows.description]
    statement = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
        sql.Identifier(table), sql.SQL(", ").join(map(sql.Identifier, columns)),
        sql.SQL(", ").join(sql.Placeholder() for _ in columns),
    )
    timestamp_indexes = [columns.index(column) for column in ("ts_start", "ts_end") if column in columns]
    count = 0
    with destination.cursor() as cursor:
        while batch := rows.fetchmany(1000):
            converted = []
            for row in batch:
                values = list(row)
                for index in timestamp_indexes:
                    stamp = datetime.fromisoformat(values[index])
                    if stamp.utcoffset() is None:
                        raise ValueError(f"Legacy table {table} has a timestamp without a UTC offset.")
                    values[index] = stamp
                converted.append(values)
            cursor.executemany(statement, converted)
            count += len(batch)
    copied = destination.execute(sql.SQL("SELECT count(*) AS total FROM {}").format(sql.Identifier(table))).fetchone()
    if copied["total"] != count:
        raise ValueError(f"Row count mismatch for {table}.")
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("application", "events", "identities"):
        parser.add_argument(f"--{name}", type=Path)
    args = parser.parse_args()
    if not any(vars(args).values()):
        parser.error("Choose at least one legacy database file.")
    with connect() as conn:
        counts = import_files(conn, **vars(args))
    print("Imported rows by table:", counts)


if __name__ == "__main__":
    main()
