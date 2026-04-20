from __future__ import annotations

from flask import Blueprint, request, send_file

from frontend import serve_react_app
from services.bit_asignacion_service import build_bit_outputs
from utils import api_error_response
from utils.excel_export import zip_named_dfs_bytes


bit_bp = Blueprint("bit_asignacion", __name__)


def _bit_error(message: str, status: int = 400):
    return api_error_response(message, "bit_asignacion.bit_page", status=status)


@bit_bp.route("/cargaBIT", methods=["GET", "POST"])
def bit_page():
    if request.method == "GET":
        return serve_react_app()

    archivo = request.files.get("archivo")
    if not archivo or archivo.filename == "":
        return _bit_error("Debes subir un archivo CSV de BIT.")

    campana_nueva = request.form.get("campana_nueva") == "on"

    try:
        named_dfs = build_bit_outputs(archivo, campana_nueva=campana_nueva)
        zip_buf = zip_named_dfs_bytes(named_dfs)
        suffix = "_NEW" if campana_nueva else ""
        return send_file(
            zip_buf,
            as_attachment=True,
            download_name=f"BIT_CARGA{suffix}.zip",
            mimetype="application/zip",
        )
    except ValueError as exc:
        return _bit_error(str(exc))
    except Exception as exc:
        return _bit_error(f"Error procesando BIT: {exc}", status=500)
