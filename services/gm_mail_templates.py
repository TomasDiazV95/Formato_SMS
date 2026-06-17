from __future__ import annotations

from functools import lru_cache
from typing import Any

from services.config_store import read_json

CONFIG_FILENAME = "gm_mail_templates.json"


@lru_cache(maxsize=1)
def list_gm_mail_templates() -> list[dict[str, Any]]:
    data = read_json(CONFIG_FILENAME, default=[])
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def get_gm_mail_template(key: str) -> dict[str, Any] | None:
    key = (key or "").strip()
    for item in list_gm_mail_templates():
        if item.get("key") == key:
            return item
    return None


def get_default_gm_mail_template() -> dict[str, Any]:
    templates = list_gm_mail_templates()
    if not templates:
        raise ValueError("No hay plantillas GM Mail configuradas.")
    return templates[0]
