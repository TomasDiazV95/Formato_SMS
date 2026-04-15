# routes/sms.py
import pandas as pd
from datetime import datetime
from flask import Blueprint, request, send_file, abort
from typing import cast, Any
import re

from services.sms_service import (
    build_crm_output,
    build_athenas_output,
    build_axia_output,
    sample_athenas_df,
    sample_axia_df,
)
from services.constants import MANDANTE_CHOICES, COLUMN_MAP
from services.mandante_rules import apply_mandante_rules
from services import db_repos
from utils.excel_export import df_to_xlsx_bytesio, zip_named_dfs_bytes
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


def _build_sms_detalle(df: pd.DataFrame, mensaje: str, tipo_salida: str, mensajes_series: pd.Series | None = None) -> list[dict[str, str | None]]:
    if df is None or df.empty:
        return []
    rut_col = _find_column(df, "rut")
    telefono_col = _find_column(df, "telefono")
    op_col = _find_column(df, "operacion")
    mensajes = None
    if mensajes_series is not None:
        mensajes = (
            mensajes_series.reindex(df.index)
            .fillna("")
            .astype(str)
            .str.strip()
        )
        mensajes = mensajes.where(mensajes != "", mensaje)
    detalles = []
    for idx, row in df.iterrows():
        mensaje_row = mensajes.get(idx, mensaje) if mensajes is not None else mensaje
        detalles.append({
            "rut": str(row.get(rut_col, "")).strip() if rut_col else None,
            "telefono": str(row.get(telefono_col, "")).strip() if telefono_col else None,
            "operacion": str(row.get(op_col, "")).strip() if op_col else None,
            "mensaje": mensaje_row,
            "extra": {"salida": tipo_salida},
        })
    return detalles


USER_COLUMN_ALIASES = {
    "usuario",
    "usuario_crm",
    "multiplex",
    "agente",
    "ejecutivo",
    "usuario_gestion",
    "usuario crm",
    "usuario gestion",
    "user",
}


def _find_user_column(df: pd.DataFrame) -> str | None:
    normalized = {_normalize_key(col): col for col in df.columns}
    for alias in USER_COLUMN_ALIASES:
        key = _normalize_key(alias)
        if key in normalized:
            return normalized[key]
    return None


def _slugify(value: str) -> str:
    value = (value or "").strip()
    normalized = re.sub(r"[^A-Za-z0-9-_]+", "_", value)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized or "usuario"


def _build_crm_zip_por_usuario(
    df: pd.DataFrame,
    *,
    fecha,
    hora_inicio: str,
    hora_fin: str,
    observacion: str,
    intervalo: int | None,
    fecha_label: str,
):
    base = df.copy()
    user_col = _find_user_column(base)
    if not user_col:
        raise ValueError("No se encontró una columna de usuario en el archivo (ej. USUARIO_CRM, USUARIO, AGENTE).")

    usuarios = base[user_col].fillna("").astype(str).str.strip()
    base["__usuario_display"] = usuarios
    base["__usuario_key"] = usuarios.str.lower()
    valid = base[base["__usuario_key"].str.len() > 0].copy()
    if valid.empty:
        raise ValueError("La columna de usuarios está vacía. Verifica el archivo de origen.")

    named_outputs: list[tuple[str, pd.DataFrame]] = []
    for key, group in valid.groupby("__usuario_key"):
        if not isinstance(key, str) or not key.strip():
            continue
        group_df = cast(pd.DataFrame, group).copy()
        display = group_df["__usuario_display"].tolist()[0]
        subset = group_df.drop(columns=["__usuario_display", "__usuario_key"])
        salida = build_crm_output(
            subset,
            usuario=display,
            fecha=fecha,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            observacion=observacion,
            intervalo_segundos=intervalo,
        )
        filename = f"cargaCRM_SMS_{_slugify(display)}_{fecha_label}.xlsx"
        named_outputs.append((filename, salida))

    zip_buf = zip_named_dfs_bytes(named_outputs)
    zip_name = f"cargaCRM_SMS_{fecha_label}_por_usuario.zip"
    return zip_buf, zip_name

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

@sms_bp.post("/sms/crm")
def sms_crm_process():
    file = request.files.get("file")
    usuario = (request.form.get("usuario") or "").strip()
    observacion = (request.form.get("observacion") or "").strip()
    fecha_str = (request.form.get("fecha") or "").strip()
    hora_inicio = (request.form.get("hora_inicio") or "").strip()
    hora_fin = (request.form.get("hora_fin") or "").strip()
    intervalo_str = (request.form.get("intervalo") or "").strip()
    multi_usuarios = request.form.get("multiples_usuarios") == "on"
    if not file or file.filename == "":
        return _sms_error("Debes subir un archivo Excel.")
    if not multi_usuarios and not usuario:
        return _sms_error("Debes ingresar un Usuario.")
    if not fecha_str or not hora_inicio or not hora_fin:
        return _sms_error("Debes indicar FECHA DE GESTIÓN y el RANGO HORARIO.")

    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except ValueError:
        return _sms_error("Formato de fecha inválido (usa AAAA-MM-DD).")

    intervalo = None
    if intervalo_str:
        try:
            intervalo_val = int(intervalo_str)
            if intervalo_val <= 0:
                raise ValueError
            intervalo = intervalo_val
        except ValueError:
            return _sms_error("El intervalo debe ser un entero positivo en segundos.")

    try:
        df = pd.read_excel(file, dtype=str)
        fecha_salida = fecha.strftime("%d-%m")
        if multi_usuarios:
            zip_buf, zip_name = _build_crm_zip_por_usuario(
                df,
                fecha=fecha,
                hora_inicio=hora_inicio,
                hora_fin=hora_fin,
                observacion=observacion,
                intervalo=intervalo,
                fecha_label=fecha_salida,
            )
            return send_file(
                zip_buf,
                as_attachment=True,
                download_name=zip_name,
                mimetype="application/zip",
            )

        carga_crm = build_crm_output(
            df,
            usuario=usuario,
            fecha=fecha,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            observacion=observacion,
            intervalo_segundos=intervalo,
        )
        buf = df_to_xlsx_bytesio(carga_crm, sheet_name="cargaCRM")

        return send_file(
            buf,
            as_attachment=True,
            download_name=f"cargaCRM_SMS_{fecha_salida}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    except Exception as e:
        return _sms_error(f"Ocurrió un error procesando el archivo: {e}", status=500)


@sms_bp.post("/sms/athenas")
def sms_athenas_process():
    file = request.files.get("file")
    mensaje = (request.form.get("mensaje") or "").strip()
    tipo_salida = (request.form.get("tipo_salida") or "").strip().upper()
    mandante_nombre = (request.form.get("mandante") or "").strip()
    mensajes_personalizados = request.form.get("mensajes_personalizados") == "on"

    if not file or file.filename == "":
        return _sms_error("Debes subir un archivo Excel.")
    if not mensaje and not mensajes_personalizados:
        return _sms_error("Debes ingresar un Mensaje.")
    if not tipo_salida:
        return _sms_error("Debes escoger un formato de salida.")
    if not mandante_nombre:
        return _sms_error("Debes seleccionar un Mandante.")

    try:
        df = pd.read_excel(file, dtype=str)
        df = apply_mandante_rules(df, mandante_nombre)
        mensaje_series = None
        if mensajes_personalizados:
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

        mandante = db_repos.fetch_mandante_by_nombre(mandante_nombre)
        if not mandante:
            return _sms_error("Mandante no encontrado en catálogo.")

        if tipo_salida == "AXIA":
            carga = build_axia_output(df, mensaje=mensaje, mensajes_series=mensaje_series if mensajes_personalizados else None)
            proceso_codigo = "SMS_AXIA"
            buf = df_to_xlsx_bytesio(carga, sheet_name="Hoja1", header=False)
            nombre = f"carga_AXIA_SMS_{fecha_actual}.xlsx"
        else:
            carga = build_athenas_output(df, mensaje=mensaje, mensajes_series=mensaje_series if mensajes_personalizados else None)
            proceso_codigo = "SMS_ATHENAS"
            buf = df_to_xlsx_bytesio(carga, sheet_name="cargaAthenas")
            nombre = f"cargaAthenas_SMS_{fecha_actual}.xlsx"

        proceso = db_repos.fetch_proceso_by_codigo(proceso_codigo)
        if not proceso:
            return _sms_error("No se logró identificar el proceso para registrar costos.", status=500)

        total_registros = max(len(carga) - 1, 0)
        metadata: dict[str, Any] = {"formato": tipo_salida}
        if mensajes_personalizados:
            metadata["mensajes_personalizados"] = True
        masividad_id = db_repos.log_masividad(
            mandante_id=mandante.id,
            proceso_id=proceso.id,
            total_registros=total_registros,
            costo_unitario=proceso.costo_unitario,
            usuario_app="sms",
            archivo_generado=nombre,
            observacion=mensaje,
            metadata=metadata,
        )

        detalles = _build_sms_detalle(
            df,
            mensaje,
            tipo_salida,
            mensaje_series if mensajes_personalizados else None,
        )
        if masividad_id and detalles:
            db_repos.bulk_insert_masividad_detalle(
                masividad_log_id=masividad_id,
                proceso_codigo=proceso.codigo,
                mandante_nombre=mandante.nombre,
                registros=detalles,
            )

        return send_file(
            buf,
            as_attachment=True,
            download_name=nombre,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    except Exception as e:
        return _sms_error(f"Ocurrió un error procesando el archivo: {e}", status=500)
