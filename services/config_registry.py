from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from services import config_store


@dataclass(frozen=True)
class ConfigFile:
    key: str
    label: str
    filename: str
    owner: str
    editable: bool = True


CONFIG_FILES: tuple[ConfigFile, ...] = (
    ConfigFile("mail_templates", "Plantillas Mail", "mail_templates.json", "Mail"),
    ConfigFile("gm_mail_templates", "Plantillas GM Mail", "gm_mail_templates.json", "GM Mail"),
    ConfigFile("mail_itau_vencida_seeds", "Semillas Mail Itau Vencida", "mail_itau_vencida_seeds.json", "Mail Itau"),
    ConfigFile("sms_itau_vencida", "SMS Itau Vencida", "sms_itau_vencida.json", "SMS Itau"),
    ConfigFile("santander_consumer_templates", "Templates Santander Consumer", "santander_consumer_templates.json", "Santander Consumer"),
    ConfigFile("santander_consumer_supervisors", "Supervisores Santander Consumer", "santander_consumer_supervisors.json", "Santander Consumer"),
)


def list_config_files() -> list[dict[str, Any]]:
    items = []
    for config in CONFIG_FILES:
        status = config_store.status(config.filename)
        items.append(
            {
                "key": config.key,
                "label": config.label,
                "filename": config.filename,
                "owner": config.owner,
                "editable": config.editable,
                "exists": status.exists,
                "valid_json": status.valid_json,
                "item_count": status.item_count,
                "error": status.error,
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
