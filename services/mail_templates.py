
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, cast

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
REENVIADORES_PATH = BASE_DIR / "PLANTILLAS MAIL" / "TANNER" / "REENVIADORES AGENTES.xlsx"

TEMPLATE_COLUMNS_TANNER = [
    "INSTITUCIÓN",
    "SEGMENTOINSTITUCIÓN",
    "message_id",
    "RUT+DV",
    "NRO_OPERACION",
    "dest_email",
    "name_from",
    "mail_from",
    "NOMBRE_AGENTE",
    "MAIL_AGENTE",
    "PHONO_AGENTE",
    "MES",
    "ANO",
]

SPANISH_MONTHS = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]


@dataclass
class MailTemplate:
    code: str
    label: str
    message_id: int
    institucion: str
    segmentoinstitucion: str
    mandante: str


MAIL_TEMPLATE_OPTIONS: list[MailTemplate] = [
    MailTemplate(
        code="TANNER_MEDIOS_PAGO",
        label="Tanner - Medios de Pago",
        message_id=87410,
        institucion="TANNER SERVICIOS FINANCIEROS",
        segmentoinstitucion="TANNER",
        mandante="Tanner",
    )
]


def get_template_by_id(template_id: int) -> Optional[MailTemplate]:
    for template in MAIL_TEMPLATE_OPTIONS:
        if template.message_id == template_id:
            return template
    return None


def get_template(code: str) -> Optional[MailTemplate]:
    for template in MAIL_TEMPLATE_OPTIONS:
        if template.code == code:
            return template
    return None


def build_mail_template(df: pd.DataFrame, template_code: str) -> pd.DataFrame:
    template = get_template(template_code)
    if not template:
        raise ValueError("Plantilla no soportada.")

    if template_code == "TANNER_MEDIOS_PAGO":
        return _build_tanner_medios_pago(df, template)

    raise ValueError("Plantilla no implementada.")


def _build_tanner_medios_pago(df: pd.DataFrame, template: MailTemplate) -> pd.DataFrame:
    base = df.copy()
    base.columns = [str(col).strip() for col in base.columns]

    rut_col = _find_column(base, {"rut+dv", "rut-dv", "rut"})
    dv_col = None
    if rut_col and "rut+dv" not in rut_col.lower().replace(" ", ""):
        dv_col = _find_column(base, {"dv", "digito", "dígito", "dv_rut"})
    op_col = _find_column(base, {"nro_operacion", "operacion", "operación", "op", "id_credito"})
    dest_col = _find_column(base, {"dest_email", "email", "correo", "mail", "dest_mail"})
    name_from_col = _find_column(base, {"name_from", "nombre_remitente"})
    mail_agente_col = _find_column(base, {"mail_agente", "correo_agente"})
    nombre_agente_col = _find_column(base, {"nombre_agente", "agente"})
    phono_col = _find_column(base, {"phono_agente", "fono_agente", "telefono_agente", "telefono", "teléfono", "telefono1"})

    if not (rut_col and op_col and dest_col and mail_agente_col and nombre_agente_col and phono_col):
        raise ValueError("Faltan columnas requeridas para la plantilla de Tanner.")

    rut_series = base[rut_col].fillna("").astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    if rut_col and "rut+dv" not in rut_col.lower().replace(" ", "") and dv_col:
        dv_series = base[dv_col].fillna("").astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
        rut_series = rut_series + "-" + dv_series

    op_series = base[op_col].fillna("").astype(str).str.replace(r"\.0$", "", regex=True).str.strip()

    mapping = _load_reenviadores()
    mail_agente_series = base[mail_agente_col].fillna("").astype(str).str.strip()
    mail_from_series = mail_agente_series.apply(lambda v: mapping.get(v.lower(), ""))

    month_name = SPANISH_MONTHS[datetime.now().month - 1]
    year_str = str(datetime.now().year)

    count = len(base)
    if name_from_col:
        name_from_series = base[name_from_col].fillna("").astype(str).str.strip()
        fallback = base[nombre_agente_col].fillna("").astype(str).str.strip()
        name_from_series = name_from_series.where(name_from_series != "", fallback)
    else:
        name_from_series = base[nombre_agente_col].fillna("").astype(str).str.strip()

    rut_values = rut_series.tolist()
    op_values = op_series.tolist()
    dest_values = base[dest_col].fillna("").astype(str).str.strip().tolist()
    name_values = name_from_series.tolist()
    mail_from_values = mail_from_series.tolist()
    nombre_agente_values = base[nombre_agente_col].fillna("").astype(str).str.strip().tolist()
    mail_agente_values = mail_agente_series.tolist()
    phono_values = base[phono_col].fillna("").astype(str).str.replace(r"\.0$", "", regex=True).str.strip().tolist()

    data = {
        "INSTITUCIÓN": [template.institucion] * count,
        "SEGMENTOINSTITUCIÓN": [template.segmentoinstitucion] * count,
        "message_id": [template.message_id] * count,
        "RUT+DV": rut_values,
        "NRO_OPERACION": op_values,
        "dest_email": dest_values,
        "name_from": name_values,
        "mail_from": mail_from_values,
        "NOMBRE_AGENTE": nombre_agente_values,
        "MAIL_AGENTE": mail_agente_values,
        "PHONO_AGENTE": phono_values,
        "MES": [month_name] * count,
        "ANO": [year_str] * count,
    }

    output = pd.DataFrame(data)
    return output.reindex(columns=TEMPLATE_COLUMNS_TANNER)


def _find_column(df: pd.DataFrame, candidates: set[str]) -> Optional[str]:
    def norm(value: str) -> str:
        return (
            value.lower()
            .replace(" ", "")
            .replace("_", "")
            .replace("-", "")
        )

    lowered = {norm(col): col for col in df.columns}
    for candidate in candidates:
        key = norm(candidate)
        if key in lowered:
            return lowered[key]
    return None


def _load_reenviadores() -> dict[str, str]:
    if not REENVIADORES_PATH.exists():
        return {}
    try:
        df = pd.read_excel(REENVIADORES_PATH)
    except PermissionError as exc:
        raise ValueError(
            "No se pudo leer 'REENVIADORES AGENTES.xlsx'. Cierra el archivo si está abierto e inténtalo nuevamente."
        ) from exc
    df.columns = [str(col).strip().lower() for col in df.columns]
    correo_col = df.columns[0]
    reenviador_col = df.columns[1]
    mapping = {}
    for _, row in df.iterrows():
        correo = str(row.get(correo_col, "")).strip().lower()
        reenviador = str(row.get(reenviador_col, "")).strip()
        if correo:
            mapping[correo] = reenviador or correo
    return mapping
