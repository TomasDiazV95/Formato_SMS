
import pandas as pd
from datetime import datetime, date
from flask import Blueprint, request, send_file
import io
from typing import cast
from pandas._typing import WriteExcelBuffer

from services.ivr_service import CAMPO1_CHOICES, build_ivr_output, build_crm_output, sample_ivr_df, _pick_col
from services.constants import MANDANTE_CHOICES
from services.mandante_rules import apply_mandante_rules
from services import db_repos
from utils.excel_export import df_to_xlsx_bytesio, zip_named_dfs_bytes
from utils import api_error_response
from frontend import serve_react_app
import re

ivr_bp = Blueprint("ivr", __name__)


def _ivr_error(message: str, status: int = 400):
    return api_error_response(message, "ivr.ivr_page", status=status)


def _build_ivr_detalle(df: pd.DataFrame, campo1: str) -> list[dict[str, str | None]]:
    if df is None or df.empty:
        return []
    registros = df.iloc[1:] if len(df) > 1 else pd.DataFrame()
    detalles = []
    for _, row in registros.iterrows():
        detalles.append({
            "rut": str(row.get("ID_CLIENTE", "")).strip() or None,
            "telefono": str(row.get("TELEFONO", "")).strip() or None,
            "operacion": str(row.get("OPCIONAL", "")).strip() or None,
            "mensaje": str(row.get("MENSAJE", "")).strip() or None,
            "extra": {"campo1": campo1},
        })
    return detalles


def _slugify(value: str) -> str:
    value = (value or "").strip()
    normalized = re.sub(r"[^A-Za-z0-9-_]+", "_", value)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized or "usuario"


def _build_crm_zip_por_usuario(
    df: pd.DataFrame,
    *,
    fecha: date,
    hora_inicio: str,
    hora_fin: str,
    observacion: str,
    intervalo: int | None,
    fecha_label: str,
):
    base = df.copy()
    user_col = _pick_col(base, "USUARIO")
    if not user_col:
        raise ValueError("No se encontró una columna de usuario en el archivo. Usa encabezados como USUARIO, USUARIO_CRM o AGENTE.")

    usuarios = base[user_col].fillna("").astype(str).str.strip()
    base["__usuario_display"] = usuarios
    base["__usuario_key"] = usuarios.str.lower()
    valid = base[base["__usuario_key"].str.len() > 0].copy()
    if valid.empty:
        raise ValueError("La columna de usuarios está vacía. Verifica el archivo de origen.")

    named_outputs: list[tuple[str, pd.DataFrame]] = []
    for key in sorted(valid["__usuario_key"].unique()):
        mask = valid["__usuario_key"] == key
        group_df = valid.loc[mask].copy()
        display = group_df["__usuario_display"].iloc[0]
        subset = group_df.drop(columns=["__usuario_display", "__usuario_key"])
        salida = build_crm_output(
            df=subset,
            fecha=fecha,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            usuario_value=display,
            observacion_value=observacion,
            intervalo_segundos=intervalo,
        )
        filename = f"carga_IVR_CRM_{_slugify(display)}_{fecha_label}.xlsx"
        named_outputs.append((filename, salida))

    zip_buf = zip_named_dfs_bytes(named_outputs)
    zip_name = f"carga_IVR_CRM_{fecha_label}_por_usuario.zip"
    return zip_buf, zip_name

@ivr_bp.get("/ivr")
def ivr_page():
    return serve_react_app()

@ivr_bp.get("/ivr/sample")
def ivr_sample():
    df = sample_ivr_df()
    name = "ejemplo_IVR_ATHENAS.xlsx"
    buf = df_to_xlsx_bytesio(df, sheet_name="Hoja1")
    return send_file(
        buf,
        as_attachment=True,
        download_name=name,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

@ivr_bp.post("/ivr/process")
def ivr_process():
    file = request.files.get("file")
    campo1 = (request.form.get("campo1") or "").strip()
    mandante_nombre = (request.form.get("mandante") or "").strip()

    if not file or file.filename == "":
        return _ivr_error("Debes subir un archivo Excel.")
    if not campo1:
        return _ivr_error("Debes seleccionar un valor para CAMPO1.")
    if not mandante_nombre:
        return _ivr_error("Debes seleccionar un Mandante.")

    try:
        df = pd.read_excel(file, dtype=str)
        df = apply_mandante_rules(df, mandante_nombre)
        out = build_ivr_output(df, campo1_value=campo1)
        fecha = datetime.now().strftime("%d-%m")
        name = f"carga_IVR_ATHENAS_{fecha}.xlsx"
        buf = df_to_xlsx_bytesio(out, sheet_name="Hoja1")

        mandante = db_repos.fetch_mandante_by_nombre(mandante_nombre)
        if not mandante:
            return _ivr_error("Mandante no encontrado en catálogo.")

        proceso = db_repos.fetch_proceso_by_codigo("IVR_ATHENAS")
        if not proceso:
            return _ivr_error("No se logró identificar el proceso para registrar costos.", status=500)

        total_registros = max(len(out) - 1, 0)
        masividad_id = db_repos.log_masividad(
            mandante_id=mandante.id,
            proceso_id=proceso.id,
            total_registros=total_registros,
            costo_unitario=proceso.costo_unitario,
            usuario_app="ivr",
            archivo_generado=name,
            observacion="IVR Athenas",
            metadata={"campo1": campo1},
        )
        detalles = _build_ivr_detalle(out, campo1)
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
            download_name=name,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as e:
        return _ivr_error(str(e), status=500)

@ivr_bp.post("/ivr_crm/process")
def ivr_crm_process():
    file          = request.files.get("file")
    usuario       = (request.form.get("usuario") or "").strip()
    observacion   = (request.form.get("observacion") or "").strip()
    fecha_str     = (request.form.get("fecha") or "").strip()
    hora_inicio   = (request.form.get("hora_inicio") or "").strip()
    hora_fin      = (request.form.get("hora_fin") or "").strip()
    intervalo_str = (request.form.get("intervalo") or "").strip()
    auto_por_usuario = request.form.get("usar_usuarios_archivo") == "on"

    intervalo = None
    if intervalo_str:
        try:
            intervalo_val = int(intervalo_str)
            if intervalo_val > 0:
                intervalo = intervalo_val
            else:
                return _ivr_error("El intervalo debe ser un entero positivo en segundos.")
        except Exception:
            return _ivr_error("Intervalo inválido. Usa un entero en segundos.")

    if not file or file.filename == "":
        return _ivr_error("Debes subir un archivo Excel.")
    if not auto_por_usuario and not usuario:
        return _ivr_error("Debes seleccionar un USUARIO.")
    if not fecha_str or not hora_inicio or not hora_fin:
        return _ivr_error("Debes indicar FECHA DE GESTIÓN y el RANGO HORARIO.")

    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except ValueError:
        return _ivr_error("Formato de fecha inválido (usa AAAA-MM-DD).")

    try:
        df = pd.read_excel(file, dtype=str)
        fecha_salida = fecha.strftime("%d-%m")

        if auto_por_usuario:
            zip_buf, filename = _build_crm_zip_por_usuario(
                df=df,
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
                download_name=filename,
                mimetype="application/zip",
            )

        salida = build_crm_output(
            df=df,
            fecha=fecha,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            usuario_value=usuario,
            observacion_value=observacion,
            intervalo_segundos=intervalo
        )
        name = f"carga_IVR_CRM_{fecha_salida}.xlsx"
        buf = io.BytesIO()
        excel_buffer = cast(WriteExcelBuffer, buf)
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            salida.to_excel(writer, index=False, sheet_name="Hoja1")
        buf.seek(0)
        return send_file(
            buf,
            as_attachment=True,
            download_name=name,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except ValueError as e:
        return _ivr_error(str(e))
    except Exception as e:
        return _ivr_error(f"Ocurrió un error procesando el archivo: {e}", status=500)
