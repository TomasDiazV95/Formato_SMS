from __future__ import annotations

import pandas as pd
from flask import Blueprint, request, send_file

from frontend import serve_react_app
from services.tanner_asignacion_service import build_tanner_asignacion, tanner_asignacion_filename
from utils import api_error_response
from utils.excel_export import df_to_xlsx_bytesio


tanner_bp = Blueprint("tanner_asignacion", __name__)


def _tanner_error(message: str, status: int = 400):
    return api_error_response(message, "tanner_asignacion.tanner_page", status=status)


@tanner_bp.route("/cargaTanner", methods=["GET", "POST"])
def tanner_page():
    if request.method == "GET":
        return serve_react_app()

    archivo = request.files.get("archivo")
    if not archivo or archivo.filename == "":
        return _tanner_error("Debes subir el archivo de Asignacion Tanner.")

    try:
        df_raw = pd.read_excel(archivo, dtype=str)
        df_out = build_tanner_asignacion(df_raw)
        nombre = tanner_asignacion_filename()
        buf = df_to_xlsx_bytesio(df_out, sheet_name="AsignacionTanner")
        return send_file(
            buf,
            as_attachment=True,
            download_name=nombre,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except ValueError as exc:
        return _tanner_error(str(exc))
    except Exception as exc:
        return _tanner_error(f"Error procesando archivo Tanner: {exc}", status=500)
