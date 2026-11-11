"""Use an isolated PostgreSQL schema per database-dependent test."""

import os
from uuid import uuid4

import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo

from .database import connect, initialize


@pytest.fixture
def postgres_dsn():
    test_url = os.getenv("TEST_DATABASE_URL")
    if not test_url:
        pytest.skip("Set TEST_DATABASE_URL to a disposable PostgreSQL database")
    schema = sql.Identifier("retailpulse_test_" + uuid4().hex)
    with connect(test_url) as conn:
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(schema))
    dsn = make_conninfo(test_url, options=f"-csearch_path={schema.as_string()}")
    try:
        with connect(dsn) as conn:
            initialize(conn)
        yield dsn
    finally:
        with connect(test_url) as conn:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(schema))


@pytest.fixture
def postgres_connection(postgres_dsn):
    with connect(postgres_dsn) as conn:
        yield conn
