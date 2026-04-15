"""Database helpers for the external resultantes source."""
from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path

import mysql.connector


def _load_env_file() -> None:
    env_path = Path(".env")
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_env_file()


RESULT_DB_CONFIG = {
    "host": os.getenv("RESULT_DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("RESULT_DB_PORT", "3306")),
    "user": os.getenv("RESULT_DB_USER", "root"),
    "password": os.getenv("RESULT_DB_PASSWORD", ""),
    "database": os.getenv("RESULT_DB_NAME", ""),
    "autocommit": False,
    "charset": "utf8mb4",
    "use_unicode": True,
}


@contextmanager
def get_resultantes_connection():
    conn = mysql.connector.connect(**RESULT_DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()
