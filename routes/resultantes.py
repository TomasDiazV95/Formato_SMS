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
    modo = (request.args.get("modo") or "rango").strip().lower()
    fecha_inicio_raw = (request.args.get("fecha_inicio") or request.args.get("fecha") or "").strip()
    fecha_fin_raw = (request.args.get("fecha_fin") or fecha_inicio_raw).strip()

    if not mandante:
        return _resultantes_error("Debes seleccionar un mandante.")
    if mandante.strip().upper() == "PORSCHE" and modo not in {"consolidado", "rango"}:
        return _resultantes_error("Modo inválido para Porsche. Usa consolidado o rango.")
    try:
        if mandante.strip().upper() == "PORSCHE" and modo == "consolidado":
            today = datetime.now().date()
            fecha_inicio = today.replace(day=1)
            fecha_fin = today
        else:
            if not fecha_inicio_raw:
                return _resultantes_error("Debes seleccionar una fecha de inicio.")
            fecha_inicio = datetime.strptime(fecha_inicio_raw, "%Y-%m-%d").date()
            fecha_fin = datetime.strptime(fecha_fin_raw, "%Y-%m-%d").date()
            if fecha_fin < fecha_inicio:
                return _resultantes_error("La fecha termino debe ser mayor o igual a la fecha inicio.")
    except ValueError:
        return _resultantes_error("Formato de fecha invalido (usa AAAA-MM-DD).")

    try:
        payload, filename, mimetype = build_resultante_file(mandante, fecha_inicio, fecha_fin, modo=modo)
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
