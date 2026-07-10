# routes/sms.py
import io
import pandas as pd
import zipfile
from datetime import date, datetime
from flask import Blueprint, request, send_file, abort

from services.sms_service import (
    build_athenas_output,
    build_axia_output,
    build_crm_output as build_sms_crm_output,
    sample_athenas_df,
    sample_axia_df,
)
from services.constants import COLUMN_MAP
from services.mandante_rules import apply_mandante_rules
from services.sms_itau_vencida import build_itau_carterizado_messages, filename_token, prepend_itau_seed_rows
from utils.excel_export import df_to_xlsx_bytes, df_to_xlsx_bytesio
from utils import api_error_response
from frontend import serve_react_app

sms_bp = Blueprint("sms", __name__)

SMS_CRM_RULES = {
    "itau vencida": ("VDAD", "ENVIO SIN RESPUESTA"),
    "itau castigo": ("VDAD", "ENVIO SIN RESPUESTA"),
    "banco internacional": ("VDAD", ""),
    "santander hipotecario": ("VDAD", ""),
    "santander consumer terreno": ("jriveros", ""),
    "santander consumer telefonía": ("jriveros", ""),
    "santander consumer telefonia": ("jriveros", ""),
    "santander consumer judicial": ("jriveros", ""),
    "general motors": ("jriveros", "SMS"),
    "la araucana": ("VDAD", ""),
    "tanner": ("VDAD", ""),
}


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


def _crm_rule_for_sms(mandante: str) -> tuple[str, str] | None:
    return SMS_CRM_RULES.get((mandante or "").strip().lower())


def _zip_sms_outputs(files: list[tuple[str, bytes]]) -> io.BytesIO:
    zip_bio = io.BytesIO()
    with zipfile.ZipFile(zip_bio, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for filename, payload in files:
            zf.writestr(filename, payload)
    zip_bio.seek(0)
    return zip_bio


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
    include_crm = request.form.get("include_crm") == "on"
    crm_fecha_raw = (request.form.get("crm_fecha") or "").strip()
    crm_hora_inicio = (request.form.get("crm_hora_inicio") or "").strip()
    crm_hora_fin = (request.form.get("crm_hora_fin") or "").strip()

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
    if include_crm:
        if mandante_nombre.strip().lower() == "caja18":
            return _sms_error("CAJA18 no genera CRM desde el modulo SMS.")
        if not crm_fecha_raw or not crm_hora_inicio or not crm_hora_fin:
            return _sms_error("Debes indicar fecha, hora inicio y hora fin para generar CRM.")
        crm_rule = _crm_rule_for_sms(mandante_nombre)
        if not crm_rule:
            return _sms_error("No hay regla CRM configurada para este mandante en SMS.")
        try:
            crm_fecha = date.fromisoformat(crm_fecha_raw)
        except ValueError:
            return _sms_error("La fecha de gestion CRM no es valida.")
    else:
        crm_rule = None
        crm_fecha = None

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
            nombre = f"carga_AXIA_SMS_{mandante_token}_{fecha_actual}.xlsx"
            main_sheet = "Hoja1"
            main_header = False
        else:
            carga = build_athenas_output(df, mensaje=mensaje, mensajes_series=mensaje_series if mensajes_personalizados else None)
            if modo_carterizado_itau and mensaje_series is not None:
                carga, _ = prepend_itau_seed_rows(carga, tipo_salida, mensaje_series)
            nombre = f"cargaAthenas_SMS_{mandante_token}_{fecha_actual}.xlsx"
            main_sheet = "cargaAthenas"
            main_header = True

        files: list[tuple[str, bytes]] = [(nombre, df_to_xlsx_bytes(carga, sheet_name=main_sheet, header=main_header))]
        if tipo_salida == "AXIA":
            csv_name = nombre.replace(".xlsx", ".csv")
            files.append((csv_name, carga.to_csv(index=False, header=False, sep=";", encoding="utf-8-sig").encode("utf-8-sig")))

        if include_crm and crm_rule and crm_fecha:
            usuario, observacion = crm_rule
            crm_df = build_sms_crm_output(
                df,
                usuario=usuario,
                fecha=crm_fecha,
                hora_inicio=crm_hora_inicio,
                hora_fin=crm_hora_fin,
                observacion=observacion,
            )
            crm_base = f"carga_CRM_SMS_{mandante_token}_{fecha_actual}"
            files.append((f"{crm_base}.xlsx", df_to_xlsx_bytes(crm_df, sheet_name="cargaCRM")))
            files.append((f"{crm_base}.csv", crm_df.to_csv(index=False, sep=";", encoding="utf-8-sig").encode("utf-8-sig")))

        if len(files) > 1:
            zip_name = f"SMS_{tipo_salida}_{mandante_token}_{fecha_actual}.zip"
            return send_file(
                _zip_sms_outputs(files),
                as_attachment=True,
                download_name=zip_name,
                mimetype="application/zip",
            )

        buf = df_to_xlsx_bytesio(carga, sheet_name=main_sheet, header=main_header)

        return send_file(
            buf,
            as_attachment=True,
            download_name=nombre,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    except Exception as e:
        return _sms_error(f"Ocurrió un error procesando el archivo: {e}", status=500)
