"""Database connection. Skeleton placeholder, owner: TL (Yueyang Du)."""
from __future__ import annotations

import psycopg
from psycopg.rows import dict_row

from cee.config import settings


def connect() -> psycopg.Connection:
    return psycopg.connect(settings().database_url, row_factory=dict_row)
