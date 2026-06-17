from __future__ import annotations

import json
import re
import sys

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.paths import config_path


def _load_json(filename: str):
    path = config_path(filename)
    if not path.exists():
        raise AssertionError(f"No existe {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _require_fields(item: dict, fields: list[str], *, label: str) -> None:
    missing = [field for field in fields if item.get(field) in (None, "")]
    if missing:
        raise AssertionError(f"{label} sin campos requeridos: {', '.join(missing)}")


def validate_mail_templates() -> None:
    items = _load_json("mail_templates.json")
    if not isinstance(items, list) or not items:
        raise AssertionError("mail_templates.json debe ser una lista no vacia")
    seen_codes = set()
    for item in items:
        if not isinstance(item, dict):
            raise AssertionError("mail_templates.json contiene un item no objeto")
        _require_fields(
            item,
            ["code", "label", "message_id", "institucion", "segmentoinstitucion", "mandante"],
            label="mail template",
        )
        if item["code"] in seen_codes:
            raise AssertionError(f"mail template duplicado: {item['code']}")
        seen_codes.add(item["code"])
        int(item["message_id"])


def validate_sms_itau() -> None:
    data = _load_json("sms_itau_vencida.json")
    templates = data.get("templates") if isinstance(data, dict) else None
    seeds = data.get("seeds") if isinstance(data, dict) else None
    if not isinstance(templates, dict) or not templates:
        raise AssertionError("sms_itau_vencida.json debe tener templates")
    if not isinstance(seeds, list) or not seeds:
        raise AssertionError("sms_itau_vencida.json debe tener seeds")
    for key, item in templates.items():
        if not isinstance(item, dict):
            raise AssertionError(f"template SMS invalido: {key}")
        _require_fields(item, ["message", "masividad_values"], label=f"template SMS {key}")
        if not isinstance(item["masividad_values"], list) or not item["masividad_values"]:
            raise AssertionError(f"template SMS sin masividades: {key}")
    for item in seeds:
        if not isinstance(item, dict):
            raise AssertionError("seed SMS invalida")
        _require_fields(item, ["type", "phone_local", "message"], label="seed SMS")
        if not re.fullmatch(r"\d{8,12}", str(item["phone_local"])):
            raise AssertionError(f"phone_local invalido: {item['phone_local']}")


def validate_mail_itau_seeds() -> None:
    items = _load_json("mail_itau_vencida_seeds.json")
    if not isinstance(items, list) or not items:
        raise AssertionError("mail_itau_vencida_seeds.json debe ser una lista no vacia")
    for item in items:
        if not isinstance(item, dict):
            raise AssertionError("seed Mail Itau invalida")
        if not any(str(value or "").strip() for value in item.values()):
            raise AssertionError("seed Mail Itau vacia")


def validate_santander_consumer() -> None:
    templates = _load_json("santander_consumer_templates.json")
    if not isinstance(templates, list) or not templates:
        raise AssertionError("santander_consumer_templates.json debe ser una lista no vacia")
    seen_keys = set()
    for item in templates:
        if not isinstance(item, dict):
            raise AssertionError("template Santander Consumer invalido")
        _require_fields(item, ["key", "label", "message_id"], label="template Santander Consumer")
        if item["key"] in seen_keys:
            raise AssertionError(f"template Santander duplicado: {item['key']}")
        seen_keys.add(item["key"])
        int(item["message_id"])

    supervisors = _load_json("santander_consumer_supervisors.json")
    for key in ["supervisor_regiones", "supervisor_rm"]:
        item = supervisors.get(key) if isinstance(supervisors, dict) else None
        if not isinstance(item, dict):
            raise AssertionError(f"falta {key}")
        _require_fields(item, ["name_from", "mail_from", "CORREO", "CELULAR"], label=key)


def main() -> None:
    validate_mail_templates()
    validate_sms_itau()
    validate_mail_itau_seeds()
    validate_santander_consumer()
    print("CONFIG_OK")


if __name__ == "__main__":
    main()
