
import pandas as pd
from datetime import datetime
from flask import Blueprint, jsonify, request, send_file
import re
import unicodedata

from services.ivr_service import build_ivr_output, get_campo1_choices, sample_ivr_df
from services.mandante_rules import apply_mandante_rules
from utils.excel_export import df_to_xlsx_bytesio
from utils import api_error_response
from frontend import serve_react_app

ivr_bp = Blueprint("ivr", __name__)


def _ivr_error(message: str, status: int = 400):
    return api_error_response(message, "ivr.ivr_page", status=status)


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

        mandante_token = _filename_token(mandante_nombre)
        name = f"carga_IVR_ATHENAS_{mandante_token}_{fecha}.xlsx"

        return send_file(
            buf,
            as_attachment=True,
            download_name=name,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as e:
        return _ivr_error(str(e), status=500)

