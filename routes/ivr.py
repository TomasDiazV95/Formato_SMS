
import pandas as pd
from datetime import datetime
from flask import Blueprint, jsonify, request, send_file
import re
import unicodedata

from services.ivr_service import build_ivr_output, get_campo1_choices, sample_ivr_df
from services.constants import MANDANTE_CHOICES
from services.mandante_rules import apply_mandante_rules
from services import db_repos
from utils.excel_export import df_to_xlsx_bytesio
from utils import api_error_response
from frontend import serve_react_app

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


def _filename_token(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")
    return text or "MANDANTE"

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


@ivr_bp.get("/ivr/campo1-options")
def ivr_campo1_options():
    options = [{"label": label, "value": value} for label, value in get_campo1_choices()]
    return jsonify({"items": options})

@ivr_bp.post("/ivr/process")
def ivr_process():
    file = request.files.get("file")
    campo1 = (request.form.get("campo1") or "").strip()
    mandante_nombre = (request.form.get("mandante") or "").strip()

    if not file or file.filename == "":
        return _ivr_error("Debes subir un archivo Excel.")
    if not campo1:
        return _ivr_error("Debes seleccionar un valor para CAMPO1.")

    allowed_values = {value for _, value in get_campo1_choices()}
    if campo1 not in allowed_values:
        return _ivr_error("El CAMPO1 seleccionado no esta habilitado en catalogo.")

    if not mandante_nombre:
        return _ivr_error("Debes seleccionar un Mandante.")

    try:
        df = pd.read_excel(file, dtype=str)
        df = apply_mandante_rules(df, mandante_nombre)
        out = build_ivr_output(df, campo1_value=campo1)
        fecha = datetime.now().strftime("%d-%m")
        buf = df_to_xlsx_bytesio(out, sheet_name="Hoja1")

        mandante = db_repos.fetch_mandante_by_nombre(mandante_nombre)
        if not mandante:
            return _ivr_error("Mandante no encontrado en catálogo.")

        mandante_token = _filename_token(mandante.nombre)
        name = f"carga_IVR_ATHENAS_{mandante_token}_{fecha}.xlsx"

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

