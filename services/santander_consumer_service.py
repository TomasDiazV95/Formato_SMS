from __future__ import annotations

from datetime import date, datetime
import re
import unicodedata
from difflib import SequenceMatcher

import pandas as pd

from services import ejecutivos_repo
from services.santander_consumer_templates import SantanderConsumerTemplate, get_santander_consumer_template
from utils.db_sqlserver import get_stc_connection


OUTPUT_COLUMNS = [
    "INSTITUCIÓN",
    "SEGMENTOINSTITUCIÓN",
    "message_id",
    "NRO_CUOTAS",
    "OPERACION_INPUT",
    "ENCONTRADO_DB",
    "RUT",
    "dest_email",
    "NRO_OPERACION",
    "CLIENTE",
    "name_from",
    "EJECUTIVO",
    "mail_from",
    "CORREO",
    "CELULAR",
    "MARCA",
    "PATENTE",
    "OFERTA A PAGO",
    "COMUNA",
    "REGION",
    "FECHA_FUENTE",
    "MES_CURSO",
    "ANO_CURSO",
    "DIA_OFERTA",
    "MES_OFERTA",
    "ANO_OFERTA",
]

SC_EXECUTIVE_MANDANTE = "Santander Consumer Terreno"

OPERATION_COLUMN_ALIASES = {
    "operacion",
    "operación",
    "nro_operacion",
    "nro operación",
    "num_op",
    "numero_operacion",
    "numero operación",
    "nro_documento",
    "id_credito",
    "op",
}


def _normalize_key(value: str) -> str:
    return (
        (value or "")
        .strip()
        .lower()
        .replace(" ", "")
        .replace("_", "")
        .replace("-", "")
    )


def _normalize_operation(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text.endswith(".0"):
        text = text[:-2]
    return text.strip()


def _normalize_agent_text(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def _ascii_fold(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return text.encode("ascii", "ignore").decode("ascii")


def _token_key(value: object) -> str:
    parts = [part for part in _ascii_fold(value).lower().split() if part]
    parts.sort()
    return " ".join(parts)


def _rut_only_numbers(value: object) -> str:
    return re.sub(r"\D+", "", str(value or "")).strip()


def _find_operation_column(df: pd.DataFrame) -> str | None:
    normalized = {_normalize_key(col): col for col in df.columns}
    candidates = {_normalize_key(name) for name in OPERATION_COLUMN_ALIASES}
    for candidate in candidates:
        if candidate in normalized:
            return normalized[candidate]
    return None


def _format_fecha_fuente(fld_fecha: object, fecha_carga: object) -> str:
    if fld_fecha not in (None, ""):
        return str(fld_fecha).strip()
    if isinstance(fecha_carga, datetime):
        return fecha_carga.strftime("%Y-%m-%d")
    if isinstance(fecha_carga, date):
        return fecha_carga.isoformat()
    return str(fecha_carga or "").strip()


def _fetch_tmp_bench_rows(operations: list[str]) -> dict[str, dict[str, object]]:
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
                op_key = _normalize_operation(row[0])
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


def _fetch_emails_by_rut(ruts: list[str]) -> dict[str, str]:
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
                rut_key = _rut_only_numbers(row[0])
                if rut_key:
                    result[rut_key] = str(row[1] or "").strip()
    return result


def _resolve_template(template_key: str) -> SantanderConsumerTemplate:
    template = get_santander_consumer_template(template_key)
    if not template:
        raise ValueError("Plantilla no válida para Santander Consumer.")
    return template


def build_santander_consumer_terreno_output(df: pd.DataFrame, *, template_key: str) -> pd.DataFrame:
    base = df.copy()
    template = _resolve_template(template_key)
    op_col = _find_operation_column(base)
    if not op_col:
        raise ValueError("El Excel no contiene una columna de operación (ej: OPERACION, NRO_OPERACION, NUM_OP).")

    operation_values = base[op_col].map(_normalize_operation)
    if operation_values.eq("").all():
        raise ValueError("La columna de operación está vacía.")

    ops_to_query = list(dict.fromkeys([op for op in operation_values.tolist() if op]))
    db_rows = _fetch_tmp_bench_rows(ops_to_query)
    now = datetime.now()
    mes_curso = str(now.month)
    ano_curso = str(now.year)
    ruts_to_query = list(
        dict.fromkeys(
            [
                _rut_only_numbers(item.get("fld_RUT"))
                for item in db_rows.values()
                if _rut_only_numbers(item.get("fld_RUT"))
            ]
        )
    )
    email_by_rut = _fetch_emails_by_rut(ruts_to_query)
    exec_cache: dict[str, ejecutivos_repo.Ejecutivo | None] = {}

    def _get_ejecutivo(nombre: str) -> ejecutivos_repo.Ejecutivo | None:
        raw = _normalize_agent_text(nombre)
        if not raw:
            return None

        cache_key = _ascii_fold(raw).lower()
        if cache_key not in exec_cache:
            candidates = [
                raw,
                raw.lower(),
                raw.upper(),
                _ascii_fold(raw),
                _ascii_fold(raw).lower(),
                _ascii_fold(raw).upper(),
            ]

            found = None
            seen: set[str] = set()
            for candidate in candidates:
                candidate = _normalize_agent_text(candidate)
                if not candidate or candidate in seen:
                    continue
                seen.add(candidate)
                found = ejecutivos_repo.fetch_by_mandante_and_nombre(SC_EXECUTIVE_MANDANTE, candidate)
                if found:
                    break

            if not found:
                target = _ascii_fold(raw).lower().strip()
                target_tokens = _token_key(raw)
                best_match = None
                best_score = 0.0
                for ejecutivo in ejecutivos_repo.list_ejecutivos(mandante=SC_EXECUTIVE_MANDANTE, activos=True):
                    options = [
                        _ascii_fold(ejecutivo.nombre_mostrar or "").lower().strip(),
                        (ejecutivo.nombre_clave or "").replace("_", " ").lower().strip(),
                        _token_key(ejecutivo.nombre_mostrar or ""),
                        _token_key((ejecutivo.nombre_clave or "").replace("_", " ")),
                    ]
                    for option in options:
                        if not option:
                            continue
                        score = max(
                            SequenceMatcher(None, target, option).ratio(),
                            SequenceMatcher(None, target_tokens, option).ratio(),
                        )
                        if score > best_score:
                            best_score = score
                            best_match = ejecutivo
                found = best_match if best_match and best_score >= 0.92 else None

            exec_cache[cache_key] = found
        return exec_cache[cache_key]

    out_rows: list[dict[str, str]] = []
    for op in operation_values.tolist():
        row = db_rows.get(op)
        if row:
            rut_normalized = _rut_only_numbers(row.get("fld_RUT"))
            base_name = _normalize_agent_text(row.get("fld_COBRADOR"))
            ejecutivo = _get_ejecutivo(base_name)
            correo_ejecutivo = (ejecutivo.correo or "").strip() if ejecutivo else ""
            reenviador = (ejecutivo.reenviador or "").strip() if ejecutivo else ""
            celular = (ejecutivo.telefono or "").strip() if ejecutivo else ""
            dest_email = email_by_rut.get(rut_normalized, "")
            out_rows.append(
                {
                    "INSTITUCIÓN": "Santander Consumer",
                    "SEGMENTOINSTITUCIÓN": "Santander Consumer",
                    "message_id": str(template.message_id),
                    "NRO_CUOTAS": template.nro_cuotas,
                    "OPERACION_INPUT": op,
                    "ENCONTRADO_DB": "SI",
                    "RUT": str(row.get("fld_RUT") or "").strip(),
                    "dest_email": dest_email,
                    "NRO_OPERACION": str(row.get("fld_OPERACION") or "").strip(),
                    "CLIENTE": str(row.get("fld_NOMBRE") or "").strip(),
                    "name_from": base_name,
                    "EJECUTIVO": base_name,
                    "mail_from": reenviador,
                    "CORREO": correo_ejecutivo,
                    "CELULAR": celular,
                    "MARCA": str(row.get("fld_MARCA") or "").strip(),
                    "PATENTE": str(row.get("fld_PATENTE") or "").strip(),
                    "OFERTA A PAGO": str(row.get("fld_DEUDA_INI") or row.get("fld_DAUDA_INI") or "").strip(),
                    "COMUNA": str(row.get("fld_COMUNA") or "").strip(),
                    "REGION": str(row.get("fld_REGION") or "").strip(),
                    "FECHA_FUENTE": _format_fecha_fuente(row.get("fld_FECHA"), row.get("fecha_carga")),
                    "MES_CURSO": mes_curso,
                    "ANO_CURSO": ano_curso,
                    "DIA_OFERTA": "",
                    "MES_OFERTA": "",
                    "ANO_OFERTA": "",
                }
            )
        else:
            out_rows.append(
                {
                    "INSTITUCIÓN": "Santander Consumer",
                    "SEGMENTOINSTITUCIÓN": "Santander Consumer",
                    "message_id": str(template.message_id),
                    "NRO_CUOTAS": template.nro_cuotas,
                    "OPERACION_INPUT": op,
                    "ENCONTRADO_DB": "NO",
                    "RUT": "",
                    "dest_email": "",
                    "NRO_OPERACION": "",
                    "CLIENTE": "",
                    "name_from": "",
                    "EJECUTIVO": "",
                    "mail_from": "",
                    "CORREO": "",
                    "CELULAR": "",
                    "MARCA": "",
                    "PATENTE": "",
                    "OFERTA A PAGO": "",
                    "COMUNA": "",
                    "REGION": "",
                    "FECHA_FUENTE": "",
                    "MES_CURSO": mes_curso,
                    "ANO_CURSO": ano_curso,
                    "DIA_OFERTA": "",
                    "MES_OFERTA": "",
                    "ANO_OFERTA": "",
                }
            )

    return pd.DataFrame(out_rows, columns=OUTPUT_COLUMNS)


def build_santander_consumer_terreno_from_excel(file_storage, *, template_key: str) -> pd.DataFrame:
    df = pd.read_excel(file_storage, dtype=str)
    return build_santander_consumer_terreno_output(df, template_key=template_key)
