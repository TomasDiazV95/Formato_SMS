from __future__ import annotations

from datetime import datetime
import re

from flask import Blueprint, request, send_file

from frontend import serve_react_app
from services.gm_mail_service import build_gm_mail_from_excel
from services.gm_mail_templates import get_gm_mail_template, list_gm_mail_templates
from utils import api_error_response
from utils.excel_export import df_to_xlsx_bytesio


gm_mail_bp = Blueprint("gm_mail", __name__)


def _gm_mail_error(message: str, status: int = 400):
    return api_error_response(message, "gm_mail.gm_mail_page", status=status)


def _filename_token(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9]+", "_", value or "").strip("_")
    return token or "GM_MAIL"


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
            }
            for item in templates
        ]
    }


@gm_mail_bp.post("/gm-mail/generar")
def gm_mail_process():
    file = request.files.get("file")
    template_key = (request.form.get("template_key") or "gm_comercial_84995").strip()
    if not file or file.filename == "":
        return _gm_mail_error("Debes subir un archivo Excel con operaciones.")
    template = get_gm_mail_template(template_key)
    if not template:
        return _gm_mail_error("Plantilla no valida para GM Mail.")

    try:
        salida = build_gm_mail_from_excel(file, template_key=template_key)
        fecha = datetime.now().strftime("%d-%m")
        prefix = template.get("filename_prefix") or template.get("label") or "GM_MAIL"
        nombre = f"{_filename_token(str(prefix))}_{fecha}.xlsx"
        sheet_name = str(template.get("sheet_name") or "GeneralMotors")[:31]
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
