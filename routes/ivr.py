
import pandas as pd
from datetime import datetime
from flask import Blueprint, render_template, request, send_file, flash, redirect, url_for
import io

from services.ivr_service import CAMPO1_CHOICES, build_ivr_output, build_crm_output, sample_ivr_df
from services.constants import MANDANTE_CHOICES
from services.mandante_rules import apply_mandante_rules
from services import db_repos
from utils.excel_export import df_to_xlsx_bytesio

ivr_bp = Blueprint("ivr", __name__)

@ivr_bp.get("/ivr")
def ivr_page():
    campo1_options = [{"label": l, "value": v} for l, v in CAMPO1_CHOICES]
    usuarios = ["dlopez", "jriveros", "VDAD"]  # ajusta si quieres
    return render_template("ivr.html", campo1_options=campo1_options, usuarios=usuarios, mandantes=MANDANTE_CHOICES)

@ivr_bp.get("/ivr/sample")
def ivr_sample():
    df = sample_ivr_df()
    name = "ejemplo_IVR_ATHENAS.xlsx"
    buf = df_to_xlsx_bytesio(df, sheet_name="Hoja1")
    return send_file(
        buf,
        as_attachment=True,
        download_name=name,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

@ivr_bp.post("/ivr/process")
def ivr_process():
    file = request.files.get("file")
    campo1 = (request.form.get("campo1") or "").strip()
    mandante_nombre = (request.form.get("mandante") or "").strip()

    if not file or file.filename == "":
        flash("Debes subir un archivo Excel.", "danger")
        return redirect(url_for("ivr.ivr_page"))
    if not campo1:
        flash("Debes seleccionar un valor para CAMPO1.", "danger")
        return redirect(url_for("ivr.ivr_page"))
    if not mandante_nombre:
        flash("Debes seleccionar un Mandante.", "danger")
        return redirect(url_for("ivr.ivr_page"))

    try:
        df = pd.read_excel(file, dtype=str)
        df = apply_mandante_rules(df, mandante_nombre)
        out = build_ivr_output(df, campo1_value=campo1)
        fecha = datetime.now().strftime("%d-%m")
        name = f"carga_IVR_ATHENAS_{fecha}.xlsx"
        buf = df_to_xlsx_bytesio(out, sheet_name="Hoja1")

        mandante = db_repos.fetch_mandante_by_nombre(mandante_nombre)
        if not mandante:
            flash("Mandante no encontrado en catálogo.", "danger")
            return redirect(url_for("ivr.ivr_page"))

        proceso = db_repos.fetch_proceso_by_codigo("IVR_ATHENAS")
        if not proceso:
            flash("No se logró identificar el proceso para registrar costos.", "danger")
            return redirect(url_for("ivr.ivr_page"))

        total_registros = max(len(out) - 1, 0)
        db_repos.log_masividad(
            mandante_id=mandante.id,
            proceso_id=proceso.id,
            total_registros=total_registros,
            costo_unitario=proceso.costo_unitario,
            usuario_app="ivr",
            archivo_generado=name,
            observacion="IVR Athenas",
            metadata={"campo1": campo1},
        )

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
    observacion   = (request.form.get("observacion") or "").strip()
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
        df = pd.read_excel(file, dtype=str)
        salida = build_crm_output(
            df=df,
            fecha=fecha,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            usuario_value=usuario,
            observacion_value=observacion,
            intervalo_segundos=intervalo
        )
        fecha_salida = fecha.strftime("%d-%m")
        name = f"carga_IVR_CRM_{fecha_salida}.xlsx"
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
