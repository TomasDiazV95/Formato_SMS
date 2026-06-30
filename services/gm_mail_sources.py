from __future__ import annotations

from services.santander_consumer_sources import normalize_operation
from utils.db_sqlserver import get_stc_connection


def fetch_tmp_asig_gm_rows(operations: list[str]) -> dict[str, dict[str, object]]:
    if not operations:
        return {}

    query_template = """
    WITH ranked AS (
        SELECT
            [fld_Customer Name],
            [fld_National Id],
            [fld_Agreement Number],
            [fld_Due Date],
            [fld_EMI],
            [fld_Email],
            ROW_NUMBER() OVER (
                PARTITION BY LTRIM(RTRIM(CAST([fld_Agreement Number] AS nvarchar(255))))
                ORDER BY (SELECT 0)
            ) AS rn
        FROM dbo.tmp_asig_gm
        WHERE LTRIM(RTRIM(CAST([fld_Agreement Number] AS nvarchar(255)))) IN ({placeholders})
    )
    SELECT [fld_Customer Name], [fld_National Id], [fld_Agreement Number], [fld_Due Date], [fld_EMI], [fld_Email]
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
                    "NOMBRE": row[0],
                    "RUT": row[1],
                    "OPERACION": row[2],
                    "FECHA_VENCIMIENTO_CUOTA": row[3],
                    "MONTO_CUOTA": row[4],
                    "dest_email": row[5],
                }

    return rows_by_operation
