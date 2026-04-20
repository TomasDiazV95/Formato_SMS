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


def _normalize_text(value: str) -> str:
    txt = unicodedata.normalize("NFKD", str(value or ""))
    txt = txt.encode("ascii", "ignore").decode("ascii")
    txt = txt.lower()
    txt = re.sub(r"[^a-z0-9]+", "", txt)
    return txt


def _find_header_row(raw: pd.DataFrame) -> int:
    target = _normalize_text("N° Contrato")
    for i in range(len(raw.index)):
        vals = raw.iloc[i].fillna("").astype(str).tolist()
        if any(_normalize_text(v) == target for v in vals):
            return i
    raise ValueError("No se encontro la fila de encabezados (que contenga 'N° Contrato').")


def _find_col(df: pd.DataFrame, aliases: set[str]) -> str | None:
    by_norm = {_normalize_text(col): col for col in df.columns}
    for alias in aliases:
        key = _normalize_text(alias)
        if key in by_norm:
            return by_norm[key]
    return None


def _as_clean_text(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.replace(r"\.0$", "", regex=True).str.strip()


def build_porsche_asignacion(df_input: pd.DataFrame) -> pd.DataFrame:
    raw = df_input.copy()
    header_idx = _find_header_row(raw)

    headers = raw.iloc[header_idx].fillna("").astype(str).str.strip().tolist()
    df = raw.iloc[header_idx + 1 :].copy()
    df.columns = headers
    df = df.dropna(how="all").reset_index(drop=True)

    contrato_col = _find_col(df, {"N° Contrato", "Nro Contrato", "No Contrato"})
    rut_col = _find_col(df, {"Rut Cliente", "RUT Cliente"})
    nombre_col = _find_col(df, {"Nombre Cliente"})
    cuotas_pagadas_col = _find_col(df, {"Cuotas Pagadas"})
    cuotas_totales_col = _find_col(df, {"Cuotas Totales"})
    cuotas_mora_col = _find_col(df, {"Cuotas en mora"})
    intereses_mora_col = _find_col(df, {"Intereses Mora"})
    gastos_col = _find_col(df, {"Gastos Cobranza"})
    valor_cuota_col = _find_col(df, {"Valor Cuota"})
    monto_adeudado_col = _find_col(df, {"Monto Adeudado"})
    marca_col = _find_col(df, {"Marca Vehiculo", "Marca Vehiculo", "Marca Vehiculo", "Marca Vehículo"})
    modelo_col = _find_col(df, {"Modelo Vehiculo", "Modelo Vehículo"})
    email_col = _find_col(df, {"E-mail", "Email", "Correo"})
    fono_col = _find_col(df, {"Fono cliente", "Telefono cliente"})
    tramo_col = _find_col(df, {"Tramo de mora"})

    required = {
        "N° Contrato": contrato_col,
        "Rut Cliente": rut_col,
        "Nombre Cliente": nombre_col,
        "E-mail": email_col,
    }
    faltantes = [name for name, col in required.items() if col is None]
    if faltantes:
        raise ValueError("Faltan columnas requeridas en base Porsche: " + ", ".join(faltantes))

    out = pd.DataFrame({c: " " for c in COLUMNAS_CRM}, index=df.index)

    out["Nro_Documento"] = _as_clean_text(df[contrato_col])
    out["RUT - DV"] = _as_clean_text(df[rut_col])
    out["NOMBRE"] = _as_clean_text(df[nombre_col])
    out["AD1"] = _as_clean_text(df[cuotas_pagadas_col]) if cuotas_pagadas_col else " "
    out["NombreProducto"] = "AUTOMOTRIZ"
    out["AD2"] = _as_clean_text(df[cuotas_totales_col]) if cuotas_totales_col else " "
    out["AD3"] = _as_clean_text(df[cuotas_mora_col]) if cuotas_mora_col else " "
    out["AD5"] = _as_clean_text(df[intereses_mora_col]) if intereses_mora_col else " "
    out["AD6"] = _as_clean_text(df[gastos_col]) if gastos_col else " "
    out["AD7"] = _as_clean_text(df[valor_cuota_col]) if valor_cuota_col else " "
    out["AD11"] = _as_clean_text(df[monto_adeudado_col]) if monto_adeudado_col else " "
    out["AD8"] = _as_clean_text(df[marca_col]) if marca_col else " "
    out["AD9"] = _as_clean_text(df[modelo_col]) if modelo_col else " "
    out["EMAIL1"] = _as_clean_text(df[email_col])
    out["FONO1"] = _as_clean_text(df[fono_col]) if fono_col else " "
    out["TIPO_DEUDOR"] = _as_clean_text(df[tramo_col]) if tramo_col else " "

    out = out.fillna(" ")
    for col in out.columns:
        out[col] = out[col].astype(str).str.strip()
    out = out.replace("", " ")
    out = out.replace("-", " ")

    return out


def porsche_asignacion_filename() -> str:
    return f"ASIGNACION_PORSCHE_{datetime.now().strftime('%d-%m-%y')}.xlsx"
