from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

import pandas as pd

from services.mail_templates import build_mail_template
from services.mandante_rules import apply_mandante_rules
from services.sms_itau_vencida import (
    build_itau_carterizado_messages,
    prepend_itau_seed_rows,
)
from services.sms_service import (
    build_athenas_output,
    build_axia_output,
)


SMS_MASIVIDAD_TO_TEMPLATE = {
    "SMS MOROSIDAD": "MOROSIDAD",
    "SMS COMPROMISO DE PAGO": "COMPROMISO_PAGO",
    "SMS COMPROMISO ROTO": "COMPROMISO_ROTO",
    "SMS CAMPANA": "CAMPANA_NUEVO",
}

MAIL_MASIVIDAD_TO_TEMPLATE = {
    "ITAU VENCIDA COBRANZA": "ITAU_VENCIDA_MAIL",
    "EMAIL CAMPANA ITAU VIGENTE": "ITAU_VENCIDA_MAIL_100998",
}

SOURCE_MASIVIDAD_ALIASES = {
    "SMS CAMPANA NUEVA": "SMS CAMPANA",
    "SMS CAMPANA NUEVO": "SMS CAMPANA",
}

HEADER_ALIASES = {
    "RUT": {
        "rut",
        "rutcliente",
        "idcliente",
    },
    "DV": {
        "dv",
        "dv1",
        "digitoverificador",
    },
    "OPERACION": {
        "operacion",
        "operaciones",
        "op",
        "ope",
        "nrooperacion",
        "nrodocumento",
        "idcredito",
    },
    "NOMBRE": {
        "nombre",
        "nombrecliente",
        "cliente",
        "contacto",
    },
    "CARTERIZADO": {
        "carterizado",
        "carterizados",
        "agente",
        "ejecutivo",
        "nombreagente",
        "carterizadoenero",
        "carterizadofebrero",
        "carterizadomarzo",
        "carterizadoabril",
        "carterizadomayo",
        "carterizadojunio",
        "carterizadojulio",
        "carterizadoagosto",
        "carterizadoseptiembre",
        "carterizadooctubre",
        "carterizadonoviembre",
        "carterizadodiciembre",
    },
    "MASIVIDAD": {
        "masividad",
        "masividades",
        "tiposms",
        "gestion",
    },
    "EMAIL": {
        "email",
        "mail",
        "correo",
        "destemail",
        "destmail",
        "emailcliente",
        "mailcliente",
    },
    "TELEFONO": {
        "telefono",
        "fono",
        "tel",
        "telefono1",
        "telefonott",
        "fonott",
    },
}

REQUIRED_SOURCE_COLUMNS = {
    "RUT",
    "DV",
    "OPERACION",
    "NOMBRE",
    "CARTERIZADO",
    "MASIVIDAD",
    "EMAIL",
    "TELEFONO",
}


@dataclass
class ItauVencidaOutputs:
    sheet_name: str
    sms_output: pd.DataFrame | None
    sms_crm_source: pd.DataFrame
    mail_outputs: dict[str, pd.DataFrame]


def _ascii_fold(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return text.encode("ascii", "ignore").decode("ascii")


def _normalize_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", _ascii_fold(value).lower())


def _normalize_label(value: object) -> str:
    text = _ascii_fold(value).upper()
    return re.sub(r"\s+", " ", text).strip()


def _canonical_masividad(value: object) -> str:
    normalized = _normalize_label(value)
    return SOURCE_MASIVIDAD_ALIASES.get(normalized, normalized)


def _canonicalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    base = df.copy()
    base.columns = [str(column).strip() for column in base.columns]
    aliases = {
        alias: canonical
        for canonical, values in HEADER_ALIASES.items()
        for alias in values
    }
    rename_map: dict[str, str] = {}
    claimed: set[str] = set(base.columns)
    for column in base.columns:
        canonical = aliases.get(_normalize_key(column))
        if not canonical or column == canonical or canonical in claimed:
            continue
        rename_map[column] = canonical
        claimed.add(canonical)
    if rename_map:
        base = base.rename(columns=rename_map)
    return base


def _row_has_content(df: pd.DataFrame) -> pd.Series:
    values = df.fillna("").astype(str)
    return values.apply(lambda column: column.str.strip().ne(""), axis=0).any(axis=1)


def load_itau_vencida_source(file) -> tuple[pd.DataFrame, str]:
    try:
        workbook = pd.ExcelFile(file)
    except Exception as exc:
        raise ValueError(f"No se pudo leer el archivo Excel: {exc}") from exc

    candidates: list[tuple[int, int, int, str, pd.DataFrame]] = []
    all_sheet_names = list(workbook.sheet_names)
    for position, sheet_name in enumerate(all_sheet_names):
        raw = pd.read_excel(workbook, sheet_name=sheet_name, dtype=str)
        base = _canonicalize_columns(raw).dropna(how="all")
        if "MASIVIDAD" not in base.columns:
            continue
        column_score = len(REQUIRED_SOURCE_COLUMNS.intersection(base.columns))
        sheet_score = 1 if "MASIVIDAD" in _normalize_key(sheet_name) else 0
        candidates.append((column_score, sheet_score, -position, sheet_name, base))

    if not candidates:
        sheets = ", ".join(all_sheet_names) or "(sin hojas)"
        raise ValueError(
            "No se encontró una hoja con columna MASIVIDAD/MASIVIDADES. "
            f"Hojas detectadas: {sheets}."
        )

    _, _, _, sheet_name, source = max(candidates, key=lambda item: item[:3])
    missing = sorted(REQUIRED_SOURCE_COLUMNS.difference(source.columns))
    if missing:
        raise ValueError(
            f"La hoja '{sheet_name}' no contiene las columnas requeridas: {', '.join(missing)}."
        )

    source = apply_mandante_rules(source, "Itau Vencida")
    source = source.loc[_row_has_content(source)].reset_index(drop=True)
    if source.empty:
        raise ValueError(f"La hoja '{sheet_name}' no contiene filas de origen.")

    masividad = source["MASIVIDAD"].fillna("").map(_canonical_masividad)
    known = set(SMS_MASIVIDAD_TO_TEMPLATE) | set(MAIL_MASIVIDAD_TO_TEMPLATE)
    unknown_mask = ~masividad.isin(known)
    if unknown_mask.any():
        unknown = []
        for value in masividad.loc[unknown_mask].tolist():
            label = value or "(vacío)"
            if label not in unknown:
                unknown.append(label)
        raise ValueError(
            "Se encontraron valores de MASIVIDAD no soportados para ITAU VENCIDA: "
            + ", ".join(unknown[:10])
        )

    return source, sheet_name


def build_itau_vencida_outputs(file, tipo_salida: str) -> ItauVencidaOutputs:
    tipo_salida = (tipo_salida or "").strip().upper()
    if tipo_salida not in {"AXIA", "ATHENAS"}:
        raise ValueError("El formato SMS debe ser AXIA o ATHENAS.")

    source, sheet_name = load_itau_vencida_source(file)
    masividad = source["MASIVIDAD"].fillna("").map(_canonical_masividad)

    sms_mask = masividad.isin(SMS_MASIVIDAD_TO_TEMPLATE)
    sms_source = source.loc[sms_mask].copy()
    sms_output = None
    sms_crm_source = source.iloc[0:0].copy()

    if not sms_source.empty:
        sms_source["MASIVIDAD"] = masividad.loc[sms_mask].values
        messages = build_itau_carterizado_messages(sms_source, "Itau Vencida")
        valid_mask = messages.fillna("").astype(str).str.strip().ne("")
        if not valid_mask.any():
            raise ValueError("No hay filas SMS validas para generar salida ITAU VENCIDA.")
        sms_crm_source = sms_source.loc[valid_mask].copy()
        valid_messages = messages.loc[valid_mask].copy()

        if tipo_salida == "AXIA":
            sms_output = build_axia_output(
                sms_crm_source,
                mensaje="SMS ITAU VENCIDA",
                mensajes_series=valid_messages,
            )
        else:
            sms_output = build_athenas_output(
                sms_crm_source,
                mensaje="SMS ITAU VENCIDA",
                mensajes_series=valid_messages,
            )
        sms_output, _ = prepend_itau_seed_rows(sms_output, tipo_salida, valid_messages)

    mail_outputs: dict[str, pd.DataFrame] = {}
    for mail_masividad, template_code in MAIL_MASIVIDAD_TO_TEMPLATE.items():
        mail_mask = masividad.eq(mail_masividad)
        mail_source = source.loc[mail_mask].copy()
        if mail_source.empty:
            continue
        mail_source["MASIVIDAD"] = "EMAIL"
        mail_outputs[template_code] = build_mail_template(
            mail_source,
            template_code,
            mandante="Itau Vencida",
        )

    if sms_output is None and not mail_outputs:
        raise ValueError("La base no contiene masividades procesables para ITAU VENCIDA.")

    return ItauVencidaOutputs(
        sheet_name=sheet_name,
        sms_output=sms_output,
        sms_crm_source=sms_crm_source,
        mail_outputs=mail_outputs,
    )
