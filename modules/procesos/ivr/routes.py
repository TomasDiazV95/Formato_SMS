
import io
import zipfile
import pandas as pd
from datetime import date, datetime
from flask import Blueprint, jsonify, request, send_file
import re
import unicodedata

from services.ivr_service import build_crm_output as build_ivr_crm_output, build_ivr_output, get_campo1_choices, sample_ivr_df
from services.mandante_rules import apply_mandante_rules
from utils.excel_export import df_to_xlsx_bytes, df_to_xlsx_bytesio
from utils import api_error_response
from frontend import serve_react_app

ivr_bp = Blueprint("ivr", __name__)

IVR_CRM_RULES = {
    "santander consumer terreno": ("jriveros", ""),
    "santander consumer telefonía": ("jriveros", ""),
    "santander consumer telefonia": ("jriveros", ""),
    "santander consumer judicial": ("jriveros", ""),
    "general motors": ("jriveros", "IVR"),
    "itau vencida": ("VDAD", ""),
    "itau castigo": ("VDAD", ""),
    "banco internacional": ("VDAD", ""),
    "santander hipotecario": ("VDAD", ""),
    "la araucana": ("VDAD", ""),
    "tanner": ("VDAD", ""),
}


def _ivr_error(message: str, status: int = 400):
    return api_error_response(message, "ivr.ivr_page", status=status)


def _filename_token(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")
    return text or "MANDANTE"


def _crm_rule_for_ivr(mandante: str) -> tuple[str, str] | None:
    return IVR_CRM_RULES.get((mandante or "").strip().lower())


def _zip_ivr_outputs(files: list[tuple[str, bytes]]) -> io.BytesIO:
    zip_bio = io.BytesIO()
    with zipfile.ZipFile(zip_bio, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for filename, payload in files:
            zf.writestr(filename, payload)
    zip_bio.seek(0)
    return zip_bio

@ivr_bp.get("/ivr")
def ivr_page():
    return serve_react_app()

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


@ivr_bp.get("/ivr/campo1-options")
def ivr_campo1_options():
    options = [{"label": label, "value": value} for label, value in get_campo1_choices()]
    return jsonify({"items": options})

@ivr_bp.post("/ivr/process")
def ivr_process():
    file = request.files.get("file")
    campo1 = (request.form.get("campo1") or "").strip()
    mandante_nombre = (request.form.get("mandante") or "").strip()
    include_crm = request.form.get("include_crm") == "on"
    crm_fecha_raw = (request.form.get("crm_fecha") or "").strip()
    crm_hora_inicio = (request.form.get("crm_hora_inicio") or "").strip()
    crm_hora_fin = (request.form.get("crm_hora_fin") or "").strip()

    if not file or file.filename == "":
        return _ivr_error("Debes subir un archivo Excel.")
    if not campo1:
        return _ivr_error("Debes seleccionar un valor para CAMPO1.")

    allowed_values = {value for _, value in get_campo1_choices()}
    if campo1 not in allowed_values:
        return _ivr_error("El CAMPO1 seleccionado no esta habilitado en catalogo.")

    if not mandante_nombre:
        return _ivr_error("Debes seleccionar un Mandante.")
    if include_crm:
        if not crm_fecha_raw or not crm_hora_inicio or not crm_hora_fin:
            return _ivr_error("Debes indicar fecha, hora inicio y hora fin para generar CRM.")
        crm_rule = _crm_rule_for_ivr(mandante_nombre)
        if not crm_rule:
            return _ivr_error("No hay regla CRM configurada para este mandante en IVR.")
        try:
            crm_fecha = date.fromisoformat(crm_fecha_raw)
        except ValueError:
            return _ivr_error("La fecha de gestion CRM no es valida.")
    else:
        crm_rule = None
        crm_fecha = None

    try:
        df = pd.read_excel(file, dtype=str)
        df = apply_mandante_rules(df, mandante_nombre)
        out = build_ivr_output(df, campo1_value=campo1)
        fecha = datetime.now().strftime("%d-%m")

        mandante_token = _filename_token(mandante_nombre)
        name = f"carga_IVR_ATHENAS_{mandante_token}_{fecha}.xlsx"

        if include_crm and crm_rule and crm_fecha:
            usuario, observacion = crm_rule
            crm_df = build_ivr_crm_output(
                df,
                fecha=crm_fecha,
                hora_inicio=crm_hora_inicio,
                hora_fin=crm_hora_fin,
                usuario_value=usuario,
                observacion_value=observacion,
            )
            crm_base = f"carga_CRM_IVR_{mandante_token}_{fecha}"
            files = [
                (name, df_to_xlsx_bytes(out, sheet_name="Hoja1")),
                (f"{crm_base}.xlsx", df_to_xlsx_bytes(crm_df, sheet_name="cargaCRM")),
                (f"{crm_base}.csv", crm_df.to_csv(index=False, sep=";", encoding="utf-8-sig").encode("utf-8-sig")),
            ]
            return send_file(
                _zip_ivr_outputs(files),
                as_attachment=True,
                download_name=f"IVR_{mandante_token}_{fecha}.zip",
                mimetype="application/zip",
            )

        buf = df_to_xlsx_bytesio(out, sheet_name="Hoja1")

        return send_file(
            buf,
            as_attachment=True,
            download_name=name,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as e:
        return _ivr_error(str(e), status=500)

