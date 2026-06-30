from __future__ import annotations

from repositories import ejecutivos_repo
from services.santander_consumer_sources import normalize_operation
from utils.db_sqlserver import get_stc_connection

MANDANTE = "Santander Consumer Telefonia"


def fetch_tmp_bench_temp_stc_rows(operations: list[str]) -> dict[str, dict[str, object]]:
    if not operations:
        return {}

    query_template = """
    WITH ranked AS (
        SELECT
            fld_RUT,
            fld_NOMBRE,
            fld_OPERACION,
            fld_EMAIL_DRIVE,
            ROW_NUMBER() OVER (
                PARTITION BY LTRIM(RTRIM(CAST(fld_OPERACION AS nvarchar(255))))
                ORDER BY ts_carga DESC, id_bench_temp_stc DESC
            ) AS rn
        FROM dbo.tmp_bench_temp_STC
        WHERE LTRIM(RTRIM(CAST(fld_OPERACION AS nvarchar(255)))) IN ({placeholders})
    )
    SELECT fld_RUT, fld_NOMBRE, fld_OPERACION, fld_EMAIL_DRIVE
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
                op_key = normalize_operation(row[2])
                if not op_key:
                    continue
                rows_by_operation[op_key] = {
                    "RUT": row[0],
                    "NOMBRE": row[1],
                    "OPERACION": row[2],
                    "EMAIL": row[3],
                }

    return rows_by_operation


def list_allowed_executives(allowed_names: list[str]) -> list[dict[str, str]]:
    allowed = {str(name or "").strip() for name in allowed_names if str(name or "").strip()}
    if not allowed:
        return []

    result = []
    for ejecutivo in ejecutivos_repo.list_ejecutivos(mandante=MANDANTE, activos=True):
        nombre = (ejecutivo.nombre_mostrar or "").strip()
        if nombre not in allowed:
            continue
        result.append(
            {
                "key": ejecutivo.nombre_clave,
                "label": nombre,
                "nombre_mostrar": nombre,
                "correo": ejecutivo.correo or "",
                "telefono": ejecutivo.telefono or "",
                "reenviador": ejecutivo.reenviador or "",
            }
        )
    return sorted(result, key=lambda item: item["label"])


def fetch_executive_by_key(nombre_clave: str):
    return ejecutivos_repo.fetch_by_mandante_and_nombre(MANDANTE, nombre_clave)
