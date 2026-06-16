from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from utils.paths import config_path


@dataclass(frozen=True)
class ConfigFile:
    key: str
    label: str
    filename: str
    owner: str
    editable: bool = True


CONFIG_FILES: tuple[ConfigFile, ...] = (
    ConfigFile("mail_templates", "Plantillas Mail", "mail_templates.json", "Mail"),
    ConfigFile("mail_itau_vencida_seeds", "Semillas Mail Itau Vencida", "mail_itau_vencida_seeds.json", "Mail Itau"),
    ConfigFile("sms_itau_vencida", "SMS Itau Vencida", "sms_itau_vencida.json", "SMS Itau"),
    ConfigFile("santander_consumer_templates", "Templates Santander Consumer", "santander_consumer_templates.json", "Santander Consumer"),
    ConfigFile("santander_consumer_supervisors", "Supervisores Santander Consumer", "santander_consumer_supervisors.json", "Santander Consumer"),
)


def _item_count(data: Any) -> int:
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        if "templates" in data and isinstance(data["templates"], dict):
            return len(data["templates"])
        return len(data)
    return 0


def list_config_files() -> list[dict[str, Any]]:
    items = []
    for config in CONFIG_FILES:
        path = config_path(config.filename)
        exists = path.exists()
        valid_json = False
        item_count = 0
        error = ""
        if exists:
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                valid_json = True
                item_count = _item_count(raw)
            except (OSError, json.JSONDecodeError) as exc:
                error = str(exc)
        items.append(
            {
                "key": config.key,
                "label": config.label,
                "filename": config.filename,
                "owner": config.owner,
                "editable": config.editable,
                "exists": exists,
                "valid_json": valid_json,
                "item_count": item_count,
                "error": error,
            }
        )
    return items


def config_warnings() -> list[str]:
    warnings = []
    for item in list_config_files():
        if not item["exists"]:
            warnings.append(f"No existe config/{item['filename']}")
        elif not item["valid_json"]:
            warnings.append(f"JSON invalido en config/{item['filename']}: {item['error']}")
    return warnings
