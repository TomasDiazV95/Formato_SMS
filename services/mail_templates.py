
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pandas as pd

from services import ejecutivos_repo

TEMPLATE_COLUMNS_TANNER = [
    "INSTITUCIÓN",
    "SEGMENTOINSTITUCIÓN",
    "message_id",
    "RUT+DV",
    "OPERACION",
    "dest_email",
    "name_from",
    "mail_from",
    "NOMBRE_AGENTE",
    "MAIL_AGENTE",
    "PHONO_AGENTE",
    "MES",
    "ANO",
]

TEMPLATE_COLUMNS_SCJ = [
    "INSTITUCIÓN",
    "SEGMENTOINSTITUCIÓN",
    "message_id",
    "PLANTILLA",
    "RUT",
    "NUM_OP",
    "name_from",
    "dest_email",
    "mail_from",
    "MAIL_AGENTE",
    "PHONO_AGENTE",
    "telefono",
    "NOMBRE_AGENTE",
]

SPANISH_MONTHS = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

AGENTE_COLUMN_ALIASES = {
    "nombre_agente",
    "agente",
    "agentes",
    "ejecutivo",
    "ejecutivos",
    "carterizado",
    "carterizados",
    "nombre agente",
}


def _normalize_agent_text(value: str) -> str:
    return " ".join((value or "").split()).strip()


@dataclass
class MailTemplate:
    code: str
    label: str
    message_id: int
    institucion: str
    segmentoinstitucion: str
    mandante: str

    def display_label(self) -> str:
        return f"{self.label} (ID: {self.message_id})"


MAIL_TEMPLATE_OPTIONS: list[MailTemplate] = [
    MailTemplate(
        code="TANNER_MEDIOS_PAGO",
        label="Tanner - Medios de Pago",
        message_id=91869,
        institucion="TANNER SERVICIOS FINANCIEROS",
        segmentoinstitucion="TANNER",
        mandante="Tanner",
    ),
    MailTemplate(
        code="TANNER_CASTIGO",
        label="Tanner - Castigo",
        message_id=96830,
        institucion="TANNER SERVICIOS FINANCIEROS",
        segmentoinstitucion="TANNER",
        mandante="Tanner",
    ),
    MailTemplate(
        code="SCJ_COBRANZA",
        label="Santander Consumer Judicial - Cobranza",
        message_id=86257,
        institucion="SANTANDER CONSUMER",
        segmentoinstitucion="SANTANDER CONSUMER",
        mandante="Santander Consumer Judicial",
    ),
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


def build_mail_template(df: pd.DataFrame, template_code: str, mandante: Optional[str] = None) -> pd.DataFrame:
    template = get_template(template_code)
    if not template:
        raise ValueError("Plantilla no soportada.")

    if template_code in {"TANNER_MEDIOS_PAGO", "TANNER_CASTIGO"}:
        return _build_tanner_medios_pago(df, template, mandante)
    if template_code == "SCJ_COBRANZA":
        return _build_scj_cobranza(df, template, mandante)

    raise ValueError("Plantilla no implementada.")


def sample_mail_template(template_code: str) -> pd.DataFrame:
    template = get_template(template_code)
    if not template:
        raise ValueError("Plantilla no soportada.")

    if template_code in {"TANNER_MEDIOS_PAGO", "TANNER_CASTIGO"}:
        sample_df = pd.DataFrame({
            "RUT+DV": ["11.111.111-1", "22.222.222-2"],
            "OPERACION": ["890123", "567890"],
            "dest_email": ["cliente1@example.com", "cliente2@example.com"],
            "NOMBRE_AGENTE": ["Juan Pérez", "Ana Díaz"],
            "MAIL_AGENTE": ["agente1@tanner.cl", "agente2@tanner.cl"],
            "PHONO_AGENTE": ["56912345678", "56987654321"],
            "name_from": ["Juan Pérez", "Ana Díaz"],
        })
        return build_mail_template(sample_df, template_code, mandante=None)
    if template_code == "SCJ_COBRANZA":
        sample_df = pd.DataFrame({
            "RUT": ["11.111.111-1", "22.222.222-2"],
            "NUM_OP": ["123456789", "987654321"],
            "dest_email": ["cliente1@example.com", "cliente2@example.com"],
            "NOMBRE_AGENTE": ["Ariel Silva", "Martina Parra"],
            "MAIL_AGENTE": ["asilva@phlegal.cl", "mparra@phlegal.cl"],
            "PHONO_AGENTE": ["56911111111", "56922222222"],
            "name_from": ["Ariel Silva", "Martina Parra"],
        })
        return build_mail_template(sample_df, template_code, mandante="Santander Consumer Judicial")

    raise ValueError("Plantilla no implementada para ejemplo.")


def _build_tanner_medios_pago(df: pd.DataFrame, template: MailTemplate, mandante: Optional[str]) -> pd.DataFrame:
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
    nombre_agente_col = _find_column(base, AGENTE_COLUMN_ALIASES)
    phono_col = _find_column(base, {"phono_agente", "fono_agente", "telefono_agente", "telefono", "teléfono", "telefono1"})

    if not (rut_col and op_col and dest_col and nombre_agente_col):
        raise ValueError("Faltan columnas requeridas para la plantilla de Tanner.")

    require_fallback_columns = mandante is None
    if require_fallback_columns and (not mail_agente_col or not phono_col):
        raise ValueError("Faltan columnas de contacto del agente en el archivo de origen.")

    rut_series = base[rut_col].fillna("").astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    if rut_col and "rut+dv" not in rut_col.lower().replace(" ", "") and dv_col:
        dv_series = base[dv_col].fillna("").astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
        rut_series = rut_series + "-" + dv_series

    op_series = base[op_col].fillna("").astype(str).str.replace(r"\.0$", "", regex=True).str.strip()

    month_name = SPANISH_MONTHS[datetime.now().month - 1]
    year_str = str(datetime.now().year)

    count = len(base)
    dest_values = base[dest_col].fillna("").astype(str).str.strip().tolist()
    nombre_agente_series = (
        base[nombre_agente_col]
        .fillna("")
        .astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )
    name_from_base = (
        base[name_from_col]
        .fillna("")
        .astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
        if name_from_col
        else nombre_agente_series
    )

    nombre_agente_values = []
    mail_agente_values = []
    phono_values = []
    mail_from_values = []
    name_from_values = []

    exec_cache: dict[tuple[str, str], Optional[ejecutivos_repo.Ejecutivo]] = {}

    def _get_ejecutivo(agente: str) -> Optional[ejecutivos_repo.Ejecutivo]:
        if not mandante or not agente:
            return None
        key = (mandante.lower(), agente.lower())
        if key not in exec_cache:
            exec_cache[key] = ejecutivos_repo.fetch_by_mandante_and_nombre(mandante, agente)
        return exec_cache[key]

    for idx, row in base.iterrows():
        agente_val = _normalize_agent_text(nombre_agente_series.iloc[idx])
        ejecutivo = _get_ejecutivo(agente_val)

        if ejecutivo:
            nombre_agente = ejecutivo.nombre_mostrar or agente_val
            mail_agente = ejecutivo.correo or ""
            phono = ejecutivo.telefono or ""
            mail_from = ejecutivo.reenviador or ejecutivo.correo or mail_agente or ""
            name_from = ejecutivo.nombre_mostrar or nombre_agente
        else:
            mail_agente = (
                str(row.get(mail_agente_col, "")).strip()
                if mail_agente_col
                else ""
            )
            phono = (
                str(row.get(phono_col, "")).strip()
                if phono_col
                else ""
            )
            nombre_agente = agente_val or _normalize_agent_text(name_from_base.iloc[idx])
            mail_from = mail_agente
            name_from = name_from_base.iloc[idx]

            if mandante and not mail_agente:
                raise ValueError(
                    f"No se encontró el ejecutivo '{agente_val}' para mandante {mandante} y el archivo no entrega correo del agente."
                )

        nombre_agente_values.append(_normalize_agent_text(nombre_agente))
        mail_agente_values.append(mail_agente)
        phono_values.append(phono)
        mail_from_values.append(mail_from)
        name_from_values.append(name_from or nombre_agente)

    data = {
        "INSTITUCIÓN": [template.institucion] * count,
        "SEGMENTOINSTITUCIÓN": [template.segmentoinstitucion] * count,
        "message_id": [template.message_id] * count,
        "RUT+DV": rut_series.tolist(),
        "OPERACION": op_series.tolist(),
        "dest_email": dest_values,
        "name_from": name_from_values,
        "mail_from": mail_from_values,
        "NOMBRE_AGENTE": nombre_agente_values,
        "MAIL_AGENTE": mail_agente_values,
        "PHONO_AGENTE": phono_values,
        "MES": [month_name] * count,
        "ANO": [year_str] * count,
    }

    output = pd.DataFrame(data)
    return output.reindex(columns=TEMPLATE_COLUMNS_TANNER)


SCJ_PLANTILLA_VALUE = "CobranzaP"
SCJ_TELEFONO = "930609666"


def _build_scj_cobranza(df: pd.DataFrame, template: MailTemplate, mandante: Optional[str]) -> pd.DataFrame:
    base = df.copy()
    base.columns = [str(col).strip() for col in base.columns]

    rut_col = _find_column(base, {"rut+dv", "rut", "rut_cliente", "id_cliente"})
    dv_col = None
    if rut_col and "rut+dv" not in rut_col.lower().replace(" ", ""):
        dv_col = _find_column(base, {"dv", "digito", "dígito", "dv_rut"})
    op_col = _find_column(base, {"num_op", "nro_operacion", "operacion", "operación", "op", "id_credito"})
    dest_col = _find_column(base, {"dest_email", "email", "correo", "mail", "dest_mail"})
    name_from_col = _find_column(base, {"name_from", "nombre_remitente"})
    mail_agente_col = _find_column(base, {"mail_agente", "correo_agente"})
    nombre_agente_col = _find_column(base, AGENTE_COLUMN_ALIASES)
    phono_col = _find_column(base, {"phono_agente", "fono_agente", "telefono_agente", "telefono"})

    if not (rut_col and op_col and dest_col):
        raise ValueError("Faltan columnas requeridas para la plantilla de Santander Consumer Judicial.")

    rut_series = base[rut_col].fillna("").astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    if rut_col and "rut+dv" not in rut_col.lower().replace(" ", "") and dv_col:
        dv_series = base[dv_col].fillna("").astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
        rut_series = rut_series + "-" + dv_series

    op_series = base[op_col].fillna("").astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    dest_values = base[dest_col].fillna("").astype(str).str.strip().tolist()

    nombre_agente_series = (
        base[nombre_agente_col]
        .fillna("")
        .astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
        if nombre_agente_col else pd.Series([""] * len(base), index=base.index)
    )
    name_from_base = (
        base[name_from_col]
        .fillna("")
        .astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
        if name_from_col else nombre_agente_series
    )

    nombre_agente_values = []
    mail_agente_values = []
    phono_values = []
    mail_from_values = []
    name_from_values = []

    exec_cache: dict[tuple[str, str], Optional[ejecutivos_repo.Ejecutivo]] = {}

    def _get_ejecutivo(agente: str) -> Optional[ejecutivos_repo.Ejecutivo]:
        if not mandante or not agente:
            return None
        key = (mandante.lower(), agente.lower())
        if key not in exec_cache:
            exec_cache[key] = ejecutivos_repo.fetch_by_mandante_and_nombre(mandante, agente)
        return exec_cache[key]

    for idx, row in base.iterrows():
        agente_val = _normalize_agent_text(nombre_agente_series.iloc[idx])
        ejecutivo = _get_ejecutivo(agente_val)

        if ejecutivo:
            nombre_agente = ejecutivo.nombre_mostrar or agente_val or name_from_base.iloc[idx]
            mail_agente = ejecutivo.correo or ""
            phono = ejecutivo.telefono or ""
            mail_from = ejecutivo.reenviador or ejecutivo.correo or mail_agente or ""
            name_from = ejecutivo.nombre_mostrar or nombre_agente
        else:
            mail_agente = (
                str(row.get(mail_agente_col, "")).strip()
                if mail_agente_col else ""
            )
            phono = (
                str(row.get(phono_col, "")).strip()
                if phono_col else ""
            )
            nombre_agente = agente_val or _normalize_agent_text(name_from_base.iloc[idx])
            mail_from = mail_agente
            name_from = name_from_base.iloc[idx]

            if mandante and not mail_agente:
                raise ValueError(
                    f"No se encontró el ejecutivo '{agente_val}' para mandante {mandante} y el archivo no entrega correo del agente."
                )

        nombre_agente_values.append(_normalize_agent_text(nombre_agente))
        mail_agente_values.append(mail_agente)
        phono_values.append(phono)
        mail_from_values.append(mail_from or mail_agente)
        name_from_values.append(name_from or nombre_agente)

    data = {
        "INSTITUCIÓN": [template.institucion] * len(base),
        "SEGMENTOINSTITUCIÓN": [template.segmentoinstitucion] * len(base),
        "message_id": [template.message_id] * len(base),
        "PLANTILLA": [SCJ_PLANTILLA_VALUE] * len(base),
        "RUT": rut_series.tolist(),
        "NUM_OP": op_series.tolist(),
        "name_from": name_from_values,
        "dest_email": dest_values,
        "mail_from": mail_from_values,
        "MAIL_AGENTE": mail_agente_values,
        "PHONO_AGENTE": phono_values,
        "telefono": [SCJ_TELEFONO] * len(base),
        "NOMBRE_AGENTE": nombre_agente_values,
    }

    output = pd.DataFrame(data)
    return output.reindex(columns=TEMPLATE_COLUMNS_SCJ)


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


