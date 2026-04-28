
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, cast
from difflib import SequenceMatcher
import re
import unicodedata
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

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

TEMPLATE_COLUMNS_SC_TELEFONIA = [
    "INSTITUCIÓN",
    "SEGMENTOINSTITUCIÓN",
    "message_id",
    "PLANTILLA",
    "CLIENTE",
    "NRO_OPERACION",
    "dest_email",
    "name_from",
    "mail_from",
    "CORREO",
]

TEMPLATE_COLUMNS_SC_TELEFONIA_MEDIOS_PAGO = [
    "INSTITUCIÓN",
    "SEGMENTOINSTITUCIÓN",
    "message_id",
    "PLANTILLA",
    "RUT",
    "dest_email",
    "name_from",
    "mail_from",
    "CORREO",
]

TEMPLATE_COLUMNS_ITAU_VENCIDA = [
    "INSTITUCIÓN",
    "SEGMENTOINSTITUCIÓN",
    "message_id",
    "RUTDV",
    "RUT ",
    "DV",
    "OPERACIONES ",
    "NOMBRE ",
    "APELLIDO_1",
    "APELLIDO_2",
    "NOMBRE COMPLETO",
    "dest_email",
    "name_from",
    "mail_from",
    "CORREO",
    "EJECUTIVO",
    "SUPERVISOR",
    "MAILS SUPERVISOR",
    "TELEFONO SUPERVISOR",
    "CARTERA",
    "CORREO_RECEPCION",
    "FONO",
    "MES_CURSO",
    "ANO_CURSO",
    "DIA_RENE",
    "MES_RENE",
    "ANO_RENE",
    "MARCA WEB Y SUCURSAL",
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
    "carterizado abril",
    "nombre agente",
}

TANNER_REQUIRED_COLUMN_LABELS = {
    "RUT+DV": {"rut+dv", "rut-dv", "rut"},
    "OPERACION": {"nro_operacion", "operacion", "operación", "op", "id_credito"},
    "dest_email": {"dest_email", "email", "correo", "mail", "dest_mail"},
    "NOMBRE_AGENTE": AGENTE_COLUMN_ALIASES,
}

TANNER_CONTACT_COLUMN_LABELS = {
    "MAIL_AGENTE": {"mail_agente", "correo_agente"},
    "PHONO_AGENTE": {"phono_agente", "fono_agente", "telefono_agente", "telefono", "teléfono", "telefono1"},
}


def _normalize_agent_text(value: str) -> str:
    return " ".join((value or "").split()).strip()


def _series(df: pd.DataFrame, col: str) -> pd.Series:
    return pd.Series(df[col])


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
        code="SC_TELEFONIA_DESCUENTO",
        label="Santander Consumer Telefonía - Descuento",
        message_id=95008,
        institucion="Santander Consumer",
        segmentoinstitucion="Santander Consumer",
        mandante="Santander Consumer Telefonía",
    ),
    MailTemplate(
        code="SC_TELEFONIA_MEDIOS_PAGO",
        label="Santander Consumer Telefonía - Medios de Pago",
        message_id=96706,
        institucion="Santander Consumer",
        segmentoinstitucion="Santander Consumer",
        mandante="Santander Consumer Telefonía",
    ),
    MailTemplate(
        code="ITAU_VENCIDA_MAIL",
        label="Itau Vencida - Mail",
        message_id=84824,
        institucion="BANCO ITAÚ",
        segmentoinstitucion="BANCO ITAÚ",
        mandante="Itau Vencida",
    ),
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

    if template_code == "SC_TELEFONIA_DESCUENTO":
        return _build_sc_telefonia_descuento(df, template)
    if template_code == "SC_TELEFONIA_MEDIOS_PAGO":
        return _build_sc_telefonia_medios_pago(df, template)
    if template_code == "ITAU_VENCIDA_MAIL":
        return _build_itau_vencida(df, template, mandante)
    if template_code in {"TANNER_MEDIOS_PAGO", "TANNER_CASTIGO"}:
        return _build_tanner_medios_pago(df, template, mandante)
    if template_code == "SCJ_COBRANZA":
        return _build_scj_cobranza(df, template, mandante)

    raise ValueError("Plantilla no implementada.")


def sample_mail_template(template_code: str) -> pd.DataFrame:
    template = get_template(template_code)
    if not template:
        raise ValueError("Plantilla no soportada.")

    if template_code == "SC_TELEFONIA_DESCUENTO":
        sample_df = pd.DataFrame({
            "NOMBRE_CLIENTE": ["CLIENTE PRUEBA UNO", "CLIENTE PRUEBA DOS"],
            "NRO_OPERACION": ["650080000001", "650080000002"],
            "MAIL": ["cliente1@example.com", "cliente2@example.com"],
        })
        return build_mail_template(sample_df, template_code, mandante="Santander Consumer Telefonía")
    if template_code == "SC_TELEFONIA_MEDIOS_PAGO":
        sample_df = pd.DataFrame({
            "RUT": ["11111111", "22222222"],
            "MAIL": ["cliente1@example.com", "cliente2@example.com"],
        })
        return build_mail_template(sample_df, template_code, mandante="Santander Consumer Telefonía")
    if template_code == "ITAU_VENCIDA_MAIL":
        sample_df = pd.DataFrame({
            "Oper": ["000000000000000002046954", "000000000000000002094727"],
            "RUT": ["13433958", "9561969"],
            "DV1": ["6", "K"],
            "Nombre": ["FELIPE EDUARDO RODAS KRAUSE", "ALBERTO AURELIO MENDEZ AMPUERO"],
            "MASIVIDAD": ["EMAIL", "EMAIL"],
            "EMAIL": ["felipe@example.com", "alberto@example.com"],
            "CARTERIZADO ABRIL": ["Jessica Carolina Diaz Mata", "Veronica Margarita Vega Bustos"],
        })
        return build_mail_template(sample_df, template_code, mandante="Itau Vencida")
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

    rut_col = _find_column(base, TANNER_REQUIRED_COLUMN_LABELS["RUT+DV"])
    dv_col = None
    if rut_col and "rut+dv" not in rut_col.lower().replace(" ", ""):
        dv_col = _find_column(base, {"dv", "digito", "dígito", "dv_rut"})
    op_col = _find_column(base, TANNER_REQUIRED_COLUMN_LABELS["OPERACION"])
    dest_col = _find_column(base, TANNER_REQUIRED_COLUMN_LABELS["dest_email"])
    name_from_col = _find_column(base, {"name_from", "nombre_remitente"})
    mail_agente_col = _find_column(base, TANNER_CONTACT_COLUMN_LABELS["MAIL_AGENTE"])
    nombre_agente_col = _find_column(base, TANNER_REQUIRED_COLUMN_LABELS["NOMBRE_AGENTE"])
    phono_col = _find_column(base, TANNER_CONTACT_COLUMN_LABELS["PHONO_AGENTE"])

    missing_required = [
        logical_name
        for logical_name, col in (
            ("RUT+DV", rut_col),
            ("OPERACION", op_col),
            ("dest_email", dest_col),
            ("NOMBRE_AGENTE", nombre_agente_col),
        )
        if col is None
    ]
    if missing_required:
        missing_details = {name: TANNER_REQUIRED_COLUMN_LABELS[name] for name in missing_required}
        raise ValueError(
            "Faltan columnas requeridas para la plantilla de Tanner: "
            + ", ".join(missing_required)
            + ". Encabezados aceptados: "
            + _format_expected_columns(missing_details)
        )

    require_fallback_columns = mandante is None
    if require_fallback_columns and (not mail_agente_col or not phono_col):
        missing_contact = [
            logical_name
            for logical_name, col in (
                ("MAIL_AGENTE", mail_agente_col),
                ("PHONO_AGENTE", phono_col),
            )
            if col is None
        ]
        missing_details = {name: TANNER_CONTACT_COLUMN_LABELS[name] for name in missing_contact}
        raise ValueError(
            "Faltan columnas de contacto del agente en el archivo de origen: "
            + ", ".join(missing_contact)
            + ". Encabezados aceptados: "
            + _format_expected_columns(missing_details)
        )

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


ITAU_SUPERVISOR = "Karen Avendaño"
ITAU_SUPERVISOR_MAIL = "kavendano@phoenixservice.cl"
ITAU_SUPERVISOR_PHONE = "442358500"
ITAU_CARTERA = "Vencida"
ITAU_CORREO_RECEPCION = "atencionclienteitauvigente@phoenixservice.cl"


def _ascii_fold(value: str) -> str:
    return unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")


def _normalize_key(value: str) -> str:
    return (
        _ascii_fold(str(value or ""))
        .lower()
        .replace(" ", "")
        .replace("_", "")
        .replace("-", "")
    )


def _normalize_phone(value: Optional[str]) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _prepare_itau_base(df: pd.DataFrame) -> pd.DataFrame:
    base = df.copy()
    base.columns = [str(col).strip() for col in base.columns]
    if _find_column(base, {"masividad"}):
        return base

    raw = df.copy()
    max_scan = min(len(raw), 15)
    header_idx = None
    required = {_normalize_key(x) for x in {"oper", "rut", "dv1", "nombre", "masividad", "email"}}
    for i in range(max_scan):
        vals = [str(v).strip() for v in raw.iloc[i].tolist()]
        keys = {_normalize_key(v) for v in vals if v}
        if required.issubset(keys):
            header_idx = i
            break
    if header_idx is None:
        return base

    headers = [str(v).strip() for v in raw.iloc[header_idx].tolist()]
    data = raw.iloc[header_idx + 1 :].copy()
    data.columns = headers
    data = data.dropna(how="all")
    data.columns = [str(col).strip() for col in data.columns]
    return data


def _resolve_itau_ejecutivo(mandante: str, agente: str) -> Optional[ejecutivos_repo.Ejecutivo]:
    raw = _normalize_agent_text(agente)
    if not raw:
        return None

    candidates = [
        raw,
        raw.lower(),
        raw.upper(),
        _ascii_fold(raw),
        _ascii_fold(raw).lower(),
        _ascii_fold(raw).upper(),
    ]
    seen: set[str] = set()
    unique = []
    for item in candidates:
        item = _normalize_agent_text(item)
        if item and item not in seen:
            seen.add(item)
            unique.append(item)

    for candidate in unique:
        found = ejecutivos_repo.fetch_by_mandante_and_nombre(mandante, candidate)
        if found:
            return found

    target = _ascii_fold(raw).lower().strip()
    if not target:
        return None
    best = None
    best_score = 0.0
    for item in ejecutivos_repo.list_ejecutivos(mandante=mandante, activos=True):
        options = [
            _ascii_fold(item.nombre_mostrar or "").lower().strip(),
            (item.nombre_clave or "").replace("_", " ").lower().strip(),
        ]
        for option in options:
            if not option:
                continue
            score = SequenceMatcher(None, target, option).ratio()
            if score > best_score:
                best_score = score
                best = item
    return best if best and best_score >= 0.92 else None


def _load_itau_seed_rows() -> list[dict[str, str]]:
    path = Path(__file__).resolve().parent.parent / "PLANTILLAS MAIL" / "ITAU VENCIDA" / "84824 ITAU VENCIDA MAIL" / "MAIL_VENCIDA_20260413.xlsx"
    if not path.exists():
        return []

    wb = load_workbook(path, data_only=True)
    ws = wb[wb.sheetnames[0]]
    headers = [str(c.value).strip() if c.value is not None else "" for c in ws[1]]
    target_map = {_normalize_key(col): col for col in TEMPLATE_COLUMNS_ITAU_VENCIDA}

    def _is_yellow(cell) -> bool:
        fill = cell.fill
        if not fill or fill.fill_type is None:
            return False
        fg = fill.fgColor
        if fg is None:
            return False
        if fg.type != "rgb":
            return False
        rgb = (fg.rgb or "").upper()
        return rgb.endswith("FFFF00") or rgb.endswith("FFD966")

    seeds: list[dict[str, str]] = []
    for row_idx in range(2, ws.max_row + 1):
        if not _is_yellow(ws.cell(row_idx, 1)):
            if seeds:
                break
            continue
        row_dict: dict[str, str] = {}
        for col_idx, header in enumerate(headers, start=1):
            if not header:
                continue
            mapped = target_map.get(_normalize_key(header))
            if not mapped:
                continue
            value = ws.cell(row_idx, col_idx).value
            row_dict[mapped] = str(value).strip() if value is not None else ""
        if any(str(v).strip() for v in row_dict.values()):
            seeds.append(row_dict)

    return seeds


def _build_itau_vencida(df: pd.DataFrame, template: MailTemplate, mandante: Optional[str]) -> pd.DataFrame:
    base = _prepare_itau_base(df)

    oper_col = _find_column(base, {"oper", "operacion", "nro_operacion", "id_credito"})
    rut_col = _find_column(base, {"rut", "rut_cliente", "id_cliente"})
    dv_col = _find_column(base, {"dv1", "dv", "digito", "dígito", "dv_rut"})
    nombre_col = _find_column(base, {"nombre", "nombre_cliente", "cliente", "contacto"})
    masividad_col = _find_column(base, {"masividad", "tipo", "canal"})
    email_col = _find_column(base, {"email", "mail", "correo", "dest_email", "dest_mail"})
    agente_col = _find_column(base, AGENTE_COLUMN_ALIASES)

    required = {
        "Oper": oper_col,
        "RUT": rut_col,
        "DV": dv_col,
        "Nombre": nombre_col,
        "MASIVIDAD": masividad_col,
        "EMAIL": email_col,
        "CARTERIZADO": agente_col,
    }
    missing = [name for name, col in required.items() if col is None]
    if missing:
        raise ValueError("Faltan columnas requeridas para plantilla Itau Vencida: " + ", ".join(missing))

    oper_col = str(oper_col)
    rut_col = str(rut_col)
    dv_col = str(dv_col)
    nombre_col = str(nombre_col)
    masividad_col = str(masividad_col)
    email_col = str(email_col)
    agente_col = str(agente_col)

    masividad_series = _series(base, masividad_col).fillna("").astype(str).str.strip().str.upper()
    filtered = cast(pd.DataFrame, base.loc[masividad_series == "EMAIL"].copy())
    if filtered.empty:
        raise ValueError("La base no contiene filas con MASIVIDAD = EMAIL.")

    rut_series = _series(filtered, rut_col).fillna("").astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    dv_series = _series(filtered, dv_col).fillna("").astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    rutdv_series = rut_series + "-" + dv_series
    oper_series = _series(filtered, oper_col).fillna("").astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    nombre_series = (
        _series(filtered, nombre_col)
        .fillna("")
        .astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )
    email_series = _series(filtered, email_col).fillna("").astype(str).str.strip()
    agente_series = (
        _series(filtered, agente_col)
        .fillna("")
        .astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )

    month_name = SPANISH_MONTHS[datetime.now().month - 1].upper()
    year_str = str(datetime.now().year)
    mandante_resolve = mandante or template.mandante

    records: list[dict[str, str]] = []
    for idx, agente in enumerate(agente_series.tolist()):
        ejecutivo = _resolve_itau_ejecutivo(mandante_resolve, agente)
        ejecutivo_name = _normalize_agent_text((ejecutivo.nombre_mostrar if ejecutivo else "") or agente)
        mail_from = (ejecutivo.reenviador if ejecutivo else "") or (ejecutivo.correo if ejecutivo else "") or ""
        correo = (ejecutivo.correo if ejecutivo else "") or ""
        fono = _normalize_phone(ejecutivo.telefono if ejecutivo else "")
        records.append({
            "INSTITUCIÓN": template.institucion,
            "SEGMENTOINSTITUCIÓN": template.segmentoinstitucion,
            "message_id": str(template.message_id),
            "RUTDV": rutdv_series.iloc[idx],
            "RUT ": rut_series.iloc[idx],
            "DV": dv_series.iloc[idx],
            "OPERACIONES ": oper_series.iloc[idx],
            "NOMBRE ": nombre_series.iloc[idx],
            "APELLIDO_1": "",
            "APELLIDO_2": "",
            "NOMBRE COMPLETO": nombre_series.iloc[idx],
            "dest_email": email_series.iloc[idx],
            "name_from": ejecutivo_name,
            "mail_from": str(mail_from).strip(),
            "CORREO": str(correo).strip(),
            "EJECUTIVO": ejecutivo_name,
            "SUPERVISOR": ITAU_SUPERVISOR,
            "MAILS SUPERVISOR": ITAU_SUPERVISOR_MAIL,
            "TELEFONO SUPERVISOR": ITAU_SUPERVISOR_PHONE,
            "CARTERA": ITAU_CARTERA,
            "CORREO_RECEPCION": ITAU_CORREO_RECEPCION,
            "FONO": fono,
            "MES_CURSO": month_name,
            "ANO_CURSO": year_str,
            "DIA_RENE": "",
            "MES_RENE": "",
            "ANO_RENE": "",
            "MARCA WEB Y SUCURSAL": "",
        })

    if not records:
        raise ValueError("No se encontró ningún ejecutivo válido para Itau Vencida en la base EMAIL.")

    output = pd.DataFrame(records).reindex(columns=TEMPLATE_COLUMNS_ITAU_VENCIDA)

    seeds = _load_itau_seed_rows()
    if not seeds:
        return output
    seeds_df = pd.DataFrame(seeds).reindex(columns=TEMPLATE_COLUMNS_ITAU_VENCIDA).fillna("")
    return pd.concat([seeds_df, output], ignore_index=True)


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


SC_TELEFONIA_PLANTILLA = "TEMPRANA"
SC_TELEFONIA_NAME_FROM = "Atencion Cliente Consumer"
SC_TELEFONIA_MAIL_FROM = "tfernandez@info.phoenixserviceinfo.cl"
SC_TELEFONIA_CORREO = "tfernandez@phoenixservice.cl"
SEED_EMAIL = "pipe5550@gmail.com"

SC_TELEFONIA_MP_PLANTILLA = "TEMPRANA"
SC_TELEFONIA_MP_NAME_FROM = "Atencion Cliente Consumer"
SC_TELEFONIA_MP_MAIL_FROM = "atencionclientes@estandar.phoenixserviceinfo.cl"
SC_TELEFONIA_MP_CORREO = "tfernandez@phoenixservice.cl"


def _load_sc_telefonia_seed_rows() -> list[dict[str, str]]:
    return [{
        "INSTITUCIÓN": "Santander Consumer",
        "SEGMENTOINSTITUCIÓN": "Santander Consumer",
        "message_id": "95008",
        "PLANTILLA": SC_TELEFONIA_PLANTILLA,
        "CLIENTE": "PRB",
        "NRO_OPERACION": "PRB",
        "dest_email": SEED_EMAIL,
        "name_from": SC_TELEFONIA_NAME_FROM,
        "mail_from": SC_TELEFONIA_MAIL_FROM,
        "CORREO": SC_TELEFONIA_CORREO,
    }]


def _build_sc_telefonia_descuento(df: pd.DataFrame, template: MailTemplate) -> pd.DataFrame:
    base = df.copy()
    base.columns = [str(col).strip() for col in base.columns]

    cliente_col = _find_column(base, {"nombre_cliente", "cliente", "nombre"})
    oper_col = _find_column(base, {"nro_operacion", "operacion", "operación", "op", "num_op"})
    email_col = _find_column(base, {"mail", "email", "correo", "dest_email", "dest_mail"})

    if not (cliente_col and oper_col and email_col):
        raise ValueError("Faltan columnas requeridas para Santander Consumer Telefonía (cliente, operacion, mail).")

    cliente = base[cliente_col].fillna("").astype(str).str.strip()
    oper = base[oper_col].fillna("").astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    dest_email = base[email_col].fillna("").astype(str).str.strip()

    output = pd.DataFrame({
        "INSTITUCIÓN": [template.institucion] * len(base),
        "SEGMENTOINSTITUCIÓN": [template.segmentoinstitucion] * len(base),
        "message_id": [template.message_id] * len(base),
        "PLANTILLA": [SC_TELEFONIA_PLANTILLA] * len(base),
        "CLIENTE": cliente.tolist(),
        "NRO_OPERACION": oper.tolist(),
        "dest_email": dest_email.tolist(),
        "name_from": [SC_TELEFONIA_NAME_FROM] * len(base),
        "mail_from": [SC_TELEFONIA_MAIL_FROM] * len(base),
        "CORREO": [SC_TELEFONIA_CORREO] * len(base),
    }).reindex(columns=TEMPLATE_COLUMNS_SC_TELEFONIA)

    seeds = _load_sc_telefonia_seed_rows()
    if not seeds:
        return output
    seed_df = pd.DataFrame(seeds).reindex(columns=TEMPLATE_COLUMNS_SC_TELEFONIA).fillna("")
    return pd.concat([seed_df, output], ignore_index=True)


def _build_sc_telefonia_medios_pago(df: pd.DataFrame, template: MailTemplate) -> pd.DataFrame:
    base = df.copy()
    base.columns = [str(col).strip() for col in base.columns]

    rut_col = _find_column(base, {"rut", "rut_cliente", "id_cliente"})
    email_col = _find_column(base, {"mail", "email", "correo", "dest_email", "dest_mail"})

    if not (rut_col and email_col):
        raise ValueError("Faltan columnas requeridas para Medios de Pago Telefonía (RUT y MAIL).")

    rut = base[rut_col].fillna("").astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    dest_email = base[email_col].fillna("").astype(str).str.strip()

    output = pd.DataFrame({
        "INSTITUCIÓN": [template.institucion] * len(base),
        "SEGMENTOINSTITUCIÓN": [template.segmentoinstitucion] * len(base),
        "message_id": [template.message_id] * len(base),
        "PLANTILLA": [SC_TELEFONIA_MP_PLANTILLA] * len(base),
        "RUT": rut.tolist(),
        "dest_email": dest_email.tolist(),
        "name_from": [SC_TELEFONIA_MP_NAME_FROM] * len(base),
        "mail_from": [SC_TELEFONIA_MP_MAIL_FROM] * len(base),
        "CORREO": [SC_TELEFONIA_MP_CORREO] * len(base),
    })
    output = output.reindex(columns=TEMPLATE_COLUMNS_SC_TELEFONIA_MEDIOS_PAGO)
    seed = pd.DataFrame([
        {
            "INSTITUCIÓN": "Santander Consumer",
            "SEGMENTOINSTITUCIÓN": "Santander Consumer",
            "message_id": "96706",
            "PLANTILLA": SC_TELEFONIA_MP_PLANTILLA,
            "RUT": "PRB",
            "dest_email": SEED_EMAIL,
            "name_from": SC_TELEFONIA_MP_NAME_FROM,
            "mail_from": SC_TELEFONIA_MP_MAIL_FROM,
            "CORREO": SC_TELEFONIA_MP_CORREO,
        }
    ]).reindex(columns=TEMPLATE_COLUMNS_SC_TELEFONIA_MEDIOS_PAGO)
    return pd.concat([seed, output], ignore_index=True)


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


def _format_expected_columns(field_map: dict[str, set[str]]) -> str:
    parts = []
    for logical_name, aliases in field_map.items():
        alias_list = ", ".join(sorted(aliases))
        parts.append(f"{logical_name} ({alias_list})")
    return "; ".join(parts)


