import os
import uuid

from flask import Blueprint, render_template, request, send_file, flash, current_app

from services.sant_hipotecario_service import leer_csv_sant_hipotecario, generar_crm
from services.sant_hipotecario_masividad_service import generar_masividad

sant_hipotecario_bp = Blueprint("sant_hipotecario", __name__)

GENERADOS = {}  # token -> data


@sant_hipotecario_bp.route("/sant-hipotecario", methods=["GET", "POST"])
def sant_hipotecario_page():
    if request.method == "POST":
        archivo = request.files.get("archivo")
        masividades = request.form.get("habilitar_masividades") == "on"

        if not archivo:
            flash("Debes subir un archivo CSV.", "danger")
            return render_template("sant_hipotecario.html")

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

            flash("Archivo procesado correctamente ✅", "success")
            return render_template(
                "sant_hipotecario.html",
                token=token,
                masividades_activadas=masividades,
                crm_name=data["crm_name"],
                masiv_name=data["masiv_name"],
            )

        except Exception as e:
            flash(f"Error procesando archivo: {e}", "danger")
            return render_template("sant_hipotecario.html")

    return render_template("sant_hipotecario.html")


@sant_hipotecario_bp.route("/sant-hipotecario/descargar/crm/<token>")
def descargar_crm(token):
    data = GENERADOS.get(token)
    if not data or not data.get("crm_path"):
        flash("No se encontró el CRM para descargar.", "danger")
        return render_template("sant_hipotecario.html")

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
        flash("No se encontró masividad para descargar (activa el switch y procesa).", "danger")
        return render_template("sant_hipotecario.html")

    return send_file(
        data["masiv_path"],
        as_attachment=True,
        download_name=data["masiv_name"],
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
