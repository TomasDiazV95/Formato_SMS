"""Database helpers for Santander Consumer SQL Server source."""
from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path

import pyodbc


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


def _driver_value() -> str:
    driver = (os.getenv("STC_DB_DRIVER") or "ODBC Driver 17 for SQL Server").strip()
    if driver.startswith("{") and driver.endswith("}"):
        return driver
    return f"{{{driver}}}"


def _connection_string() -> str:
    server = (os.getenv("STC_DB_SERVER") or "").strip()
    database = (os.getenv("STC_DB_NAME") or "").strip()
    user = (os.getenv("STC_DB_USER") or "").strip()
    password = os.getenv("STC_DB_PASSWORD") or ""

    if not server or not database or not user:
        raise RuntimeError("Faltan variables STC_DB_SERVER, STC_DB_NAME o STC_DB_USER para conectar a SQL Server.")

    encrypt = (os.getenv("STC_DB_ENCRYPT") or "no").strip().lower()
    trust_cert = (os.getenv("STC_DB_TRUST_SERVER_CERT") or "yes").strip().lower()

    return (
        f"DRIVER={_driver_value()};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        f"Encrypt={encrypt};"
        f"TrustServerCertificate={trust_cert};"
    )


@contextmanager
def get_stc_connection():
    timeout = int(os.getenv("STC_DB_TIMEOUT", "30"))
    conn = pyodbc.connect(_connection_string(), timeout=timeout, autocommit=False)
    try:
        yield conn
    finally:
        conn.close()
