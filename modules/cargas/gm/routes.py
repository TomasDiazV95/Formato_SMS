# routes/gm.py
import pandas as pd
from datetime import datetime
from flask import Blueprint, request, send_file

from services.gm_service import procesar_gm
from utils.excel_export import zip_named_dfs_bytes
from utils import api_error_response
from frontend import serve_react_app

gm_bp = Blueprint("gm", __name__)


def _gm_error(message: str, status: int = 400):
    return api_error_response(message, "gm.gm_page", status=status)


@gm_bp.route("/cargaGM", methods=["GET", "POST"])
def gm_page():
    if request.method == "GET":
        return serve_react_app()

    try:
        comparar = request.form.get("habilitar_comparacion") == "on"
        masividades = request.form.get("habilitar_masividades") == "on"

        archivo = request.files.get("archivo")
        if not archivo or archivo.filename == "":
            return _gm_error("Debes subir el archivo Collection (Nuevo).")

        df_nuevo = pd.read_excel(archivo)

        df_ant = None
        if comparar:
            archivo_anterior = request.files.get("archivo_anterior")
            if not archivo_anterior or archivo_anterior.filename == "":
                return _gm_error("Activaste comparación, pero no subiste archivo anterior.")
            df_ant = pd.read_excel(archivo_anterior)

        # Procesa y devuelve lista de (nombre_excel, df)
        named_dfs = procesar_gm(
            df_nuevo=df_nuevo,
            df_antiguo=df_ant,
            comparar=comparar,
            masividades=masividades,
        )

        fecha = datetime.now().strftime("%d-%m")
        zip_buf = zip_named_dfs_bytes(named_dfs)

        return send_file(
            zip_buf,
            as_attachment=True,
            download_name=f"Procesamiento_GM_{fecha}.zip",
            mimetype="application/zip",
        )

    except Exception as e:
        return _gm_error(f"Error al procesar: {e}", status=500)
