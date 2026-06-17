from __future__ import annotations

from datetime import datetime
from typing import Optional, cast

import pandas as pd

from services.contact_dedupe import dedupe_by_column_keep_first


def build_itau_vencida(df: pd.DataFrame, template, mandante: Optional[str]) -> pd.DataFrame:
    from services import mail_templates as mt

    base = mt._prepare_itau_base(df)

    oper_col = mt._find_column(base, {"oper", "operacion", "nro_operacion", "id_credito"})
    rut_col = mt._find_column(base, {"rut", "rut_cliente", "id_cliente"})
    dv_col = mt._find_column(base, {"dv1", "dv", "digito", "dígito", "dv_rut"})
    nombre_col = mt._find_column(base, {"nombre", "nombre_cliente", "cliente", "contacto"})
    masividad_col = mt._find_column(base, {"masividad", "tipo", "canal"})
    email_col = mt._find_column(base, {"email", "mail", "correo", "dest_email", "dest_mail"})
    agente_col = mt._find_column(base, mt.AGENTE_COLUMN_ALIASES)

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

    base = dedupe_by_column_keep_first(base, rut_col).reset_index(drop=True)

    oper_col = str(oper_col)
    rut_col = str(rut_col)
    dv_col = str(dv_col)
    nombre_col = str(nombre_col)
    masividad_col = str(masividad_col)
    email_col = str(email_col)
    agente_col = str(agente_col)

    masividad_series = mt._series(base, masividad_col).fillna("").astype(str).str.strip().str.upper()
    filtered = cast(pd.DataFrame, base.loc[masividad_series == "EMAIL"].copy())
    if filtered.empty:
        raise ValueError("La base no contiene filas con MASIVIDAD = EMAIL.")

    rut_series = mt._series(filtered, rut_col).fillna("").astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    dv_series = mt._series(filtered, dv_col).fillna("").astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    rutdv_series = rut_series + "-" + dv_series
    oper_series = mt._series(filtered, oper_col).fillna("").astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    nombre_series = (
        mt._series(filtered, nombre_col)
        .fillna("")
        .astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )
    email_series = mt._series(filtered, email_col).fillna("").astype(str).str.strip()
    agente_series = (
        mt._series(filtered, agente_col)
        .fillna("")
        .astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )

    month_name = mt.SPANISH_MONTHS[datetime.now().month - 1].upper()
    year_str = str(datetime.now().year)
    mandante_resolve = mandante or template.mandante

    records: list[dict[str, str]] = []
    for idx, agente in enumerate(agente_series.tolist()):
        ejecutivo = mt._resolve_itau_ejecutivo(mandante_resolve, agente)
        ejecutivo_name = mt._normalize_agent_text((ejecutivo.nombre_mostrar if ejecutivo else "") or agente)
        mail_from = (ejecutivo.reenviador if ejecutivo else "") or (ejecutivo.correo if ejecutivo else "") or ""
        correo = (ejecutivo.correo if ejecutivo else "") or ""
        fono = mt._normalize_phone(ejecutivo.telefono if ejecutivo else "")
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
            "SUPERVISOR": mt.ITAU_SUPERVISOR,
            "MAILS SUPERVISOR": mt.ITAU_SUPERVISOR_MAIL,
            "TELEFONO SUPERVISOR": mt.ITAU_SUPERVISOR_PHONE,
            "CARTERA": mt.ITAU_CARTERA,
            "CORREO_RECEPCION": mt.ITAU_CORREO_RECEPCION,
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

    output = pd.DataFrame(records).reindex(columns=mt.TEMPLATE_COLUMNS_ITAU_VENCIDA)

    seeds = mt._load_itau_seed_rows()
    if not seeds:
        return output
    seeds_df = pd.DataFrame(seeds).reindex(columns=mt.TEMPLATE_COLUMNS_ITAU_VENCIDA).fillna("")
    return pd.concat([seeds_df, output], ignore_index=True)
