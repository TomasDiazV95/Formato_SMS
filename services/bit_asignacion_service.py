from __future__ import annotations

from datetime import datetime
import io
import re
import unicodedata

import chardet
import pandas as pd


CRM_COLUMNS = [
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


ADICIONAL_COLUMNS = [
    "rut",
    "PORC_DCTO_PUT",
    "PORC_DCTO_AP",
    "PORC_ABONO_EXIGIDO_RENE",
    "PORC_ABONO_EXIGIDO_AP",
    "FECHA_TOPE_OFERTA",
    "Campana",
    "DSCTO_GTOS_COBRANZAS",
    "MTO_TRANSFERIR",
]


def _normalize_key(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip().replace(" ", "").replace("_", "")
    return re.sub(r"[^a-z0-9]", "", text)


def _detect_encoding(file_bytes: bytes) -> str:
    detected = chardet.detect(file_bytes)
    return str(detected.get("encoding") or "utf-8")


def _read_bit_csv(file_storage) -> pd.DataFrame:
    file_bytes = file_storage.read()
    if not file_bytes:
        raise ValueError("El archivo CSV está vacío.")

    encoding = _detect_encoding(file_bytes)
    stream = io.BytesIO(file_bytes)
    try:
        df = pd.read_csv(
            stream,
            encoding=encoding,
            sep=";",
            dtype=str,
            keep_default_na=False,
            na_filter=False,
            on_bad_lines="skip",
        )
    except UnicodeDecodeError:
        stream.seek(0)
        df = pd.read_csv(
            stream,
            encoding="latin-1",
            sep=";",
            dtype=str,
            keep_default_na=False,
            na_filter=False,
            on_bad_lines="skip",
        )

    clean_cols = [str(c).replace("\ufeff", "").strip() for c in df.columns]
    df.columns = clean_cols
    return df


def _find_col(df: pd.DataFrame, aliases: set[str]) -> str | None:
    idx = {_normalize_key(c): c for c in df.columns}
    for alias in aliases:
        key = _normalize_key(alias)
        if key in idx:
            return idx[key]
    return None


def _text_series(df: pd.DataFrame, col: str | None) -> pd.Series:
    if not col or col not in df.columns:
        return pd.Series([" "] * len(df), index=df.index, dtype=object)
    s = df[col].astype(str).str.strip()
    s = s.str.replace(r"\.0$", "", regex=True)
    s = s.replace(r"^\s*$", " ", regex=True)
    return s


def _text_series_exact(df: pd.DataFrame, col: str | None) -> pd.Series:
    """Preserva el contenido textual original (solo trim de bordes)."""
    if not col or col not in df.columns:
        return pd.Series([" "] * len(df), index=df.index, dtype=object)
    s = df[col].astype(str).str.strip()
    s = s.replace(r"^\s*$", " ", regex=True)
    return s


def _date_series(df: pd.DataFrame, col: str | None) -> pd.Series:
    if not col or col not in df.columns:
        return pd.Series([" "] * len(df), index=df.index, dtype=object)
    raw = _text_series(df, col)
    parsed_dmy = pd.to_datetime(raw, format="%d-%m-%Y", errors="coerce")
    parsed_ymd = pd.to_datetime(raw, format="%Y-%m-%d", errors="coerce")
    parsed = parsed_dmy.fillna(parsed_ymd)
    out = parsed.dt.strftime("%d-%m-%Y")
    return out.fillna(" ")


def _clean_dataframe_text(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        s = out[col]
        mask = s.isna()
        out.loc[~mask, col] = s.loc[~mask].astype(str).str.strip()
        out.loc[mask, col] = " "
        out[col] = out[col].replace(r"^\s*$", " ", regex=True)
    out = out.replace(["nan", "NaN", "NaT", "None", "<NA>"], " ")
    out = out.replace("", " ")
    out = out.replace("-", " ")
    return out


def build_bit_outputs(file_storage, campana_nueva: bool) -> list[tuple[str, pd.DataFrame]]:
    df = _read_bit_csv(file_storage)

    nro_operacion = _find_col(df, {"NRO_OPERACION"})
    rut = _find_col(df, {"RUT"})
    dv = _find_col(df, {"DV"})
    nombre = _find_col(df, {"NOMBRE_CLIENTE"})
    fecha_curse = _find_col(df, {"FECHA_CURSE"})
    grupo_producto = _find_col(df, {"GRUPO_PRODUCTO"})
    cuotas_morosas = _find_col(df, {"CUOTAS_MOROSAS"})
    nro_total_cuotas = _find_col(df, {"NRO_TOTAL_CUOTAS"})
    fe_vto = _find_col(df, {"FE_VTO_CUOTA"})
    mto_cuota = _find_col(df, {"MTO_CUOTA"})
    nombre_eje = _find_col(df, {"NOMBRE_EJE_COMER"})
    fec_mora = _find_col(df, {"FEC_MORA"})
    deuda_total = _find_col(df, {"DEUDA_TOTAL"})
    correo_eje = _find_col(df, {"CORREO_EJE_COMER"})
    fono_eje = _find_col(df, {"TELEFONO_EJE_NORM"})
    campana = _find_col(df, {"CAMPANA"})
    monto_mora_total = _find_col(df, {"MONTO_MORA_TOTAL"})
    dir_part = _find_col(df, {"DIR_PARTICULAR"})
    comuna = _find_col(df, {"COMUNA"})
    ciudad = _find_col(df, {"CIUDAD"})
    dir_com = _find_col(df, {"DIR_COMERCIAL"})
    comuna_com = _find_col(df, {"COMUNA_COMERCIAL"})
    ciudad_com = _find_col(df, {"CIUDAD_COMERCIAL"})
    mail = _find_col(df, {"MAIL"})
    fono1 = _find_col(df, {"TELEFONO1"})
    fono2 = _find_col(df, {"TELEFONO2"})
    fono3 = _find_col(df, {"TELEFONO3"})
    cartera = _find_col(df, {"CARTERA"})
    producto = _find_col(df, {"PRODUCTO"})

    if not all([nro_operacion, rut, dv, nombre, mail]):
        raise ValueError("El CSV BIT no contiene las columnas mínimas requeridas (NRO_OPERACION, RUT, DV, NOMBRE_CLIENTE, MAIL).")

    crm = pd.DataFrame({c: " " for c in CRM_COLUMNS}, index=df.index)
    # Operacion debe conservarse textual exactamente como viene en origen.
    crm["Nro_Documento"] = _text_series_exact(df, nro_operacion)
    crm["RUT - DV"] = _text_series(df, rut).str.strip().str.cat(_text_series(df, dv).str.strip(), sep="-", na_rep=" ")
    crm["NOMBRE"] = _text_series(df, nombre)
    crm["AD1"] = _date_series(df, fecha_curse)
    crm["NombreProducto"] = _text_series(df, grupo_producto)
    crm["AD2"] = _text_series(df, cuotas_morosas)
    crm["AD3"] = _text_series(df, nro_total_cuotas)
    crm["AD4"] = _date_series(df, fe_vto)
    crm["AD5"] = _text_series(df, mto_cuota)
    crm["AD6"] = _text_series(df, nombre_eje)
    crm["AD7"] = _date_series(df, fec_mora)
    crm["DEUDA TOTAL"] = _text_series(df, deuda_total)
    crm["AD11"] = _text_series(df, correo_eje)
    crm["AD8"] = _text_series(df, fono_eje)
    crm["AD9"] = _text_series(df, campana)
    crm["AD10"] = _text_series(df, monto_mora_total)
    crm["DIRECCION"] = _text_series(df, dir_part)
    crm["COMUNA"] = _text_series(df, comuna)
    crm["CIUDAD"] = _text_series(df, ciudad)
    crm["DIRECCION_COMERCIAL"] = _text_series(df, dir_com)
    crm["COMUNA_COMERCIAL"] = _text_series(df, comuna_com)
    crm["CIUDAD_COMERCIAL"] = _text_series(df, ciudad_com)
    crm["EMAIL1"] = _text_series(df, mail)
    crm["FONO1"] = _text_series(df, fono1)
    crm["FONO2"] = _text_series(df, fono2)
    crm["FONO3"] = _text_series(df, fono3)
    crm["TIPO_DEUDOR"] = _text_series(df, cartera)
    crm["TIPO_PRODUCTO 1"] = _text_series(df, producto)
    crm["AD14"] = "NEW" if campana_nueva else " "
    crm = _clean_dataframe_text(crm)

    adicional = pd.DataFrame({c: " " for c in ADICIONAL_COLUMNS}, index=df.index)
    adicional["rut"] = _text_series(df, rut).str.strip().str.cat(_text_series(df, dv).str.strip(), sep="-", na_rep=" ")
    adicional["PORC_DCTO_PUT"] = _text_series(df, _find_col(df, {"PORC_DCTO_PUT"}))
    adicional["PORC_DCTO_AP"] = _text_series(df, _find_col(df, {"PORC_DCTO_AP"}))
    adicional["PORC_ABONO_EXIGIDO_RENE"] = _text_series(df, _find_col(df, {"PORC_ABONO_EXIGIDO_RENE"}))
    adicional["PORC_ABONO_EXIGIDO_AP"] = _text_series(df, _find_col(df, {"PORC_ABONO_EXIGIDO_AP"}))
    adicional["FECHA_TOPE_OFERTA"] = _text_series(df, _find_col(df, {"FECHA_TOPE_OFERTA"}))
    adicional["Campana"] = _text_series(df, campana)
    adicional["DSCTO_GTOS_COBRANZAS"] = _text_series(df, _find_col(df, {"DSCTO_GTOS_COBRANZAS"}))
    adicional["MTO_TRANSFERIR"] = _text_series(df, _find_col(df, {"MTO_TRANSFERIR"}))
    adicional = _clean_dataframe_text(adicional)

    now = datetime.now()
    crm_name = f"CARGA BIT {now.strftime('%d-%m-%Y')}.xlsx"
    adi_name = f"Info_adi_{now.strftime('%d-%m-%y')}.xlsx"
    return [(crm_name, crm), (adi_name, adicional)]
