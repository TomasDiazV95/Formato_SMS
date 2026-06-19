from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import Any

import pandas as pd

from config import EMAIL_RE
from services import sc_telefonia_mail_sources
from services.contact_dedupe import dedupe_by_column_keep_first, dedupe_by_column_keep_first_normalized
from services.sc_telefonia_mail_templates import get_default_sc_telefonia_mail_template, get_sc_telefonia_mail_template
from services.santander_consumer_sources import normalize_operation

OPERATION_COLUMN_KEYS = {"OPERACION", "OP", "NRO OPERACION", "N OPERACION"}
MONTHS_ES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}


def normalize_header(value: object) -> str:
    text = str(value or "").strip().upper()
    text = "".join(
        char for char in unicodedata.normalize("NFD", text)
        if unicodedata.category(char) != "Mn"
    )
    text = re.sub(r"[_\-]+", " ", text)
    return re.sub(r"\s+", " ", text)


def find_operation_column(columns: list[object]) -> object:
    for column in columns:
        if normalize_header(column) in OPERATION_COLUMN_KEYS:
            return column
    raise ValueError("El archivo debe contener una columna OPERACION, OP, NRO_OPERACION o N_OPERACION.")


def _template_columns(template: dict[str, Any]) -> list[str]:
    columns = template.get("columns")
    if not isinstance(columns, list) or not columns:
        raise ValueError("La plantilla Santander Consumer Telefonia no tiene columnas configuradas.")
    return [str(column) for column in columns]


def _template_dict(template: dict[str, Any], key: str) -> dict[str, Any]:
    value = template.get(key)
    return value if isinstance(value, dict) else {}


def _template_list(template: dict[str, Any], key: str) -> list[Any]:
    value = template.get(key)
    return value if isinstance(value, list) else []


def _date_parts(value: date | None) -> dict[str, str]:
    if not value:
        return {"DIA": "", "MES": "", "ANO": ""}
    return {"DIA": str(value.day), "MES": MONTHS_ES[value.month], "ANO": str(value.year)}


def _get_executive_value(ejecutivo, field: str) -> str:
    if not ejecutivo:
        return ""
    return str(getattr(ejecutivo, field, None) or "").strip()


def build_sc_telefonia_mail_output(
    df_origin: pd.DataFrame,
    *,
    template_key: str,
    selected_date: date | None = None,
    executive_key: str = "",
) -> pd.DataFrame:
    template = get_sc_telefonia_mail_template(template_key) or get_default_sc_telefonia_mail_template()
    columns = _template_columns(template)
    fixed_values = _template_dict(template, "fixed_values")
    source_map = _template_dict(template, "source_map")
    executive_fields = _template_dict(template, "executive_fields")
    seed_rows = [item for item in _template_list(template, "seed_rows") if isinstance(item, dict)]
    dedupe_columns = [str(item) for item in _template_list(template, "dedupe_columns")]
    date_values = _date_parts(selected_date)

    ejecutivo = None
    if template.get("requires_executive"):
        if not executive_key:
            raise ValueError("Debes seleccionar una ejecutiva.")
        ejecutivo = sc_telefonia_mail_sources.fetch_executive_by_key(executive_key)
        if not ejecutivo:
            raise ValueError("La ejecutiva seleccionada no existe o no esta activa.")
        allowed_names = {str(name or "").strip() for name in _template_list(template, "allowed_executives")}
        if allowed_names and (ejecutivo.nombre_mostrar or "").strip() not in allowed_names:
            raise ValueError("La ejecutiva seleccionada no esta permitida para esta plantilla.")

    operation_column = find_operation_column(list(df_origin.columns))
    operations = [normalize_operation(value) for value in df_origin[operation_column].tolist()]
    source_operations = [operation for operation in operations if operation]
    unique_operations = list(dict.fromkeys(source_operations))
    rows_by_operation = sc_telefonia_mail_sources.fetch_tmp_bench_temp_stc_rows(unique_operations)

    output_rows: list[dict[str, Any]] = []
    for seed in seed_rows:
        row = {column: "" for column in columns}
        row.update(fixed_values)
        row.update({key: value for key, value in date_values.items() if key in row})
        row.update({key: value for key, value in seed.items() if key in row})
        for target, executive_field in executive_fields.items():
            if target in row:
                row[target] = _get_executive_value(ejecutivo, str(executive_field))
        output_rows.append(row)

    for operation in operations:
        if not operation:
            continue
        source_row = rows_by_operation.get(operation, {})
        row = {column: "" for column in columns}
        row.update(fixed_values)
        row.update({key: value for key, value in date_values.items() if key in row})
        for target, source_key in source_map.items():
            if target not in row:
                continue
            if source_key == "OPERACION":
                row[target] = normalize_operation(source_row.get(source_key)) or operation
            else:
                row[target] = str(source_row.get(source_key) or "").strip()
        for target, executive_field in executive_fields.items():
            if target in row:
                row[target] = _get_executive_value(ejecutivo, str(executive_field))
        output_rows.append(row)

    output = pd.DataFrame(output_rows, columns=columns)
    if output.empty:
        return output

    valid_email = output["dest_email"].astype(str).str.strip().str.match(EMAIL_RE, na=False)
    empty_email = output["dest_email"].astype(str).str.strip() == ""
    output = output[valid_email | empty_email].reset_index(drop=True)
    for column in dedupe_columns:
        if column == "dest_email":
            output = dedupe_by_column_keep_first_normalized(output, column).reset_index(drop=True)
        else:
            output = dedupe_by_column_keep_first(output, column).reset_index(drop=True)
    return output[columns].reset_index(drop=True)


def build_sc_telefonia_mail_from_excel(
    file_storage,
    *,
    template_key: str,
    selected_date: date | None = None,
    executive_key: str = "",
) -> pd.DataFrame:
    df_origin = pd.read_excel(file_storage)
    return build_sc_telefonia_mail_output(
        df_origin,
        template_key=template_key,
        selected_date=selected_date,
        executive_key=executive_key,
    )
