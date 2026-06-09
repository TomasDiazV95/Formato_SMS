from __future__ import annotations

from datetime import datetime

from flask import Blueprint, jsonify, request

from frontend import serve_react_app
from services import campo1_catalog, mail_templates
from services.constants import MANDANTE_CHOICES


backoffice_bp = Blueprint("backoffice", __name__)


@backoffice_bp.get("/backoffice/catalogos")
def backoffice_catalogos_page():
    return serve_react_app()


@backoffice_bp.get("/api/backoffice/catalogos")
def backoffice_catalogos_data():
    templates = [
        {
            "code": item.code,
            "label": item.label,
            "message_id": item.message_id,
            "institucion": item.institucion,
            "segmentoinstitucion": item.segmentoinstitucion,
            "mandante": item.mandante,
        }
        for item in mail_templates.MAIL_TEMPLATE_OPTIONS
    ]

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "warnings": [],
        "catalogs": {
            "mandantes": {
                "app_constants": MANDANTE_CHOICES,
            },
            "ivr_campo1": campo1_catalog.list_items(active_only=False),
            "mail_templates": templates,
        },
    }
    return jsonify(payload)


@backoffice_bp.get("/api/backoffice/campo1")
def backoffice_campo1_list():
    return jsonify({"items": campo1_catalog.list_items(active_only=False)})


@backoffice_bp.post("/api/backoffice/campo1")
def backoffice_campo1_create():
    payload = request.get_json(silent=True) or {}
    try:
        item = campo1_catalog.create_item(
            label=str(payload.get("label") or ""),
            value=str(payload.get("value") or ""),
            active=bool(payload.get("active", True)),
        )
        return jsonify({"item": item}), 201
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 400


@backoffice_bp.put("/api/backoffice/campo1/<int:item_id>")
def backoffice_campo1_update(item_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        item = campo1_catalog.update_item(
            item_id,
            label=payload.get("label") if "label" in payload else None,
            value=payload.get("value") if "value" in payload else None,
            active=payload.get("active") if "active" in payload else None,
        )
        return jsonify({"item": item})
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 400


@backoffice_bp.delete("/api/backoffice/campo1/<int:item_id>")
def backoffice_campo1_delete(item_id: int):
    try:
        campo1_catalog.delete_item(item_id)
        return jsonify({"ok": True})
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 404
