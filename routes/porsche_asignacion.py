from __future__ import annotations

import pandas as pd
from flask import Blueprint, request, send_file

from frontend import serve_react_app
from services.porsche_asignacion_service import build_porsche_asignacion, porsche_asignacion_filename
from utils import api_error_response
from utils.excel_export import df_to_xlsx_bytesio


porsche_bp = Blueprint("porsche_asignacion", __name__)


def _porsche_error(message: str, status: int = 400):
    return api_error_response(message, "porsche_asignacion.porsche_page", status=status)


@porsche_bp.route("/cargaPorsche", methods=["GET", "POST"])
def porsche_page():
    if request.method == "GET":
        return serve_react_app()

    archivo = request.files.get("archivo")
    if not archivo or archivo.filename == "":
        return _porsche_error("Debes subir el archivo de Asignacion Porsche.")

    try:
        df_raw = pd.read_excel(archivo, dtype=str, header=None)
        df_out = build_porsche_asignacion(df_raw)
        nombre = porsche_asignacion_filename()
        buf = df_to_xlsx_bytesio(df_out, sheet_name="AsignacionPorsche")
        return send_file(
            buf,
            as_attachment=True,
            download_name=nombre,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except ValueError as exc:
        return _porsche_error(str(exc))
    except Exception as exc:
        return _porsche_error(f"Error procesando archivo Porsche: {exc}", status=500)
