from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Any

import pandas as pd

from config import EMAIL_RE
from services.contact_dedupe import dedupe_by_column_keep_first, dedupe_by_column_keep_first_normalized
from services.gm_mail_templates import get_default_gm_mail_template, get_gm_mail_template
from services import gm_mail_sources
from services.mail_service import build_mail_crm_output
from services.santander_consumer_sources import normalize_operation

OPERATION_COLUMN_KEYS = {"OPERACION", "OP"}


def normalize_header(value: object) -> str:
    text = str(value or "").strip().upper()
    text = "".join(
        char for char in unicodedata.normalize("NFD", text)
        if unicodedata.category(char) != "Mn"
    )
    return re.sub(r"\s+", " ", text)


def find_operation_column(columns: list[object]) -> object:
    for column in columns:
        if normalize_header(column) in OPERATION_COLUMN_KEYS:
            return column
    raise ValueError("El archivo debe contener una columna OPERACION u OP.")


def _format_date(value: object) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, datetime):
        return value.strftime("%d-%m-%Y")
    if isinstance(value, date):
        return value.strftime("%d-%m-%Y")
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return str(value).strip()
    return parsed.strftime("%d-%m-%Y")


def _template_columns(template: dict[str, Any]) -> list[str]:
    columns = template.get("columns")
    if not isinstance(columns, list) or not columns:
        raise ValueError("La plantilla GM Mail no tiene columnas configuradas.")
    return [str(column) for column in columns]


def _template_fixed_values(template: dict[str, Any]) -> dict[str, Any]:
    fixed_values = template.get("fixed_values")
    if not isinstance(fixed_values, dict):
        return {}
    return fixed_values


def _template_seed_rows(template: dict[str, Any]) -> list[dict[str, Any]]:
    seed_rows = template.get("seed_rows")
    if not isinstance(seed_rows, list):
        return []
    return [item for item in seed_rows if isinstance(item, dict)]


def build_gm_mail_output(
    df_origin: pd.DataFrame,
    *,
    template_key: str = "gm_comercial_84995",
    today: date | None = None,
    delivery_date: date | None = None,
) -> pd.DataFrame:
    template = get_gm_mail_template(template_key) or get_default_gm_mail_template()
    columns = _template_columns(template)
    fixed_values = _template_fixed_values(template)
    seed_rows = _template_seed_rows(template)
    today = today or date.today()
    delivery_date_text = delivery_date.strftime("%d-%m-%Y") if delivery_date else ""

    operation_column = find_operation_column(list(df_origin.columns))
    operations = [normalize_operation(value) for value in df_origin[operation_column].tolist()]
    source_operations = [operation for operation in operations if operation]
    unique_operations = list(dict.fromkeys(source_operations))
    rows_by_operation = gm_mail_sources.fetch_tmp_asig_gm_rows(unique_operations)

    output_rows: list[dict[str, Any]] = []
    for seed in seed_rows:
        row = {column: "" for column in columns}
        row.update(fixed_values)
        row.update({key: value for key, value in seed.items() if key in row})
        row["FECHA_ARCHIVO"] = today.strftime("%d-%m-%Y")
        if "FECHA_ENTREGA" in row:
            row["FECHA_ENTREGA"] = delivery_date_text
        output_rows.append(row)

    for operation in operations:
        if not operation:
            continue
        source_row = rows_by_operation.get(operation, {})
        row = {column: "" for column in columns}
        row.update(fixed_values)
        row["OPERACION"] = normalize_operation(source_row.get("OPERACION")) or operation
        row["NOMBRE"] = str(source_row.get("NOMBRE") or "").strip()
        row["RUT"] = str(source_row.get("RUT") or "").strip()
        row["FECHA_VENCIMIENTO_CUOTA"] = _format_date(source_row.get("FECHA_VENCIMIENTO_CUOTA"))
        row["MONTO_CUOTA"] = source_row.get("MONTO_CUOTA") or ""
        row["FECHA_ARCHIVO"] = today.strftime("%d-%m-%Y")
        if "FECHA_ENTREGA" in row:
            row["FECHA_ENTREGA"] = delivery_date_text
        row["dest_email"] = str(source_row.get("dest_email") or "").strip()
        output_rows.append(row)

    output = pd.DataFrame(output_rows, columns=columns)
    if output.empty:
        return output

    valid_email = output["dest_email"].astype(str).str.strip().str.match(EMAIL_RE, na=False)
    empty_email = output["dest_email"].astype(str).str.strip() == ""
    output = output[valid_email | empty_email].reset_index(drop=True)
    output = dedupe_by_column_keep_first(output, "RUT")
    output = dedupe_by_column_keep_first_normalized(output, "dest_email")
    return output[columns].reset_index(drop=True)


def build_gm_mail_from_excel(
    file_storage,
    *,
    template_key: str = "gm_comercial_84995",
    delivery_date: date | None = None,
) -> pd.DataFrame:
    df_origin = pd.read_excel(file_storage)
    return build_gm_mail_output(df_origin, template_key=template_key, delivery_date=delivery_date)


def build_gm_mail_crm_output(
    gm_output: pd.DataFrame,
    *,
    fecha: date,
    hora_inicio: str,
    hora_fin: str,
) -> pd.DataFrame:
    required = {"RUT", "OPERACION", "dest_email"}
    missing = sorted(required - set(gm_output.columns))
    if missing:
        raise ValueError("Faltan columnas para generar CRM GM: " + ", ".join(missing))

    crm_source = gm_output.rename(columns={"dest_email": "MAIL"}).copy()
    crm_source = crm_source[
        crm_source["RUT"].astype(str).str.strip().ne("")
        & crm_source["OPERACION"].astype(str).str.strip().ne("")
        & crm_source["MAIL"].astype(str).str.strip().ne("")
    ].reset_index(drop=True)
    return build_mail_crm_output(
        crm_source,
        fecha=fecha,
        hora_inicio=hora_inicio,
        hora_fin=hora_fin,
        usuario_value="jriveros",
        observacion_value="ENVIO MAIL",
    )
