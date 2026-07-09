"""Database tool - run read-only queries against a SQL database.

Owner: Ahmad
"""
from __future__ import annotations


def query(sql: str) -> list[dict]:
    """Execute a SELECT statement and return rows as dicts."""
    # TODO: use a SQLAlchemy engine built from backend.config.settings
    raise NotImplementedError("Ahmad: implement DB querying")
