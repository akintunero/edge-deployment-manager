#!/usr/bin/env python3
"""Control plane database schema migrations."""

from __future__ import annotations

from importlib import resources
from typing import Any


def apply_migrations(connection: Any) -> None:
    """Apply bundled SQL migrations in order."""
    sql = resources.files(__package__).joinpath("001_devices.sql").read_text(encoding="utf-8")
    with connection.cursor() as cursor:
        for statement in sql.split(";"):
            chunk = statement.strip()
            if chunk:
                cursor.execute(chunk)
    connection.commit()
