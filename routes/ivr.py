
import pandas as pd
from datetime import datetime
from flask import Blueprint, render_template, request, send_file, flash, redirect, url_for
import io

from services.ivr_service import CAMPO1_CHOICES, build_ivr_output, build_crm_output
from utils.excel_export import df_to_xlsx_bytesio

ivr_bp = Blueprint("ivr", __name__)

@ivr_bp.get("/ivr")
def ivr_page():
    campo1_options = [{"label": l, "value": v} for l, v in CAMPO1_CHOICES]
    usuarios = ["dlopez", "jriveros", "VDAD"]  # ajusta si quieres
    return render_template("ivr.html", campo1_options=campo1_options, usuarios=usuarios)

@ivr_bp.post("/ivr/process")
def ivr_process():
    file = request.files.get("file")
    campo1 = (request.form.get("campo1") or "").strip()

    if not file or file.filename == "":
        flash("Debes subir un archivo Excel.", "danger")
        return redirect(url_for("ivr.ivr_page"))
    if not campo1:
        flash("Debes seleccionar un valor para CAMPO1.", "danger")
        return redirect(url_for("ivr.ivr_page"))

    try:
        df = pd.read_excel(file, engine="openpyxl")
        out = build_ivr_output(df, campo1_value=campo1)

        fecha = datetime.now().strftime("%d-%m")
        name = f"cargaIVR_{fecha}_.xlsx"
        buf = df_to_xlsx_bytesio(out, sheet_name="Hoja1")

        return send_file(
            buf,
            as_attachment=True,
            download_name=name,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as e:
        flash(str(e), "danger")
        return redirect(url_for("ivr.ivr_page"))

@ivr_bp.post("/ivr_crm/process")
def ivr_crm_process():
    file          = request.files.get("file")
    usuario       = (request.form.get("usuario") or "").strip()
    fecha_str     = (request.form.get("fecha") or "").strip()
    hora_inicio   = (request.form.get("hora_inicio") or "").strip()
    hora_fin      = (request.form.get("hora_fin") or "").strip()
    intervalo_str = (request.form.get("intervalo") or "").strip()

    intervalo = None
    if intervalo_str:
        try:
            intervalo_val = int(intervalo_str)
            if intervalo_val > 0:
                intervalo = intervalo_val
            else:
                flash("El intervalo debe ser un entero positivo en segundos.", "danger")
                return redirect(url_for("ivr.ivr_page"))
        except Exception:
            flash("Intervalo inválido. Usa un entero en segundos.", "danger")
            return redirect(url_for("ivr.ivr_page"))

    if not file or file.filename == "":
        flash("Debes subir un archivo Excel.", "danger")
        return redirect(url_for("ivr.ivr_page"))
    if not usuario:
        flash("Debes seleccionar un USUARIO.", "danger")
        return redirect(url_for("ivr.ivr_page"))
    if not fecha_str or not hora_inicio or not hora_fin:
        flash("Debes indicar FECHA DE GESTIÓN y el RANGO HORARIO.", "danger")
        return redirect(url_for("ivr.ivr_page"))

    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Formato de fecha inválido (usa AAAA-MM-DD).", "danger")
        return redirect(url_for("ivr.ivr_page"))

    try:
        df = pd.read_excel(file, engine="openpyxl")
        salida = build_crm_output(
            df=df,
            fecha=fecha,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            usuario_value=usuario,
            intervalo_segundos=intervalo
        )
        fecha_actual = datetime.now().strftime("%d-%m")
        name = f"cargaIVR_CRM_{fecha_actual}.xlsx"
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            salida.to_excel(writer, index=False, sheet_name="Hoja1")
        buf.seek(0)
        return send_file(
            buf,
            as_attachment=True,
            download_name=name,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except ValueError as e:
        flash(str(e), "danger")
        return redirect(url_for("ivr.ivr_page"))
    except Exception as e:
        flash(f"Ocurrió un error procesando el archivo: {e}", "danger")
        return redirect(url_for("ivr.ivr_page"))