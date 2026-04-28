from __future__ import annotations

from datetime import datetime

from flask import Blueprint, request, send_file

from frontend import serve_react_app
from services.santander_consumer_service import build_santander_consumer_terreno_from_excel
from utils import api_error_response
from utils.excel_export import df_to_xlsx_bytesio


santander_consumer_bp = Blueprint("santander_consumer", __name__)


def _sc_error(message: str, status: int = 400):
    return api_error_response(message, "santander_consumer.santander_consumer_page", status=status)


@santander_consumer_bp.get("/santander-consumer")
def santander_consumer_page():
    return serve_react_app()


@santander_consumer_bp.post("/santander-consumer/terreno")
def santander_consumer_terreno_process():
    file = request.files.get("file")
    template_key = (request.form.get("template_key") or "").strip()
    asignacion_mode = (request.form.get("asignacion_mode") or "normal").strip().lower()
    if asignacion_mode not in {"normal", "supervisor_regiones", "supervisor_rm"}:
        asignacion_mode = "normal"
    if not file or file.filename == "":
        return _sc_error("Debes subir un archivo Excel.")
    if not template_key:
        return _sc_error("Debes seleccionar una plantilla.")

    try:
        salida = build_santander_consumer_terreno_from_excel(
            file,
            template_key=template_key,
            asignacion_mode=asignacion_mode,
        )
        fecha = datetime.now().strftime("%d-%m")
        nombre = f"Santander_Consumer_Terreno_{fecha}.xlsx"
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
