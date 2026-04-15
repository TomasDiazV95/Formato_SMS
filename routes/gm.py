# routes/gm.py
import pandas as pd
from datetime import datetime
from flask import Blueprint, request, send_file

from services.gm_service import procesar_gm
from services import db_repos
from utils.excel_export import zip_named_dfs_bytes
from utils import api_error_response
from frontend import serve_react_app

gm_bp = Blueprint("gm", __name__)


def _gm_error(message: str, status: int = 400):
    return api_error_response(message, "gm.gm_page", status=status)


def _find_masividad_df(named_dfs):
    for name, df in named_dfs:
        if isinstance(name, str) and "MASIVIDADES_GM" in name.upper():
            return name, df
    return None, None


def _build_gm_detalle(df):
    if df is None or df.empty:
        return []
    detalles = []
    for _, row in df.iterrows():
        detalles.append({
            "rut": str(row.get("RUT", "")).strip() or None,
            "operacion": str(row.get("OPERACION", "")).strip() or None,
            "mail": str(row.get("dest_email", "")).strip() or None,
            "plantilla": str(row.get("message_id", "")).strip() or None,
            "extra": {
                "institucion": str(row.get("INSTITUCIÓN", "")).strip() or None,
                "segmento": str(row.get("SEGMENTOINSTITUCIÓN", "")).strip() or None,
            }
        })
    return detalles

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

        masiv_filename, masiv_df = (None, None)
        if masividades:
            masiv_filename, masiv_df = _find_masividad_df(named_dfs)
            mandante = db_repos.fetch_mandante_by_nombre("General Motors")
            proceso = db_repos.fetch_proceso_by_codigo("MAIL_GM")
            if mandante and proceso and masiv_df is not None:
                total_registros = len(masiv_df.index)
                masiv_id = db_repos.log_masividad(
                    mandante_id=mandante.id,
                    proceso_id=proceso.id,
                    total_registros=total_registros,
                    costo_unitario=proceso.costo_unitario,
                    usuario_app="gm",
                    archivo_generado=masiv_filename,
                    observacion="Masividad GM",
                    metadata={"origen": "cargaGM"},
                )
                detalles = _build_gm_detalle(masiv_df)
                if masiv_id and detalles:
                    db_repos.bulk_insert_masividad_detalle(
                        masividad_log_id=masiv_id,
                        proceso_codigo=proceso.codigo,
                        mandante_nombre=mandante.nombre,
                        registros=detalles,
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
