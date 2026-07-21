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
    if "CAMPANA" not in templates:
        raise AssertionError("sms_itau_vencida.json debe incluir CAMPANA")
    if "SMS CAMPAÑA" not in templates["CAMPANA"].get("masividad_values", []):
        raise AssertionError("SMS Campaña debe aceptar MASIVIDAD SMS CAMPAÑA")
    campana_seeds = [item for item in seeds if isinstance(item, dict) and item.get("type") == "CAMPANA"]
    if len(campana_seeds) != 6:
        raise AssertionError("SMS Campaña debe tener 6 semillas")
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
    if "medios_pago" not in seen_keys:
        raise AssertionError("Santander Consumer debe incluir medios_pago")
    medios_pago = next(item for item in templates if item.get("key") == "medios_pago")
    if int(medios_pago.get("message_id")) != 85636:
        raise AssertionError("Santander Consumer medios_pago debe usar message_id 85636")

    supervisors = _load_json("santander_consumer_supervisors.json")
    for key in ["supervisor_regiones", "supervisor_rm"]:
        item = supervisors.get(key) if isinstance(supervisors, dict) else None
        if not isinstance(item, dict):
            raise AssertionError(f"falta {key}")
        _require_fields(item, ["name_from", "mail_from", "CORREO", "CELULAR"], label=key)


def validate_gm_mail_templates() -> None:
    templates = _load_json("gm_mail_templates.json")
    if not isinstance(templates, list) or not templates:
        raise AssertionError("gm_mail_templates.json debe ser una lista no vacia")
    seen_keys = set()
    base_columns = [
        "INSTITUCIÓN",
        "SEGMENTOINSTITUCIÓN",
        "message_id",
        "NOMBRE",
        "RUT",
        "OPERACION",
        "FECHA_VENCIMIENTO_CUOTA",
        "MONTO_CUOTA",
        "FECHA_ARCHIVO",
        "FONO_EJECUTIVA",
        "dest_email",
        "name_from",
        "mail_from",
        "CORREO_EJECUTIVA",
    ]
    extension_columns = base_columns[:9] + ["FECHA_ENTREGA"] + base_columns[9:]
    descuento_columns = base_columns[:8] + ["FECHA_VALIDA"] + base_columns[8:]
    expected_by_key = {
        "gm_comercial_84995": base_columns,
        "gm_extension_84591": extension_columns,
        "gm_descuento_98960": descuento_columns,
    }
    for item in templates:
        if not isinstance(item, dict):
            raise AssertionError("template GM Mail invalido")
        _require_fields(item, ["key", "label", "filename_prefix", "sheet_name"], label="template GM Mail")
        if item["key"] in seen_keys:
            raise AssertionError(f"template GM Mail duplicado: {item['key']}")
        seen_keys.add(item["key"])
        expected_columns = expected_by_key.get(item.get("key"))
        if item.get("columns") != expected_columns:
            raise AssertionError("GM Mail columnas inesperadas")
        fixed = item.get("fixed_values")
        if not isinstance(fixed, dict):
            raise AssertionError("GM Mail fixed_values invalido")
        _require_fields(
            fixed,
            ["INSTITUCIÓN", "SEGMENTOINSTITUCIÓN", "message_id", "FONO_EJECUTIVA", "name_from", "mail_from", "CORREO_EJECUTIVA"],
            label="GM Mail fixed_values",
        )
        int(fixed["message_id"])
        int(fixed["FONO_EJECUTIVA"])
        if item.get("key") == "gm_extension_84591" and fixed.get("message_id") != 84591:
            raise AssertionError("GM Extension debe usar message_id 84591")
        if item.get("key") == "gm_extension_84591" and not item.get("requires_delivery_date"):
            raise AssertionError("GM Extension debe requerir fecha entrega")
        if item.get("key") == "gm_descuento_98960" and fixed.get("message_id") != 98960:
            raise AssertionError("GM Descuento debe usar message_id 98960")
        if item.get("key") == "gm_descuento_98960" and item.get("date_field") != "FECHA_VALIDA":
            raise AssertionError("GM Descuento debe usar FECHA_VALIDA")
        if item.get("key") == "gm_descuento_98960" and not item.get("requires_delivery_date"):
            raise AssertionError("GM Descuento debe requerir fecha")
        seed_rows = item.get("seed_rows")
        if not isinstance(seed_rows, list) or len(seed_rows) != 2:
            raise AssertionError("GM Mail debe tener 2 semillas")
        expected_seeds = {
            "pipe5550@gmail.com": "1-1",
            "cfuentes@phoenixservice.cl": "1-2",
        }
        seen_seed_emails = set()
        for seed in seed_rows:
            if not isinstance(seed, dict):
                raise AssertionError("GM Mail semilla invalida")
            for field in ["NOMBRE", "RUT", "OPERACION", "MONTO_CUOTA", "dest_email"]:
                if seed.get(field) in (None, ""):
                    raise AssertionError(f"GM Mail semilla sin {field}")
            email = str(seed.get("dest_email") or "").strip().lower()
            seen_seed_emails.add(email)
            if expected_seeds.get(email) != seed.get("RUT"):
                raise AssertionError(f"GM Mail semilla con RUT inesperado: {email}")
            if seed.get("NOMBRE") != "PRB" or str(seed.get("OPERACION")) != "1234":
                raise AssertionError(f"GM Mail semilla neutral invalida: {email}")
        if seen_seed_emails != set(expected_seeds):
            raise AssertionError("GM Mail semillas requeridas incompletas")


def validate_sc_telefonia_mail_templates() -> None:
    templates = _load_json("sc_telefonia_mail_templates.json")
    if not isinstance(templates, list) or len(templates) != 3:
        raise AssertionError("sc_telefonia_mail_templates.json debe tener 3 plantillas")
    expected = {
        "sc_telefonia_descuento_95008": [
            "INSTITUCIÓN", "SEGMENTOINSTITUCIÓN", "message_id", "PLANTILLA", "RUT", "CLIENTE", "NRO_OPERACION", "dest_email", "name_from", "mail_from", "CORREO", "DIA", "MES", "ANO",
        ],
        "sc_telefonia_medios_pago_96706": [
            "INSTITUCIÓN", "SEGMENTOINSTITUCIÓN", "message_id", "PLANTILLA", "RUT", "NOMBRE", "N_OPERACION", "dest_email", "name_from", "mail_from", "CORREO",
        ],
        "sc_telefonia_novacion_93500": [
            "INSTITUCIÓN", "SEGMENTOINSTITUCIÓN", "message_id", "PLANTILLA", "RUT", "NOMBRE", "OPERACION", "dest_email", "name_from", "mail_from", "CORREO", "EJECU", "FONO_EJECUTIVO", "CORREO_EJE", "DIA", "MES", "ANO",
        ],
    }
    seen = set()
    for item in templates:
        if not isinstance(item, dict):
            raise AssertionError("template SC Telefonia invalido")
        _require_fields(item, ["key", "label", "filename_prefix", "sheet_name"], label="template SC Telefonia")
        key = item["key"]
        if key in seen:
            raise AssertionError(f"template SC Telefonia duplicado: {key}")
        seen.add(key)
        if item.get("columns") != expected.get(key):
            raise AssertionError(f"SC Telefonia columnas inesperadas: {key}")
        fixed = item.get("fixed_values")
        source_map = item.get("source_map")
        seed_rows = item.get("seed_rows")
        if not isinstance(fixed, dict) or not isinstance(source_map, dict):
            raise AssertionError(f"SC Telefonia config invalida: {key}")
        if not isinstance(seed_rows, list) or not seed_rows:
            raise AssertionError(f"SC Telefonia sin semillas: {key}")
        if len(seed_rows) != 1 or not isinstance(seed_rows[0], dict):
            raise AssertionError(f"SC Telefonia debe tener 1 semilla: {key}")
        seed = seed_rows[0]
        if str(seed.get("dest_email") or "").strip().lower() != "pipe5550@gmail.com":
            raise AssertionError(f"SC Telefonia debe tener solo semilla pipe5550: {key}")
        for field in ["RUT", "dest_email"]:
            if seed.get(field) in (None, ""):
                raise AssertionError(f"SC Telefonia semilla sin {field}: {key}")
        if key == "sc_telefonia_descuento_95008" and (not seed.get("CLIENTE") or not seed.get("NRO_OPERACION")):
            raise AssertionError("SC Telefonia descuento semilla incompleta")
        if key == "sc_telefonia_medios_pago_96706" and (not seed.get("NOMBRE") or not seed.get("N_OPERACION")):
            raise AssertionError("SC Telefonia medios pago semilla incompleta")
        if key == "sc_telefonia_novacion_93500" and (not seed.get("NOMBRE") or not seed.get("OPERACION")):
            raise AssertionError("SC Telefonia novacion semilla incompleta")
        int(fixed["message_id"])
        if key == "sc_telefonia_medios_pago_96706" and item.get("dedupe_columns") != ["RUT", "dest_email"]:
            raise AssertionError("SC Telefonia 96706 debe deduplicar por RUT y dest_email")
        if key == "sc_telefonia_novacion_93500":
            if not item.get("requires_executive") or fixed.get("FONO_EJECUTIVO") != 967280344:
                raise AssertionError("SC Telefonia novacion ejecutiva/fono invalido")


def main() -> None:
    validate_mail_templates()
    validate_gm_mail_templates()
    validate_sc_telefonia_mail_templates()
    validate_sms_itau()
    validate_mail_itau_seeds()
    validate_santander_consumer()
    print("CONFIG_OK")


if __name__ == "__main__":
    main()
