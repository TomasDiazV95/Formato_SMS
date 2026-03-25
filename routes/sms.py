# routes/sms.py
import pandas as pd
from datetime import datetime
from flask import Blueprint, render_template, request, send_file, flash, redirect, url_for, abort

from services.sms_service import (
    build_crm_output,
    build_athenas_output,
    build_axia_output,
    sample_athenas_df,
    sample_axia_df,
)
from services.constants import MANDANTE_CHOICES
from services.mandante_rules import apply_mandante_rules
from services import db_repos
from utils.excel_export import df_to_xlsx_bytesio

sms_bp = Blueprint("sms", __name__)

@sms_bp.get("/")
def main():
    return render_template("portal.html")


@sms_bp.get("/procesos")
def procesos_menu():
    return render_template("procesos.html")


@sms_bp.get("/cargas")
def cargas_menu():
    return render_template("cargas.html")

@sms_bp.get("/sms")
def sms_page():
    return render_template("index.html", mandantes=MANDANTE_CHOICES)

@sms_bp.get("/sms/sample/<tipo>")
def sms_sample(tipo: str):
    tipo = (tipo or "").upper()
    if tipo == "ATHENAS":
        df = sample_athenas_df()
        sheet = "cargaAthenas"
        name = "ejemplo_SMS_ATHENAS.xlsx"
        header = True
    elif tipo == "AXIA":
        df = sample_axia_df()
        sheet = "Hoja1"
        name = "ejemplo_SMS_AXIA.xlsx"
        header = False
    else:
        abort(404)

    buf = df_to_xlsx_bytesio(df, sheet_name=sheet, header=header)
    return send_file(
        buf,
        as_attachment=True,
        download_name=name,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

@sms_bp.post("/sms/crm")
def sms_crm_process():
    file = request.files.get("file")
    usuario = (request.form.get("usuario") or "").strip()
    observacion = (request.form.get("observacion") or "").strip()
    fecha_str = (request.form.get("fecha") or "").strip()
    hora_inicio = (request.form.get("hora_inicio") or "").strip()
    hora_fin = (request.form.get("hora_fin") or "").strip()
    if not file or file.filename == "":
        flash("Debes subir un archivo Excel.", "danger")
        return redirect(url_for("sms.sms_page"))
    if not usuario:
        flash("Debes ingresar un Usuario.", "danger")
        return redirect(url_for("sms.sms_page"))
    if not fecha_str or not hora_inicio or not hora_fin:
        flash("Debes indicar FECHA DE GESTIÓN y el RANGO HORARIO.", "danger")
        return redirect(url_for("sms.sms_page"))

    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Formato de fecha inválido (usa AAAA-MM-DD).", "danger")
        return redirect(url_for("sms.sms_page"))

    try:
        df = pd.read_excel(file, dtype=str)
        carga_crm = build_crm_output(
            df,
            usuario=usuario,
            fecha=fecha,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            observacion=observacion,
            intervalo_segundos=5,
        )
        fecha_salida = fecha.strftime("%d-%m")
        buf = df_to_xlsx_bytesio(carga_crm, sheet_name="cargaCRM")

        return send_file(
            buf,
            as_attachment=True,
            download_name=f"cargaCRM_SMS_{fecha_salida}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    except Exception as e:
        flash(f"Ocurrió un error procesando el archivo: {e}", "danger")
        return redirect(url_for("sms.sms_page"))


@sms_bp.post("/sms/athenas")
def sms_athenas_process():
    file = request.files.get("file")
    mensaje = (request.form.get("mensaje") or "").strip()
    tipo_salida = (request.form.get("tipo_salida") or "").strip().upper()
    mandante_nombre = (request.form.get("mandante") or "").strip()

    if not file or file.filename == "":
        flash("Debes subir un archivo Excel.", "danger")
        return redirect(url_for("sms.sms_page"))
    if not mensaje:
        flash("Debes ingresar un Mensaje.", "danger")
        return redirect(url_for("sms.sms_page"))
    if not tipo_salida:
        flash("Debes escoger un formato de salida.", "danger")
        return redirect(url_for("sms.sms_page"))
    if not mandante_nombre:
        flash("Debes seleccionar un Mandante.", "danger")
        return redirect(url_for("sms.sms_page"))

    try:
        df = pd.read_excel(file, dtype=str)
        df = apply_mandante_rules(df, mandante_nombre)
        fecha_actual = datetime.now().strftime("%d-%m")

        mandante = db_repos.fetch_mandante_by_nombre(mandante_nombre)
        if not mandante:
            flash("Mandante no encontrado en catálogo.", "danger")
            return redirect(url_for("sms.sms_page"))

        if tipo_salida == "AXIA":
            carga = build_axia_output(df, mensaje=mensaje)
            proceso_codigo = "SMS_AXIA"
            buf = df_to_xlsx_bytesio(carga, sheet_name="Hoja1", header=False)
            nombre = f"carga_AXIA_SMS_{fecha_actual}.xlsx"
        else:
            carga = build_athenas_output(df, mensaje=mensaje)
            proceso_codigo = "SMS_ATHENAS"
            buf = df_to_xlsx_bytesio(carga, sheet_name="cargaAthenas")
            nombre = f"cargaAthenas_SMS_{fecha_actual}.xlsx"

        proceso = db_repos.fetch_proceso_by_codigo(proceso_codigo)
        if not proceso:
            flash("No se logró identificar el proceso para registrar costos.", "danger")
            return redirect(url_for("sms.sms_page"))

        total_registros = max(len(carga) - 1, 0)
        db_repos.log_masividad(
            mandante_id=mandante.id,
            proceso_id=proceso.id,
            total_registros=total_registros,
            costo_unitario=proceso.costo_unitario,
            usuario_app="sms",
            archivo_generado=nombre,
            observacion=mensaje,
            metadata={"formato": tipo_salida},
        )

        return send_file(
            buf,
            as_attachment=True,
            download_name=nombre,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    except Exception as e:
        flash(f"Ocurrió un error procesando el archivo: {e}", "danger")
        return redirect(url_for("sms.sms_page"))
