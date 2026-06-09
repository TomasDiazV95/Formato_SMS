from __future__ import annotations

import pandas as pd
from flask import Blueprint, request, send_file

from frontend import serve_react_app
from services.direcciones_depurador_service import (
    build_direcciones_depuradas,
    direcciones_depuradas_filename,
)
from utils import api_error_response
from utils.excel_export import df_to_xlsx_bytesio


direcciones_depurador_bp = Blueprint("direcciones_depurador", __name__)


def _direcciones_error(message: str, status: int = 400):
    return api_error_response(message, "direcciones_depurador.direcciones_page", status=status)


@direcciones_depurador_bp.get("/depuradores/direcciones")
def direcciones_page():
    return serve_react_app()


@direcciones_depurador_bp.post("/depuradores/direcciones")
def direcciones_process():
    archivo = request.files.get("archivo")
    if not archivo or archivo.filename == "":
        return _direcciones_error("Debes subir un archivo Excel de direcciones.")

    try:
        df_raw = pd.read_excel(archivo, dtype=str)
        df_out = build_direcciones_depuradas(df_raw)
        nombre = direcciones_depuradas_filename()
        buf = df_to_xlsx_bytesio(df_out, sheet_name="DireccionesDepuradas")
        return send_file(
            buf,
            as_attachment=True,
            download_name=nombre,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except ValueError as exc:
        return _direcciones_error(str(exc))
    except Exception as exc:
        return _direcciones_error(f"Error depurando direcciones: {exc}", status=500)
