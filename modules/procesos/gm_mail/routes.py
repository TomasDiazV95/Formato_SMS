from __future__ import annotations

import io
import zipfile
from datetime import date, datetime
import re

from flask import Blueprint, request, send_file

from frontend import serve_react_app
from services.gm_mail_service import build_gm_mail_crm_output, build_gm_mail_from_excel
from services.gm_mail_templates import get_gm_mail_template, list_gm_mail_templates
from utils import api_error_response
from utils.excel_export import df_to_xlsx_bytes, df_to_xlsx_bytesio


gm_mail_bp = Blueprint("gm_mail", __name__)


def _gm_mail_error(message: str, status: int = 400):
    return api_error_response(message, "gm_mail.gm_mail_page", status=status)


def _filename_token(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9]+", "_", value or "").strip("_")
    return token or "GM_MAIL"


def _zip_gm_mail_outputs(
    *,
    template_filename: str,
    template_sheet: str,
    template_df,
    crm_filename_base: str,
    crm_df,
) -> io.BytesIO:
    zip_bio = io.BytesIO()
    with zipfile.ZipFile(zip_bio, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(template_filename, df_to_xlsx_bytes(template_df, sheet_name=template_sheet))
        zf.writestr(f"{crm_filename_base}.xlsx", df_to_xlsx_bytes(crm_df, sheet_name="CRM"))
        csv_payload = crm_df.to_csv(index=False, sep=";", encoding="utf-8-sig")
        zf.writestr(f"{crm_filename_base}.csv", csv_payload)
    zip_bio.seek(0)
    return zip_bio


@gm_mail_bp.get("/gm-mail")
def gm_mail_page():
    return serve_react_app()


@gm_mail_bp.get("/gm-mail/templates")
def gm_mail_templates():
    templates = list_gm_mail_templates()
    return {
        "templates": [
            {
                "key": item.get("key"),
                "label": item.get("label"),
                "filename_prefix": item.get("filename_prefix") or item.get("label"),
                "requires_delivery_date": bool(item.get("requires_delivery_date")),
            }
            for item in templates
        ]
    }


@gm_mail_bp.post("/gm-mail/generar")
def gm_mail_process():
    file = request.files.get("file")
    template_key = (request.form.get("template_key") or "gm_comercial_84995").strip()
    delivery_date_raw = (request.form.get("delivery_date") or "").strip()
    include_crm = request.form.get("include_crm") == "on"
    crm_fecha_raw = (request.form.get("crm_fecha") or "").strip()
    crm_hora_inicio = (request.form.get("crm_hora_inicio") or "").strip()
    crm_hora_fin = (request.form.get("crm_hora_fin") or "").strip()
    if not file or file.filename == "":
        return _gm_mail_error("Debes subir un archivo Excel con operaciones.")
    template = get_gm_mail_template(template_key)
    if not template:
        return _gm_mail_error("Plantilla no valida para GM Mail.")
    delivery_date = None
    if template.get("requires_delivery_date"):
        if not delivery_date_raw:
            return _gm_mail_error("Debes seleccionar la fecha de entrega.")
        try:
            delivery_date = date.fromisoformat(delivery_date_raw)
        except ValueError:
            return _gm_mail_error("La fecha de entrega no es valida.")
    crm_fecha = None
    if include_crm:
        if not crm_fecha_raw or not crm_hora_inicio or not crm_hora_fin:
            return _gm_mail_error("Debes indicar fecha, hora inicio y hora fin para generar CRM.")
        try:
            crm_fecha = date.fromisoformat(crm_fecha_raw)
        except ValueError:
            return _gm_mail_error("La fecha de gestion CRM no es valida.")

    try:
        salida = build_gm_mail_from_excel(file, template_key=template_key, delivery_date=delivery_date)
        fecha = datetime.now().strftime("%d-%m")
        prefix = template.get("filename_prefix") or template.get("label") or "GM_MAIL"
        nombre = f"{_filename_token(str(prefix))}_{fecha}.xlsx"
        sheet_name = str(template.get("sheet_name") or "GeneralMotors")[:31]
        if include_crm:
            crm_df = build_gm_mail_crm_output(
                salida,
                fecha=crm_fecha,
                hora_inicio=crm_hora_inicio,
                hora_fin=crm_hora_fin,
            )
            crm_base = f"cargaCRM_GM_MAIL_{fecha}"
            zip_buf = _zip_gm_mail_outputs(
                template_filename=nombre,
                template_sheet=sheet_name,
                template_df=salida,
                crm_filename_base=crm_base,
                crm_df=crm_df,
            )
            return send_file(
                zip_buf,
                as_attachment=True,
                download_name=f"GM_MAIL_{fecha}.zip",
                mimetype="application/zip",
            )
        buf = df_to_xlsx_bytesio(salida, sheet_name=sheet_name)
        return send_file(
            buf,
            as_attachment=True,
            download_name=nombre,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except ValueError as exc:
        return _gm_mail_error(str(exc))
    except Exception as exc:
        return _gm_mail_error(f"Ocurrio un error procesando el archivo: {exc}", status=500)
