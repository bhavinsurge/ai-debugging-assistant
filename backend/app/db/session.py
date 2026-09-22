from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator
from urllib.parse import urlparse

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.core.config import get_settings

_pool: ConnectionPool | None = None


def assert_safe_database(url: str) -> None:
    """Refuse anything that is not a rootcause_* database name."""
    name = urlparse(url).path.lstrip("/")
    if not name.startswith("rootcause"):
        raise RuntimeError(f"Refusing non-rootcause database: {name!r}")


def get_pool(database_url: str | None = None) -> ConnectionPool:
    global _pool
    settings = get_settings()
    url = database_url or settings.database_url
    assert_safe_database(url)
    if _pool is None or (database_url and database_url != settings.database_url):
        if database_url and database_url != settings.database_url:
            return ConnectionPool(conninfo=url, kwargs={"row_factory": dict_row}, min_size=1, max_size=8, open=True)
        _pool = ConnectionPool(conninfo=url, kwargs={"row_factory": dict_row}, min_size=1, max_size=10, open=True)
    return _pool


@contextmanager
def get_conn(database_url: str | None = None) -> Iterator[Connection]:
    pool = get_pool(database_url)
    with pool.connection() as conn:
        yield conn


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
