from __future__ import annotations

import io
import re
import uuid
from datetime import datetime, timedelta

import pandas as pd
from flask import Blueprint, request, send_file

from frontend import serve_react_app
from services.mail_service import build_mail_crm_output
from services.sms_service import build_crm_output as build_sms_crm_output
from utils import api_error_response
from utils.excel_export import df_to_xlsx_bytesio, zip_named_dfs_bytes


crm_bp = Blueprint("crm", __name__)

CRM_SESSIONS: dict[str, dict[str, object]] = {}
CRM_SESSION_TTL_MINUTES = 90


def _crm_error(message: str, status: int = 400):
    return api_error_response(message, "crm.crm_page", status=status)


def _cleanup_sessions() -> None:
    now = datetime.now()
    expired: list[str] = []
    for token, payload in CRM_SESSIONS.items():
        created = payload.get("created_at")
        if not isinstance(created, datetime):
            expired.append(token)
            continue
        if now - created > timedelta(minutes=CRM_SESSION_TTL_MINUTES):
            expired.append(token)
    for token in expired:
        CRM_SESSIONS.pop(token, None)


def _slugify(value: str) -> str:
    value = (value or "").strip()
    normalized = re.sub(r"[^A-Za-z0-9-_]+", "_", value)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized or "usuario"


def _filename_token(value: str) -> str:
    value = (value or "").strip()
    normalized = re.sub(r"[^A-Za-z0-9-_]+", "_", value)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized or "MANDANTE"


def _normalize_key(value: str) -> str:
    return (
        (value or "")
        .strip()
        .lower()
        .replace(" ", "")
        .replace("_", "")
        .replace("-", "")
    )


def _find_user_column(df: pd.DataFrame) -> str | None:
    aliases = {
        "usuario",
        "usuario_crm",
        "agente",
        "ejecutivo",
        "usuario_gestion",
        "usuario crm",
        "usuario gestion",
        "user",
    }
    normalized = {_normalize_key(col): col for col in df.columns}
    for alias in aliases:
        key = _normalize_key(alias)
        if key in normalized:
            return normalized[key]
    return None


def _read_any_dataframe(file_bytes: bytes, filename: str | None = None) -> pd.DataFrame:
    name = (filename or "").lower()
    if name.endswith(".csv"):
        try:
            return pd.read_csv(io.BytesIO(file_bytes), sep=";", dtype=str, keep_default_na=False, na_filter=False)
        except Exception:
            return pd.read_csv(io.BytesIO(file_bytes), dtype=str, keep_default_na=False, na_filter=False)
    try:
        return pd.read_excel(io.BytesIO(file_bytes), dtype=str)
    except Exception:
        return pd.read_csv(io.BytesIO(file_bytes), sep=";", dtype=str, keep_default_na=False, na_filter=False)


@crm_bp.get("/procesos/crm")
def crm_page():
    return serve_react_app()


@crm_bp.post("/crm/session")
def crm_session_create():
    _cleanup_sessions()
    file = request.files.get("file")
    mode = (request.form.get("mode") or "").strip().lower()
    source = (request.form.get("source") or "").strip()
    if not file or file.filename == "":
        return _crm_error("Debes adjuntar un archivo para crear la sesión CRM.")
    if mode not in {"sms_ivr", "mail"}:
        return _crm_error("Modo de CRM inválido. Usa sms_ivr o mail.")

    file_bytes = file.read()
    if not file_bytes:
        return _crm_error("El archivo enviado está vacío.")

    token = uuid.uuid4().hex
    CRM_SESSIONS[token] = {
        "mode": mode,
        "source": source,
        "filename": file.filename,
        "file_bytes": file_bytes,
        "created_at": datetime.now(),
    }

    return {
        "ok": True,
        "token": token,
        "mode": mode,
        "source": source,
        "filename": file.filename,
        "expires_in_minutes": CRM_SESSION_TTL_MINUTES,
    }


def _build_sms_ivr_multi_zip(
    df: pd.DataFrame,
    *,
    fecha,
    hora_inicio: str,
    hora_fin: str,
    observacion: str,
    intervalo: int | None,
    fecha_label: str,
    mandante_token: str,
) -> tuple[io.BytesIO, str]:
    user_col = _find_user_column(df)
    if not user_col:
        raise ValueError("No se encontró una columna de usuario en el archivo (USUARIO_CRM/USUARIO/AGENTE).")

    base = df.copy()
    usuarios = base[user_col].fillna("").astype(str).str.strip()
    base["__usuario_display"] = usuarios
    base["__usuario_key"] = usuarios.str.lower()
    valid = base[base["__usuario_key"].str.len() > 0].copy()
    if valid.empty:
        raise ValueError("La columna de usuarios está vacía. Verifica el archivo de origen.")

    named_outputs: list[tuple[str, pd.DataFrame]] = []
    user_keys = pd.unique(valid["__usuario_key"]).tolist()
    for key in sorted(str(item) for item in user_keys):
        group = valid.loc[valid["__usuario_key"] == key].copy()
        display = group["__usuario_display"].iloc[0]
        subset = group.drop(columns=["__usuario_display", "__usuario_key"])
        salida = build_sms_crm_output(
            subset,
            usuario=display,
            fecha=fecha,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            observacion=observacion,
            intervalo_segundos=intervalo,
        )
        filename = f"cargaCRM_{mandante_token}_{_slugify(display)}_{fecha_label}.xlsx"
        named_outputs.append((filename, salida))

    return zip_named_dfs_bytes(named_outputs), f"cargaCRM_{mandante_token}_{fecha_label}_por_usuario.zip"


@crm_bp.post("/crm/carga")
def crm_carga():
    _cleanup_sessions()

    mode = (request.form.get("mode") or "").strip().lower()
    token = (request.form.get("token") or "").strip()
    file = request.files.get("file")

    usuario = (request.form.get("usuario") or "").strip()
    observacion = (request.form.get("observacion") or "").strip()
    fecha_str = (request.form.get("fecha") or "").strip()
    hora_inicio = (request.form.get("hora_inicio") or "").strip()
    hora_fin = (request.form.get("hora_fin") or "").strip()
    intervalo_str = (request.form.get("intervalo") or "").strip()
    mandante_salida = (request.form.get("mandante_salida") or "").strip()
    multi_usuarios = request.form.get("multi_usuarios") == "on"

    if mode not in {"sms_ivr", "mail"}:
        return _crm_error("Modo de CRM inválido. Usa sms_ivr o mail.")
    if not mandante_salida:
        return _crm_error("Debes seleccionar mandante para el nombre de salida.")
    if not fecha_str or not hora_inicio or not hora_fin:
        return _crm_error("Debes indicar FECHA DE GESTIÓN y el RANGO HORARIO.")
    if mode == "sms_ivr" and not multi_usuarios and not usuario:
        return _crm_error("Debes indicar usuario para CRM SMS/IVR.")
    if mode == "mail" and not usuario:
        return _crm_error("Debes indicar usuario para CRM Mail.")

    intervalo = None
    if intervalo_str:
        try:
            parsed = int(intervalo_str)
            if parsed <= 0:
                raise ValueError
            intervalo = parsed
        except ValueError:
            return _crm_error("El intervalo debe ser un entero positivo en segundos.")

    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except ValueError:
        return _crm_error("Formato de fecha inválido (usa AAAA-MM-DD).")

    payload = CRM_SESSIONS.get(token) if token else None
    if token and not payload:
        return _crm_error("La sesión CRM expiró o no existe. Vuelve a generar desde el proceso.", status=404)

    if payload:
        source_mode = str(payload.get("mode") or "")
        if source_mode and source_mode != mode:
            return _crm_error("El modo seleccionado no coincide con la sesión precargada.")
        file_bytes = payload.get("file_bytes")
        filename = str(payload.get("filename") or "")
        if not isinstance(file_bytes, (bytes, bytearray)):
            return _crm_error("La sesión CRM no contiene un archivo válido.", status=500)
        df = _read_any_dataframe(bytes(file_bytes), filename)
    else:
        if not file or file.filename == "":
            return _crm_error("Debes subir archivo manual o usar sesión precargada.")
        try:
            df = pd.read_excel(file, dtype=str)
        except Exception:
            file.stream.seek(0)
            df = pd.read_csv(file.stream, sep=";", dtype=str, keep_default_na=False, na_filter=False)

    try:
        fecha_salida = fecha.strftime("%d-%m")
        mandante_token = _filename_token(mandante_salida)
        if mode == "mail":
            salida = build_mail_crm_output(
                df=df,
                fecha=fecha,
                hora_inicio=hora_inicio,
                hora_fin=hora_fin,
                usuario_value=usuario,
                observacion_value=observacion,
                intervalo_segundos=intervalo,
            )
            buf = df_to_xlsx_bytesio(salida, sheet_name="cargaMailCRM")
            nombre = f"carga_MAIL_CRM_{mandante_token}_{fecha_salida}.xlsx"
            return send_file(
                buf,
                as_attachment=True,
                download_name=nombre,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        if multi_usuarios:
            zip_buf, zip_name = _build_sms_ivr_multi_zip(
                df,
                fecha=fecha,
                hora_inicio=hora_inicio,
                hora_fin=hora_fin,
                observacion=observacion,
                intervalo=intervalo,
                fecha_label=fecha_salida,
                mandante_token=mandante_token,
            )
            return send_file(zip_buf, as_attachment=True, download_name=zip_name, mimetype="application/zip")

        salida = build_sms_crm_output(
            df,
            usuario=usuario,
            fecha=fecha,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            observacion=observacion,
            intervalo_segundos=intervalo,
        )
        buf = df_to_xlsx_bytesio(salida, sheet_name="cargaCRM")
        nombre = f"carga_CRM_SMS_IVR_{mandante_token}_{fecha_salida}.xlsx"
        return send_file(
            buf,
            as_attachment=True,
            download_name=nombre,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except ValueError as exc:
        return _crm_error(str(exc))
    except Exception as exc:
        return _crm_error(f"Error procesando CRM: {exc}", status=500)
