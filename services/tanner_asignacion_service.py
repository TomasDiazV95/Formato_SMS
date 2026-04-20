from __future__ import annotations

from datetime import datetime
import re
import unicodedata

import pandas as pd


COLUMNAS_CRM = [
    "Nro_Documento", "RUT - DV", "NOMBRE", "AD1", "NombreProducto", "AD2", "AD3", "AD4", "AD5", "AD6", "AD7",
    "DEUDA TOTAL", "AD11", "AD8", "AD9", "AD10", "DIRECCION", "COMUNA", "CIUDAD", "REGION", "DIRECCION_COMERCIAL",
    "COMUNA_COMERCIAL", "CIUDAD_COMERCIAL", "REGION_COMERCIAL", "EMAIL1", "AD13", "FONO1", "FONO2", "FONO3", "FONO4",
    "FONO5", "FONO6", "AD14", "AD15", "TIPO_DEUDOR", "TIPO_PRODUCTO 1", "AFINIDAD_1", "NRO_PRODUCTO 1", "FECHA_VEN_1",
    "COD_SEG_1", "ID_BANCO_1", "TIPO_PRODUCTO_2", "AFINIDAD_2", "NRO_PRODUCTO_2", "FECHA_VEN_2", "COD_SEG_2", "ID_BANCO_2",
    "TIPO_PRODUCTO_3", "AFINIDAD_3", "NRO_PRODUCTO_3", "FECHA_VEN_3", "COD_SEG_3", "ID_BANCO_3", "TIPO_PRODUCTO_4", "AFINIDAD_4",
    "NRO_PRODUCTO_4", "FECHA_VEN_4", "COD_SEG_4", "ID_BANCO_4", "TIPO_PRODUCTO_5", "AFINIDAD_5", "NRO_PRODUCTO_5", "FECHA_VEN_5",
    "COD_SEG_5", "ID_BANCO_5", "PRIMER_NOMBRE", "SEGUNDO_NOMBRE", "APE_PATERNO", "APE_MATERNO", "EDAD", "SEXO", "FECHA_NAC",
    "NUMERO", "DEPARTAMENTO", "POBLACION",
]


TRAMO_TO_MARCA = {
    "1-30": "1-30",
    "31-60": "31-60",
    "61-90": "C4",
    "91-120": "+90",
    "121-150": "+90",
    "151-180": "+90",
    "181-210": "+90",
    "211-240": "+90",
    "241-270": "+90",
    "271-300": "+90",
    "301-330": "+90",
    "331-360": "+90",
    "361-390": "+90",
    "366-730": "+90",
    "731-1095": "+90",
    "0-365": "CASTIGO",
}


def _normalize_key(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip().replace(" ", "").replace("_", "")
    return re.sub(r"[^a-z0-9]", "", text)


def _find_col(df: pd.DataFrame, aliases: set[str]) -> str | None:
    idx = {_normalize_key(c): c for c in df.columns}
    for alias in aliases:
        key = _normalize_key(alias)
        if key in idx:
            return idx[key]
    return None


def _text(series: pd.Series) -> pd.Series:
    out = series.fillna("").astype(str).str.strip()
    out = out.str.replace(r"\.0$", "", regex=True)
    return out.replace(r"^\s*$", " ", regex=True)


def _date(series: pd.Series) -> pd.Series:
    base = _text(series)
    parsed_dmy = pd.to_datetime(base, format="%d-%m-%Y", errors="coerce")
    parsed_ymd = pd.to_datetime(base, format="%Y-%m-%d", errors="coerce")
    parsed = parsed_dmy.fillna(parsed_ymd)
    return parsed.dt.strftime("%d-%m-%Y").fillna(" ")


def _normalize_tramo(series: pd.Series) -> pd.Series:
    return (
        _text(series)
        .str.replace(r"[–—−]", "-", regex=True)
        .str.replace(r"\s+", "", regex=True)
    )


def build_tanner_asignacion(df_input: pd.DataFrame) -> pd.DataFrame:
    df = df_input.copy()
    df.columns = [str(c).replace("\ufeff", "").strip() for c in df.columns]

    id_credito_col = _find_col(df, {"ID_CREDITO", "IDCREDITO", "NRO_OPERACION", "OPERACION"})
    rut_col = _find_col(df, {"RUT"})
    dv_col = _find_col(df, {"DV"})
    nombre_col = _find_col(df, {"RAZON_SOCIAL", "NOMBRE_CLIENTE"})
    tramo_col = _find_col(df, {"TRAMO_INI"})
    estado_jud_col = _find_col(df, {"ESTADO_JUDICIAL"})
    valor_cuota_col = _find_col(df, {"VALOR_CUOTA"})
    fecha_vcto_col = _find_col(df, {"FECHA_PROX_VCTO"})
    monto_adeudado_col = _find_col(df, {"MONTO_ADEUDADO"})
    saldo_insoluto_col = _find_col(df, {"SALDO_INSOLUTO_INI"})
    patente_col = _find_col(df, {"VEHICULO_1_PATENTE"})
    campana_col = _find_col(df, {"CAMPANAS"})
    tribunal_col = _find_col(df, {"TRIBUNAL"})
    email_col = _find_col(df, {"EMAIL_1", "EMAIL"})
    fono1_col = _find_col(df, {"TELEFONO_1"})
    fono2_col = _find_col(df, {"TELEFONO_2"})
    fono3_col = _find_col(df, {"TELEFONO_3"})

    required = {
        "ID_CREDITO": id_credito_col,
        "RUT": rut_col,
        "DV": dv_col,
        "RAZON_SOCIAL": nombre_col,
        "TRAMO_INI": tramo_col,
        "EMAIL_1": email_col,
    }
    missing = [k for k, v in required.items() if v is None]
    if missing:
        raise ValueError("Faltan columnas requeridas en base Tanner: " + ", ".join(missing))

    tramo_norm = _normalize_tramo(df[tramo_col])
    nombre_producto = tramo_norm.map(TRAMO_TO_MARCA).fillna("SIN MARCA")

    out = pd.DataFrame({c: " " for c in COLUMNAS_CRM}, index=df.index)
    out["Nro_Documento"] = _text(df[id_credito_col])
    out["RUT - DV"] = _text(df[rut_col]).str.cat(_text(df[dv_col]), sep="-", na_rep=" ")
    out["NOMBRE"] = _text(df[nombre_col])
    out["NombreProducto"] = nombre_producto.astype(str)
    out["AD3"] = _text(df[tramo_col])
    out["AD4"] = _text(df[estado_jud_col]) if estado_jud_col else " "
    out["AD5"] = _text(df[valor_cuota_col]) if valor_cuota_col else " "
    out["AD6"] = _date(df[fecha_vcto_col]) if fecha_vcto_col else " "
    out["DEUDA TOTAL"] = _text(df[monto_adeudado_col]) if monto_adeudado_col else " "
    out["AD11"] = _text(df[saldo_insoluto_col]) if saldo_insoluto_col else " "
    out["AD8"] = _text(df[patente_col]) if patente_col else " "
    out["AD9"] = _text(df[campana_col]) if campana_col else " "
    out["AD10"] = _text(df[tribunal_col]) if tribunal_col else " "
    out["EMAIL1"] = _text(df[email_col])
    out["FONO1"] = _text(df[fono1_col]) if fono1_col else " "
    out["FONO2"] = _text(df[fono2_col]) if fono2_col else " "
    out["FONO3"] = _text(df[fono3_col]) if fono3_col else " "

    out = out.fillna(" ")
    for col in out.columns:
        out[col] = out[col].astype(str).str.strip()
    out = out.replace("", " ")
    out = out.replace("-", " ")
    return out


def tanner_asignacion_filename() -> str:
    return f"ASIGNACION_TANNER_{datetime.now().strftime('%d-%m-%y')}.xlsx"
