from __future__ import annotations

import re
from datetime import date, datetime

from utils.db_sqlserver import get_stc_connection


SC_TERRENO_BLOCKED_EMAILS = frozenset(
    {
        "administracion@ingtm.net",
        "aaa@gmail.com",
        "aaaa@gmail.com",
        "sdfd@gmail.com",
        "abc@gmail.com",
    }
)
SC_TERRENO_BLOCKED_EMAIL_DOMAINS = frozenset({"phoenixservice.cl"})


def is_blocked_terreno_email(value: object) -> bool:
    email = str(value or "").strip().lower()
    if not email:
        return False
    if email in SC_TERRENO_BLOCKED_EMAILS:
        return True
    _, separator, domain = email.rpartition("@")
    return bool(separator and domain in SC_TERRENO_BLOCKED_EMAIL_DOMAINS)


def normalize_operation(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text.endswith(".0"):
        text = text[:-2]
    return text.strip()


def rut_only_numbers(value: object) -> str:
    return re.sub(r"\D+", "", str(value or "")).strip()


def format_fecha_fuente(fld_fecha: object, fecha_carga: object) -> str:
    if fld_fecha not in (None, ""):
        return str(fld_fecha).strip()
    if isinstance(fecha_carga, datetime):
        return fecha_carga.strftime("%Y-%m-%d")
    if isinstance(fecha_carga, date):
        return fecha_carga.isoformat()
    return str(fecha_carga or "").strip()


def fetch_tmp_bench_rows(operations: list[str]) -> dict[str, dict[str, object]]:
    if not operations:
        return {}

    query_template = """
    WITH ranked AS (
        SELECT
            fld_OPERACION,
            fld_RUT,
            fld_NOMBRE,
            fld_COBRADOR,
            fld_MARCA,
            fld_PATENTE,
            fld_DEUDA_INI,
            fld_COMUNA,
            fld_REGION,
            fld_FECHA,
            fecha_carga,
            ROW_NUMBER() OVER (
                PARTITION BY LTRIM(RTRIM(CAST(fld_OPERACION AS nvarchar(255))))
                ORDER BY ts_carga DESC, id_bench_stc DESC
            ) AS rn
        FROM dbo.tmp_bench_STC
        WHERE LTRIM(RTRIM(CAST(fld_OPERACION AS nvarchar(255)))) IN ({placeholders})
    )
    SELECT fld_OPERACION, fld_RUT, fld_NOMBRE, fld_COBRADOR, fld_MARCA, fld_PATENTE, fld_DEUDA_INI, fld_COMUNA, fld_REGION, fld_FECHA, fecha_carga
    FROM ranked
    WHERE rn = 1
    """

    rows_by_operation: dict[str, dict[str, object]] = {}
    chunk_size = 500

    with get_stc_connection() as conn:
        cur = conn.cursor()
        for i in range(0, len(operations), chunk_size):
            chunk = operations[i:i + chunk_size]
            placeholders = ", ".join("?" for _ in chunk)
            query = query_template.format(placeholders=placeholders)
            cur.execute(query, chunk)
            for row in cur.fetchall():
                op_key = normalize_operation(row[0])
                if not op_key:
                    continue
                rows_by_operation[op_key] = {
                    "fld_OPERACION": row[0],
                    "fld_RUT": row[1],
                    "fld_NOMBRE": row[2],
                    "fld_COBRADOR": row[3],
                    "fld_MARCA": row[4],
                    "fld_PATENTE": row[5],
                    "fld_DEUDA_INI": row[6],
                    "fld_COMUNA": row[7],
                    "fld_REGION": row[8],
                    "fld_FECHA": row[9],
                    "fecha_carga": row[10],
                }

    return rows_by_operation


def fetch_emails_by_rut(ruts: list[str]) -> dict[str, str]:
    if not ruts:
        return {}

    today = date.today()
    month_start = date(today.year, today.month, 1)
    if today.month == 12:
        next_month_start = date(today.year + 1, 1, 1)
    else:
        next_month_start = date(today.year, today.month + 1, 1)

    query_template = """
    SELECT rut, email, ranking, fecha_carga
    FROM dbo.emails_carga
    WHERE cartera = ?
      AND ranking IN (1, 2, 3)
      AND fecha_carga >= ?
      AND fecha_carga < ?
      AND LTRIM(RTRIM(CAST(rut AS nvarchar(64)))) IN ({placeholders})
    ORDER BY
        LTRIM(RTRIM(CAST(rut AS nvarchar(64)))),
        ranking ASC,
        fecha_carga DESC
    """

    result: dict[str, str] = {}
    chunk_size = 1000
    with get_stc_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT COUNT(*)
            FROM dbo.emails_carga
            WHERE cartera = ?
              AND fecha_carga >= ?
              AND fecha_carga < ?
            """,
            ("525", month_start, next_month_start),
        )
        current_month_rows = int(cur.fetchone()[0] or 0)
        if current_month_rows == 0:
            raise ValueError("Los mails de Santander Consumer Terreno para el mes actual no están cargados.")

        for i in range(0, len(ruts), chunk_size):
            chunk = ruts[i:i + chunk_size]
            placeholders = ", ".join("?" for _ in chunk)
            query = query_template.format(placeholders=placeholders)
            cur.execute(query, ("525", month_start, next_month_start, *chunk))
            for row in cur.fetchall():
                rut_key = rut_only_numbers(row[0])
                if not rut_key or rut_key in result:
                    continue
                email = str(row[1] or "").strip()
                if is_blocked_terreno_email(email):
                    continue
                result[rut_key] = email
    return result
