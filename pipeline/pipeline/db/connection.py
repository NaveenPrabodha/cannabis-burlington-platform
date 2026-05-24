"""
Shared psycopg2 connection helpers for the pipeline.
Sync driver is fine here — scrapers are I/O-bound on the HTTP side,
not the DB. Keeps things simple compared to async.
"""

from __future__ import annotations

from contextlib import contextmanager
from urllib.parse import urlparse

import psycopg2
from psycopg2.extensions import connection as Connection

from pipeline.config import get_settings


def _dsn_kwargs() -> dict:
    """Convert the SQLAlchemy-style URL into psycopg2 connect kwargs."""
    url = urlparse(get_settings().database_url.replace("postgresql+psycopg2", "postgresql"))
    return {
        "host": url.hostname,
        "port": url.port or 5432,
        "dbname": url.path.lstrip("/"),
        "user": url.username,
        "password": url.password,
    }


@contextmanager
def get_connection() -> Connection:
    conn = psycopg2.connect(**_dsn_kwargs())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
