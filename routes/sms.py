# routes/sms.py
import pandas as pd
from datetime import datetime
from flask import Blueprint, render_template, request, send_file, flash, redirect, url_for

from services.sms_service import build_outputs
from utils.excel_export import zip_two_excels_bytes

sms_bp = Blueprint("sms", __name__)

@sms_bp.get("/")
def main():
    return render_template("main.html")

@sms_bp.get("/sms")
def sms_page():
    return render_template("index.html")

@sms_bp.post("/sms/process")
def sms_process():
    file = request.files.get("file")
    mensaje = (request.form.get("mensaje") or "").strip()
    usuario = (request.form.get("usuario") or "").strip()

    if not file or file.filename == "":
        flash("Debes subir un archivo Excel.", "danger")
        return redirect(url_for("sms.sms_page"))
    if not mensaje:
        flash("Debes ingresar un Mensaje.", "danger")
        return redirect(url_for("sms.sms_page"))
    if not usuario:
        flash("Debes ingresar un Usuario.", "danger")
        return redirect(url_for("sms.sms_page"))

    try:
        df = pd.read_excel(file)

        cargaCRM_df, cargaAthenas_df = build_outputs(df, mensaje=mensaje, usuario=usuario)

        fecha_actual = datetime.now().strftime("%d-%m")
        zip_buf = zip_two_excels_bytes(
            (f"cargaCRM_{fecha_actual}_.xlsx", cargaCRM_df, "cargaCRM"),
            (f"cargaAthenas_{fecha_actual}_.xlsx", cargaAthenas_df, "cargaAthenas"),
        )

        return send_file(
            zip_buf,
            as_attachment=True,
            download_name=f"salidas_{fecha_actual}.zip",
            mimetype="application/zip",
        )

    except Exception as e:
        flash(f"Ocurrió un error procesando el archivo: {e}", "danger")
        return redirect(url_for("sms.sms_page"))
