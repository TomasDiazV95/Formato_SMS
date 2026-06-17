from __future__ import annotations

import re
from datetime import date, datetime

from utils.db_sqlserver import get_stc_connection


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

    query_template = """
    WITH ranked_emails AS (
        SELECT
            rut,
            email,
            ROW_NUMBER() OVER (
                PARTITION BY LTRIM(RTRIM(CAST(rut AS nvarchar(64))))
                ORDER BY fecha_carga DESC
            ) AS rn
        FROM dbo.emails_carga
        WHERE LTRIM(RTRIM(CAST(rut AS nvarchar(64)))) IN ({placeholders})
    )
    SELECT rut, email
    FROM ranked_emails
    WHERE rn = 1
    """

    result: dict[str, str] = {}
    chunk_size = 1000
    with get_stc_connection() as conn:
        cur = conn.cursor()
        for i in range(0, len(ruts), chunk_size):
            chunk = ruts[i:i + chunk_size]
            placeholders = ", ".join("?" for _ in chunk)
            query = query_template.format(placeholders=placeholders)
            cur.execute(query, chunk)
            for row in cur.fetchall():
                rut_key = rut_only_numbers(row[0])
                if rut_key:
                    result[rut_key] = str(row[1] or "").strip()
    return result
