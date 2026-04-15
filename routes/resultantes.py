from __future__ import annotations

import io
from datetime import datetime

from flask import Blueprint, request, send_file

from frontend import serve_react_app
from services.resultantes_service import build_resultante_file
from utils import api_error_response


resultantes_bp = Blueprint("resultantes", __name__)


def _resultantes_error(message: str, status: int = 400):
    return api_error_response(message, "resultantes.resultantes_page", status=status)


@resultantes_bp.get("/resultantes")
def resultantes_page():
    return serve_react_app()


@resultantes_bp.get("/resultantes/download")
def resultantes_download():
    mandante = (request.args.get("mandante") or "").strip()
    fecha_inicio_raw = (request.args.get("fecha_inicio") or request.args.get("fecha") or "").strip()
    fecha_fin_raw = (request.args.get("fecha_fin") or fecha_inicio_raw).strip()

    if not mandante:
        return _resultantes_error("Debes seleccionar un mandante.")
    if not fecha_inicio_raw:
        return _resultantes_error("Debes seleccionar una fecha de inicio.")

    try:
        fecha_inicio = datetime.strptime(fecha_inicio_raw, "%Y-%m-%d").date()
        fecha_fin = datetime.strptime(fecha_fin_raw, "%Y-%m-%d").date()
        if fecha_fin < fecha_inicio:
            return _resultantes_error("La fecha termino debe ser mayor o igual a la fecha inicio.")
    except ValueError:
        return _resultantes_error("Formato de fecha invalido (usa AAAA-MM-DD).")

    try:
        payload, filename, mimetype = build_resultante_file(mandante, fecha_inicio, fecha_fin)
        return send_file(
            io.BytesIO(payload),
            as_attachment=True,
            download_name=filename,
            mimetype=mimetype,
        )
    except ValueError as exc:
        return _resultantes_error(str(exc))
    except Exception as exc:
        return _resultantes_error(f"No se pudo generar la resultante: {exc}", status=500)
