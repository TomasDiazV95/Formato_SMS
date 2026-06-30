from __future__ import annotations

from datetime import date, datetime
import re

from flask import Blueprint, request, send_file

from frontend import serve_react_app
from services.santander_consumer_service import build_santander_consumer_terreno_from_excel
from services.santander_consumer_templates import get_santander_consumer_template
from utils import api_error_response
from utils.excel_export import df_to_xlsx_bytesio


santander_consumer_bp = Blueprint("santander_consumer", __name__)


def _sc_error(message: str, status: int = 400):
    return api_error_response(message, "santander_consumer.santander_consumer_page", status=status)


def _filename_token(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9]+", "_", value or "").strip("_").lower()
    return token or "plantilla"


@santander_consumer_bp.get("/santander-consumer")
def santander_consumer_page():
    return serve_react_app()


@santander_consumer_bp.post("/santander-consumer/terreno")
def santander_consumer_terreno_process():
    file = request.files.get("file")
    template_key = (request.form.get("template_key") or "").strip()
    asignacion_mode = (request.form.get("asignacion_mode") or "normal").strip().lower()
    offer_deadline_raw = (request.form.get("offer_deadline") or "").strip()
    if asignacion_mode not in {"normal", "supervisor_regiones", "supervisor_rm"}:
        asignacion_mode = "normal"
    if not file or file.filename == "":
        return _sc_error("Debes subir un archivo Excel.")
    if not template_key:
        return _sc_error("Debes seleccionar una plantilla.")
    template = get_santander_consumer_template(template_key)
    if not template:
        return _sc_error("Plantilla no válida para Santander Consumer.")

    requires_offer_deadline = template_key in {"susceptible", "reconduccion"}
    offer_deadline = None
    if requires_offer_deadline:
        if not offer_deadline_raw:
            return _sc_error("Debes seleccionar la fecha de plazo máximo válido.")
        try:
            offer_deadline = date.fromisoformat(offer_deadline_raw)
        except ValueError:
            return _sc_error("La fecha de plazo máximo válido no es válida.")

    try:
        salida = build_santander_consumer_terreno_from_excel(
            file,
            template_key=template_key,
            asignacion_mode=asignacion_mode,
            offer_deadline=offer_deadline,
        )
        fecha = datetime.now().strftime("%d-%m")
        nombre = f"sc_terreno_{_filename_token(template_key)}_{fecha}.xlsx"
        buf = df_to_xlsx_bytesio(salida, sheet_name="SantanderConsumer")
        return send_file(
            buf,
            as_attachment=True,
            download_name=nombre,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except ValueError as exc:
        return _sc_error(str(exc))
    except Exception as exc:
        return _sc_error(f"Ocurrió un error procesando el archivo: {exc}", status=500)
