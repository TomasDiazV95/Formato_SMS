# routes/sms.py
import pandas as pd
from datetime import datetime
from flask import Blueprint, request, send_file, abort

from services.sms_service import (
    build_athenas_output,
    build_axia_output,
    sample_athenas_df,
    sample_axia_df,
)
from services.constants import COLUMN_MAP
from services.mandante_rules import apply_mandante_rules
from services.sms_itau_vencida import build_itau_carterizado_messages, filename_token, prepend_itau_seed_rows
from utils.excel_export import df_to_xlsx_bytesio
from utils import api_error_response
from frontend import serve_react_app

sms_bp = Blueprint("sms", __name__)


def _sms_error(message: str, status: int = 400):
    return api_error_response(message, "sms.sms_page", status=status)


def _normalize_key(value: str) -> str:
    return (
        (value or "")
        .strip()
        .lower()
        .replace(" ", "")
        .replace("_", "")
        .replace("-", "")
    )


def _find_column(df: pd.DataFrame, logical: str) -> str | None:
    logical = (logical or "").lower()
    normalized = {_normalize_key(col): col for col in df.columns}
    candidates = {logical}
    if logical in COLUMN_MAP:
        candidates |= {_normalize_key(name) for name in COLUMN_MAP[logical]}
    for candidate in candidates:
        key = _normalize_key(candidate)
        if key in normalized:
            return normalized[key]
    return None


@sms_bp.get("/")
def main():
    return serve_react_app()


@sms_bp.get("/procesos")
def procesos_menu():
    return serve_react_app()


@sms_bp.get("/cargas")
def cargas_menu():
    return serve_react_app()

@sms_bp.get("/sms")
def sms_page():
    return serve_react_app()

@sms_bp.get("/sms/sample/<tipo>")
def sms_sample(tipo: str):
    tipo = (tipo or "").upper()
    if tipo == "ATHENAS":
        df = sample_athenas_df()
        sheet = "cargaAthenas"
        name = "ejemplo_SMS_ATHENAS.xlsx"
        header = True
    elif tipo == "AXIA":
        df = sample_axia_df()
        sheet = "Hoja1"
        name = "ejemplo_SMS_AXIA.xlsx"
        header = False
    else:
        abort(404)

    buf = df_to_xlsx_bytesio(df, sheet_name=sheet, header=header)
    return send_file(
        buf,
        as_attachment=True,
        download_name=name,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

@sms_bp.post("/sms/athenas")
def sms_athenas_process():
    file = request.files.get("file")
    mensaje = (request.form.get("mensaje") or "").strip()
    tipo_salida = (request.form.get("tipo_salida") or "").strip().upper()
    mandante_nombre = (request.form.get("mandante") or "").strip()
    mensajes_personalizados = request.form.get("mensajes_personalizados") == "on"
    modo_carterizado_itau = request.form.get("modo_carterizado_itau") == "on"

    if not file or file.filename == "":
        return _sms_error("Debes subir un archivo Excel.")
    if not mensaje and not mensajes_personalizados and not modo_carterizado_itau:
        return _sms_error("Debes ingresar un Mensaje.")
    if not tipo_salida:
        return _sms_error("Debes escoger un formato de salida.")
    if not mandante_nombre:
        return _sms_error("Debes seleccionar un Mandante.")
    if modo_carterizado_itau and mandante_nombre.lower() != "itau vencida":
        return _sms_error("El modo carterizado Itaú solo está habilitado para mandante Itau Vencida.")

    try:
        df = pd.read_excel(file, dtype=str)
        df = apply_mandante_rules(df, mandante_nombre)
        mensaje_series = None
        if modo_carterizado_itau:
            mensaje_series = build_itau_carterizado_messages(df, mandante_nombre)
            valid_mask = mensaje_series.fillna("").astype(str).str.strip() != ""
            if not valid_mask.any():
                return _sms_error("No hay filas SMS válidas para generar salida Itaú (revisa MASIVIDAD).")
            df = df.loc[valid_mask].copy()
            mensaje_series = mensaje_series.loc[valid_mask].copy()
            mensaje = "SMS ITAU CARTERIZADO"
            mensajes_personalizados = True
        elif mensajes_personalizados:
            mensaje_col = _find_column(df, "mensaje")
            if not mensaje_col:
                return _sms_error("Activaste múltiples mensajes pero no existe una columna 'Mensaje' en el archivo.")
            mensaje_series = df[mensaje_col].fillna("").astype(str).str.strip()
            if mensaje_series.eq("").all() and not mensaje:
                return _sms_error("La columna 'Mensaje' está vacía y no ingresaste un mensaje base.")
            if not mensaje:
                primera = mensaje_series[mensaje_series != ""]
                if primera.empty:
                    return _sms_error("No hay mensajes válidos en la columna 'Mensaje'.")
                mensaje = primera.iloc[0]
            mensaje_series = mensaje_series.where(mensaje_series != "", mensaje)

        fecha_actual = datetime.now().strftime("%d-%m")
        mandante_token = filename_token(mandante_nombre)

        if tipo_salida == "AXIA":
            carga = build_axia_output(df, mensaje=mensaje, mensajes_series=mensaje_series if mensajes_personalizados else None)
            if modo_carterizado_itau and mensaje_series is not None:
                carga, _ = prepend_itau_seed_rows(carga, tipo_salida, mensaje_series)
            buf = df_to_xlsx_bytesio(carga, sheet_name="Hoja1", header=False)
            nombre = f"carga_AXIA_SMS_{mandante_token}_{fecha_actual}.xlsx"
        else:
            carga = build_athenas_output(df, mensaje=mensaje, mensajes_series=mensaje_series if mensajes_personalizados else None)
            if modo_carterizado_itau and mensaje_series is not None:
                carga, _ = prepend_itau_seed_rows(carga, tipo_salida, mensaje_series)
            buf = df_to_xlsx_bytesio(carga, sheet_name="cargaAthenas")
            nombre = f"cargaAthenas_SMS_{mandante_token}_{fecha_actual}.xlsx"

        return send_file(
            buf,
            as_attachment=True,
            download_name=nombre,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    except Exception as e:
        return _sms_error(f"Ocurrió un error procesando el archivo: {e}", status=500)
