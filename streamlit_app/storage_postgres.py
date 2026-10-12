"""Private PostgreSQL connection adapter for the existing storage contract.

Only fixed, internal SQL uses qmark placeholders; user values stay separately
bound. No database URL or provider exception is exposed to the frontend.
"""
from contextlib import contextmanager
from functools import lru_cache
import os


class StorageUnavailable(RuntimeError):
    pass


class PostgresConnection:
    postgres = True

    def __init__(self, connection):
        self.connection = connection

    def execute(self, query, params=None):
        # This is deliberately not a general SQL translator. The storage module
        # supplies fixed statements without question marks in SQL literals.
        return self.connection.execute(query.replace("?", "%s"), params)

    def commit(self):
        self.connection.commit()


@lru_cache(maxsize=2)
def _pool(database_url):
    from psycopg_pool import ConnectionPool
    return ConnectionPool(
        conninfo=database_url, min_size=0, max_size=5, timeout=15,
        max_idle=60, open=True, check=ConnectionPool.check_connection,
        kwargs={
            "connect_timeout": 10,
            "prepare_threshold": None,
            "sslmode": "verify-full",
            "sslrootcert": "system",
            "options": "-c statement_timeout=15000 -c lock_timeout=10000",
        },
    )


@contextmanager
def connection():
    database_url = os.environ.get("INI_DATABASE_URL", "").strip()
    if not database_url:
        raise StorageUnavailable("Persistent storage is not configured.")
    try:
        with _pool(database_url).connection() as conn:
            yield PostgresConnection(conn)
    except StorageUnavailable:
        raise
    except Exception:
        # Do not leak hostnames, credentials, SQL values, or driver diagnostics.
        raise StorageUnavailable("Persistent storage is temporarily unavailable. Please try again shortly.") from None
