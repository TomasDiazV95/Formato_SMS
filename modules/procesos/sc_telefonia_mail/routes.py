from __future__ import annotations

from datetime import date, datetime
import re

from flask import Blueprint, request, send_file

from frontend import serve_react_app
from services.sc_telefonia_mail_service import build_sc_telefonia_mail_from_excel
from services.sc_telefonia_mail_sources import list_allowed_executives
from services.sc_telefonia_mail_templates import get_sc_telefonia_mail_template, list_sc_telefonia_mail_templates
from utils import api_error_response
from utils.excel_export import df_to_xlsx_bytesio


sc_telefonia_mail_bp = Blueprint("sc_telefonia_mail", __name__)


def _sc_tel_error(message: str, status: int = 400):
    return api_error_response(message, "sc_telefonia_mail.sc_telefonia_mail_page", status=status)


def _filename_token(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9]+", "_", value or "").strip("_")
    return token or "SC_TELEFONIA_MAIL"


@sc_telefonia_mail_bp.get("/sc-telefonia-mail")
def sc_telefonia_mail_page():
    return serve_react_app()


@sc_telefonia_mail_bp.get("/sc-telefonia-mail/templates")
def sc_telefonia_mail_templates():
    templates = list_sc_telefonia_mail_templates()
    return {
        "templates": [
            {
                "key": item.get("key"),
                "label": item.get("label"),
                "filename_prefix": item.get("filename_prefix") or item.get("label"),
                "requires_date": bool(item.get("requires_date")),
                "requires_executive": bool(item.get("requires_executive")),
            }
            for item in templates
        ]
    }


@sc_telefonia_mail_bp.get("/sc-telefonia-mail/executives")
def sc_telefonia_mail_executives():
    template_key = (request.args.get("template_key") or "").strip()
    template = get_sc_telefonia_mail_template(template_key)
    if not template:
        return {"executives": []}
    allowed = template.get("allowed_executives") if isinstance(template.get("allowed_executives"), list) else []
    return {"executives": list_allowed_executives([str(item) for item in allowed])}


@sc_telefonia_mail_bp.post("/sc-telefonia-mail/generar")
def sc_telefonia_mail_process():
    file = request.files.get("file")
    template_key = (request.form.get("template_key") or "").strip()
    selected_date_raw = (request.form.get("selected_date") or "").strip()
    executive_key = (request.form.get("executive_key") or "").strip()

    if not file or file.filename == "":
        return _sc_tel_error("Debes subir un archivo Excel con operaciones.")
    if not template_key:
        return _sc_tel_error("Debes seleccionar una plantilla.")
    template = get_sc_telefonia_mail_template(template_key)
    if not template:
        return _sc_tel_error("Plantilla no valida para Santander Consumer Telefonia.")

    selected_date = None
    if template.get("requires_date"):
        if not selected_date_raw:
            return _sc_tel_error("Debes seleccionar la fecha.")
        try:
            selected_date = date.fromisoformat(selected_date_raw)
        except ValueError:
            return _sc_tel_error("La fecha no es valida.")
    if template.get("requires_executive") and not executive_key:
        return _sc_tel_error("Debes seleccionar una ejecutiva.")

    try:
        salida = build_sc_telefonia_mail_from_excel(
            file,
            template_key=template_key,
            selected_date=selected_date,
            executive_key=executive_key,
        )
        fecha = datetime.now().strftime("%d-%m")
        prefix = template.get("filename_prefix") or template.get("label") or "SC_TELEFONIA_MAIL"
        nombre = f"{_filename_token(str(prefix))}_{fecha}.xlsx"
        sheet_name = str(template.get("sheet_name") or "PlantillaMail")[:31]
        buf = df_to_xlsx_bytesio(salida, sheet_name=sheet_name)
        return send_file(
            buf,
            as_attachment=True,
            download_name=nombre,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except ValueError as exc:
        return _sc_tel_error(str(exc))
    except Exception as exc:
        return _sc_tel_error(f"Ocurrio un error procesando el archivo: {exc}", status=500)
