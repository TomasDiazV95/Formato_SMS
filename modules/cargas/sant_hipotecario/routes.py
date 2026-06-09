import os
import uuid

from flask import Blueprint, request, send_file, current_app, jsonify

from services.sant_hipotecario_service import leer_csv_sant_hipotecario, generar_crm
from services.sant_hipotecario_masividad_service import generar_masividad
from frontend import serve_react_app
from utils import api_error_response

sant_hipotecario_bp = Blueprint("sant_hipotecario", __name__)

GENERADOS = {}  # token -> data


def _sant_error(message: str, status: int = 400):
    return api_error_response(message, "sant_hipotecario.sant_hipotecario_page", status=status)


@sant_hipotecario_bp.route("/sant-hipotecario", methods=["GET", "POST"])
def sant_hipotecario_page():
    if request.method == "GET":
        return serve_react_app()

    if request.method == "POST":
        archivo = request.files.get("archivo")
        masividades = request.form.get("habilitar_masividades") == "on"

        if not archivo:
            return _sant_error("Debes subir un archivo CSV.")

        try:
            df = leer_csv_sant_hipotecario(archivo)

            output_dir = os.path.join(current_app.root_path, "outputs", "sant_hipotecario")

            crm_res = generar_crm(df, output_dir)
            data = {
                "crm_path": crm_res["crm_path"],
                "crm_name": crm_res["crm_name"],
                "masiv_path": None,
                "masiv_name": None
            }

            if masividades:
                mas_res = generar_masividad(df, output_dir)
                data["masiv_path"] = mas_res["masiv_path"]
                data["masiv_name"] = mas_res["masiv_name"]

            token = str(uuid.uuid4())
            GENERADOS[token] = data

            return jsonify({
                "message": "Archivo procesado correctamente.",
                "token": token,
                "crm_name": data["crm_name"],
                "masiv_name": data["masiv_name"],
                "masividades_activadas": masividades,
            })

        except Exception as e:
            return _sant_error(f"Error procesando archivo: {e}", status=500)

    return serve_react_app()


@sant_hipotecario_bp.route("/sant-hipotecario/descargar/crm/<token>")
def descargar_crm(token):
    data = GENERADOS.get(token)
    if not data or not data.get("crm_path"):
        return _sant_error("No se encontró el CRM para descargar.", status=404)

    return send_file(
        data["crm_path"],
        as_attachment=True,
        download_name=data["crm_name"],
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@sant_hipotecario_bp.route("/sant-hipotecario/descargar/masividad/<token>")
def descargar_masividad(token):
    data = GENERADOS.get(token)
    if not data or not data.get("masiv_path"):
        return _sant_error("No se encontró masividad para descargar (activa el switch y procesa).", status=404)

    return send_file(
        data["masiv_path"],
        as_attachment=True,
        download_name=data["masiv_name"],
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
