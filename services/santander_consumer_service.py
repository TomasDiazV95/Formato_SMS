from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from services.contact_dedupe import dedupe_by_column_keep_first, dedupe_by_column_keep_first_normalized
from services.santander_consumer_templates import SantanderConsumerTemplate, get_santander_consumer_template
from services import santander_consumer_assignments as sc_assignments
from services import santander_consumer_sources as sc_sources


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

MEDIOS_PAGO_COLUMNS = [
    "INSTITUCIÓN",
    "SEGMENTOINSTITUCIÓN",
    "message_id",
    "PLANTILLA",
    "RUT",
    "NRO_OPERACION",
    "dest_email",
    "name_from",
    "mail_from",
    "CORREO",
]

MEDIOS_PAGO_FIXED = {
    "INSTITUCIÓN": "Santander Consumer",
    "SEGMENTOINSTITUCIÓN": "Santander Consumer",
    "message_id": "85636",
    "PLANTILLA": "TEMPRANA",
    "name_from": "Atencion Cliente Consumer",
    "mail_from": "atencionclientes@estandar.phoenixserviceinfo.cl",
    "CORREO": "mgalvez@phoenixservice.cl",
}

MEDIOS_PAGO_SEED = {
    "RUT": "4444444",
    "NRO_OPERACION": "12345",
    "dest_email": "pipe5550@gmail.com",
}

SPANISH_MONTHS = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]

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


def _find_operation_column(df: pd.DataFrame) -> str | None:
    normalized = {_normalize_key(col): col for col in df.columns}
    candidates = {_normalize_key(name) for name in OPERATION_COLUMN_ALIASES}
    for candidate in candidates:
        if candidate in normalized:
            return normalized[candidate]
    return None


def _resolve_template(template_key: str) -> SantanderConsumerTemplate:
    template = get_santander_consumer_template(template_key)
    if not template:
        raise ValueError("Plantilla no válida para Santander Consumer.")
    return template


def build_santander_consumer_terreno_output(
    df: pd.DataFrame,
    *,
    template_key: str,
    asignacion_mode: str = "normal",
    offer_deadline: date | None = None,
) -> pd.DataFrame:
    base = df.copy()
    template = _resolve_template(template_key)
    if template.key == "medios_pago":
        return _build_medios_pago_output(base, template)

    op_col = _find_operation_column(base)
    if not op_col:
        raise ValueError("El Excel no contiene una columna de operación (ej: OPERACION, NRO_OPERACION, NUM_OP).")

    operation_values = base[op_col].map(sc_sources.normalize_operation)
    if operation_values.eq("").all():
        raise ValueError("La columna de operación está vacía.")

    ops_to_query = list(dict.fromkeys([op for op in operation_values.tolist() if op]))
    db_rows = sc_sources.fetch_tmp_bench_rows(ops_to_query)
    now = datetime.now()
    mes_curso = SPANISH_MONTHS[now.month - 1]
    ano_curso = str(now.year)
    dia_oferta = offer_deadline.strftime("%d") if offer_deadline else ""
    mes_oferta = SPANISH_MONTHS[offer_deadline.month - 1] if offer_deadline else ""
    ano_oferta = str(offer_deadline.year) if offer_deadline else ""
    ruts_to_query = list(
        dict.fromkeys(
            [
                sc_sources.rut_only_numbers(item.get("fld_RUT"))
                for item in db_rows.values()
                if sc_sources.rut_only_numbers(item.get("fld_RUT"))
            ]
        )
    )
    email_by_rut = sc_sources.fetch_emails_by_rut(ruts_to_query)
    exec_cache = {}

    out_rows: list[dict[str, str]] = []
    for op in operation_values.tolist():
        row = db_rows.get(op)
        if row:
            rut_normalized = sc_sources.rut_only_numbers(row.get("fld_RUT"))
            base_name = sc_assignments.normalize_agent_text(row.get("fld_COBRADOR"))
            ejecutivo = sc_assignments.resolve_ejecutivo(base_name, exec_cache)
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
                    "FECHA_FUENTE": sc_sources.format_fecha_fuente(row.get("fld_FECHA"), row.get("fecha_carga")),
                    "MES_CURSO": mes_curso,
                    "ANO_CURSO": ano_curso,
                    "DIA_OFERTA": dia_oferta,
                    "MES_OFERTA": mes_oferta,
                    "ANO_OFERTA": ano_oferta,
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
                    "DIA_OFERTA": dia_oferta,
                    "MES_OFERTA": mes_oferta,
                    "ANO_OFERTA": ano_oferta,
                }
            )

    result = pd.DataFrame(out_rows, columns=OUTPUT_COLUMNS)
    return sc_assignments.apply_supervisor_override(result, asignacion_mode)


def _build_medios_pago_output(base: pd.DataFrame, template: SantanderConsumerTemplate) -> pd.DataFrame:
    op_col = _find_operation_column(base)
    if not op_col:
        raise ValueError("El Excel no contiene una columna de operación (ej: OPERACION, NRO_OPERACION, NUM_OP).")

    operation_values = base[op_col].map(sc_sources.normalize_operation)
    if operation_values.eq("").all():
        raise ValueError("La columna de operación está vacía.")

    ops_to_query = list(dict.fromkeys([op for op in operation_values.tolist() if op]))
    db_rows = sc_sources.fetch_tmp_bench_rows(ops_to_query)
    ruts_to_query = list(
        dict.fromkeys(
            [
                sc_sources.rut_only_numbers(item.get("fld_RUT"))
                for item in db_rows.values()
                if sc_sources.rut_only_numbers(item.get("fld_RUT"))
            ]
        )
    )
    email_by_rut = sc_sources.fetch_emails_by_rut(ruts_to_query)

    out_rows: list[dict[str, str]] = []
    for op in operation_values.tolist():
        if not op:
            continue
        row = db_rows.get(op)
        output_row = {column: "" for column in MEDIOS_PAGO_COLUMNS}
        output_row.update(MEDIOS_PAGO_FIXED)
        output_row["message_id"] = str(template.message_id)
        if row:
            rut_normalized = sc_sources.rut_only_numbers(row.get("fld_RUT"))
            output_row["RUT"] = str(row.get("fld_RUT") or "").strip()
            output_row["NRO_OPERACION"] = str(row.get("fld_OPERACION") or "").strip() or op
            output_row["dest_email"] = email_by_rut.get(rut_normalized, "")
        else:
            output_row["NRO_OPERACION"] = op
        out_rows.append(output_row)

    output = pd.DataFrame(out_rows, columns=MEDIOS_PAGO_COLUMNS)
    if not output.empty:
        output = dedupe_by_column_keep_first(output, "RUT").reset_index(drop=True)
        output = dedupe_by_column_keep_first_normalized(output, "dest_email").reset_index(drop=True)

    seed = {column: "" for column in MEDIOS_PAGO_COLUMNS}
    seed.update(MEDIOS_PAGO_FIXED)
    seed["message_id"] = str(template.message_id)
    seed.update(MEDIOS_PAGO_SEED)
    seed_df = pd.DataFrame([seed], columns=MEDIOS_PAGO_COLUMNS)
    return pd.concat([seed_df, output], ignore_index=True).reindex(columns=MEDIOS_PAGO_COLUMNS)


def build_santander_consumer_terreno_from_excel(
    file_storage,
    *,
    template_key: str,
    asignacion_mode: str = "normal",
    offer_deadline: date | None = None,
) -> pd.DataFrame:
    df = pd.read_excel(file_storage, dtype=str)
    return build_santander_consumer_terreno_output(
        df,
        template_key=template_key,
        asignacion_mode=asignacion_mode,
        offer_deadline=offer_deadline,
    )
