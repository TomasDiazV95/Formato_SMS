from __future__ import annotations

import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd

from repositories import ejecutivos_repo
from services import config_store
from utils.paths import PROJECT_ROOT, archive_path, config_path


ITAU_SMS_DIRS = [
    archive_path("sms_itau_vencida_txt"),
    PROJECT_ROOT / "SMS_ITAU_VENCIDA",
]
ITAU_SMS_CONFIG_PATH = config_path("sms_itau_vencida.json")

ITAU_SMS_TEMPLATE_FILES = {
    "MOROSIDAD": "SMS NORMAL-MOROSIDAD.txt",
    "COMPROMISO_PAGO": "SMS VIGENTE-COMPROMISO DE PAGO.txt",
    "COMPROMISO_ROTO": "SMS VENCIDO-COMPROMISO ROTO.txt",
    "CAMPANA": "SMS CAMPANA.txt",
}

ITAU_SEED_FILE = "SEMILLA ITAU VENCIDA.txt"

ITAU_MASIVIDAD_TO_TEMPLATE = {
    "SMS MOROSIDAD": "MOROSIDAD",
    "SMS COMPROMISO DE PAGO": "COMPROMISO_PAGO",
    "SMS COMPROMISO ROTO": "COMPROMISO_ROTO",
    "SMS CAMPANA": "CAMPANA",
    "SMS CAMPAÑA": "CAMPANA",
}


def _normalize_key(value: str) -> str:
    return (
        (value or "")
        .strip()
        .lower()
        .replace(" ", "")
        .replace("_", "")
        .replace("-", "")
    )


def normalize_spaces(value: str) -> str:
    return " ".join((value or "").split()).strip()


def ascii_fold(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    return text.encode("ascii", "ignore").decode("ascii")


def filename_token(value: str) -> str:
    text = ascii_fold(normalize_spaces(value))
    text = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")
    return text or "MANDANTE"


def _find_first_column(df: pd.DataFrame, aliases: set[str]) -> str | None:
    normalized = {_normalize_key(col): col for col in df.columns}
    for alias in aliases:
        key = _normalize_key(alias)
        if key in normalized:
            return normalized[key]
    return None


def _find_itau_sms_file(filename: str) -> Path | None:
    for directory in ITAU_SMS_DIRS:
        path = directory / filename
        if path.exists():
            return path
    return None


def load_itau_sms_config() -> dict | None:
    if not ITAU_SMS_CONFIG_PATH.exists():
        return None
    try:
        config = config_store.read_json("sms_itau_vencida.json")
    except (OSError, json.JSONDecodeError):
        return None
    return config if isinstance(config, dict) else None


def _itau_masividad_to_template_from_config(config: dict | None) -> dict[str, str]:
    if not config:
        return ITAU_MASIVIDAD_TO_TEMPLATE
    mapping: dict[str, str] = {}
    templates = config.get("templates") or {}
    if not isinstance(templates, dict):
        return ITAU_MASIVIDAD_TO_TEMPLATE
    for template_key, item in templates.items():
        if not isinstance(item, dict):
            continue
        for value in item.get("masividad_values") or []:
            normalized = ascii_fold(normalize_spaces(str(value))).upper()
            normalized = re.sub(r"\s+", " ", normalized)
            if normalized:
                mapping[normalized] = str(template_key).strip().upper()
    return mapping or ITAU_MASIVIDAD_TO_TEMPLATE


def _normalize_contact_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if not digits:
        return ""
    if digits.startswith("56"):
        return f"+{digits}"
    if digits.startswith("0"):
        digits = digits.lstrip("0")
    return f"+56{digits}"


def load_itau_sms_template(tipo_sms: str) -> str:
    template_key = (tipo_sms or "").strip().upper()
    config = load_itau_sms_config()
    if config:
        item = (config.get("templates") or {}).get(template_key) or {}
        text = str(item.get("message") or "").strip() if isinstance(item, dict) else ""
        if text:
            return text

    filename = ITAU_SMS_TEMPLATE_FILES.get(template_key)
    if not filename:
        raise ValueError("Tipo de SMS Itaú no soportado.")
    file_path = _find_itau_sms_file(filename)
    if not file_path:
        raise ValueError(f"No se encontró la plantilla Itaú: {filename}")
    text = file_path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"La plantilla Itaú está vacía: {filename}")
    return text


def _strip_trailing_phone(template_text: str) -> str:
    without_phone = re.sub(r"(?:\+?\d[\d\s\-()]{6,})\s*$", "", template_text or "").strip()
    return without_phone or (template_text or "").strip()


def _resolve_itau_phone(mandante: str, carterizado_name: str) -> str:
    raw = normalize_spaces(carterizado_name)
    if not raw:
        return ""

    candidates = [
        raw,
        raw.lower(),
        raw.upper(),
        ascii_fold(raw),
        ascii_fold(raw).lower(),
        ascii_fold(raw).upper(),
    ]
    seen: set[str] = set()
    unique_candidates: list[str] = []
    for item in candidates:
        item = normalize_spaces(item)
        if item and item not in seen:
            seen.add(item)
            unique_candidates.append(item)

    for candidate in unique_candidates:
        ejecutivo = ejecutivos_repo.fetch_by_mandante_and_nombre(mandante, candidate)
        if ejecutivo and ejecutivo.telefono:
            phone = _normalize_contact_phone(ejecutivo.telefono)
            if phone:
                return phone

    target = ascii_fold(raw).lower().strip()
    if target:
        try:
            best_score = 0.0
            best_phone = ""
            for ejecutivo in ejecutivos_repo.list_ejecutivos(mandante=mandante, activos=True):
                options = [
                    ascii_fold(ejecutivo.nombre_mostrar or "").lower().strip(),
                    (ejecutivo.nombre_clave or "").replace("_", " ").lower().strip(),
                ]
                for option in options:
                    if not option:
                        continue
                    score = SequenceMatcher(None, target, option).ratio()
                    if score > best_score and ejecutivo.telefono:
                        best_score = score
                        best_phone = _normalize_contact_phone(ejecutivo.telefono)
            if best_score >= 0.92 and best_phone:
                return best_phone
        except Exception:
            pass
    return ""


def build_itau_carterizado_messages(df: pd.DataFrame, mandante: str) -> pd.Series:
    carterizado_col = _find_first_column(
        df,
        {"carterizado", "carterizado<", "agente", "ejecutivo", "nombre_agente", "nombre agente", "carterizado abril"},
    )
    if not carterizado_col:
        raise ValueError("No se encontró la columna CARTERIZADO/AGENTE en el Excel.")

    masividad_col = _find_first_column(df, {"masividad", "tipo_sms", "tipo sms", "gestion", "gestion"})
    if not masividad_col:
        raise ValueError("No se encontró la columna MASIVIDAD en el Excel de Itaú.")

    template_cache: dict[str, str] = {}
    config = load_itau_sms_config()
    masividad_to_template = _itau_masividad_to_template_from_config(config)

    def _normalize_masividad(value: str) -> str:
        text = ascii_fold(normalize_spaces(value)).upper()
        text = re.sub(r"\s+", " ", text)
        return text

    def _template_text_from_masividad(value: str) -> str:
        key = masividad_to_template.get(_normalize_masividad(value))
        if not key:
            return ""
        if key not in template_cache:
            template_cache[key] = _strip_trailing_phone(load_itau_sms_template(key))
        return template_cache[key]

    phones: list[str] = []
    templates: list[str] = []
    missing: list[str] = []
    invalid_masividades: list[str] = []

    raw_carterizados = df[carterizado_col].fillna("").astype(str).tolist()
    raw_masividades = df[masividad_col].fillna("").astype(str).tolist()
    for raw_name, raw_masividad in zip(raw_carterizados, raw_masividades):
        template_text = _template_text_from_masividad(raw_masividad)
        templates.append(template_text)
        if not template_text:
            invalid_masividades.append(normalize_spaces(raw_masividad) or "(vacío)")
            phones.append("")
            continue

        carterizado = normalize_spaces(raw_name)
        phone = _resolve_itau_phone(mandante, carterizado)
        phones.append(phone)
        if not phone:
            missing.append(carterizado or "(vacío)")

    if invalid_masividades:
        uniq_invalid = []
        for item in invalid_masividades:
            if item not in uniq_invalid:
                uniq_invalid.append(item)
        only_invalid = all(not t for t in templates)
        if only_invalid:
            raise ValueError(
                "No se encontraron valores de MASIVIDAD válidos para SMS Itaú. "
                f"Valores detectados: {', '.join(uniq_invalid[:8])}"
            )

    messages = [f"{tpl} {phone}".strip() if tpl and phone else "" for tpl, phone in zip(templates, phones)]
    if not any(messages):
        uniq = []
        for name in missing:
            if name not in uniq:
                uniq.append(name)
        preview = ", ".join(uniq[:8])
        extra = "" if len(uniq) <= 8 else f" ... (+{len(uniq) - 8} más)"
        raise ValueError(
            "No se encontró teléfono de ejecutivo para los carterizados del archivo. "
            f"Ejemplos: {preview}{extra}. Revisa ejecutivos_phoenix/alias para Itau Vencida."
        )
    return pd.Series(messages, index=df.index)


def _seed_type_from_message(message: str) -> str | None:
    text = ascii_fold(normalize_spaces(message)).upper()
    if not text:
        return None
    if "MORA" in text:
        return "MOROSIDAD"
    if "PROXIMO" in text and "VENC" in text:
        return "COMPROMISO_PAGO"
    if "PENDIENTE" in text:
        return "COMPROMISO_ROTO"
    return None


def load_itau_seed_rows() -> list[dict[str, str]]:
    config = load_itau_sms_config()
    if config and isinstance(config.get("seeds"), list):
        rows = []
        for item in config["seeds"]:
            if not isinstance(item, dict):
                continue
            seed_type = str(item.get("type") or "").strip().upper()
            phone_local = re.sub(r"\D", "", str(item.get("phone_local") or ""))
            message = normalize_spaces(str(item.get("message") or ""))
            if seed_type and phone_local and message:
                rows.append({
                    "seed_type": seed_type,
                    "phone_local": phone_local,
                    "message": message,
                })
        if rows:
            return rows

    seed_path = _find_itau_sms_file(ITAU_SEED_FILE)
    if not seed_path:
        return []

    rows: list[dict[str, str]] = []
    for raw_line in seed_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if "\t" in line:
            phone_raw, msg_raw = line.split("\t", 1)
        else:
            parts = line.split(maxsplit=1)
            if len(parts) < 2:
                continue
            phone_raw, msg_raw = parts[0], parts[1]
        digits = re.sub(r"\D", "", phone_raw or "")
        if not digits:
            continue
        seed_type = _seed_type_from_message(msg_raw)
        if not seed_type:
            continue
        rows.append({
            "seed_type": seed_type,
            "phone_local": digits,
            "message": normalize_spaces(msg_raw),
        })
    return rows


def prepend_itau_seed_rows(
    carga: pd.DataFrame,
    tipo_salida: str,
    mensaje_series: pd.Series,
) -> tuple[pd.DataFrame, int]:
    seeds = load_itau_seed_rows()
    if not seeds:
        return carga, 0

    target_types = {
        seed_type
        for seed_type in mensaje_series.fillna("").astype(str).map(_seed_type_from_message).tolist()
        if seed_type
    }
    if not target_types:
        return carga, 0

    selected = [row for row in seeds if row["seed_type"] in target_types]
    if not selected:
        return carga, 0

    base = carga.copy()
    if tipo_salida == "AXIA":
        if not base.empty and str(base.iloc[0].get("FONO", "")).strip() == "976900353":
            base = base.iloc[1:].copy()
        seed_df = pd.DataFrame(
            [{"FONO": row["phone_local"], "MENSAJE": row["message"]} for row in selected]
        )
        final_df = pd.concat([seed_df, base], ignore_index=True)
        return final_df, len(seed_df)

    if "ID_CLIENTE (RUT)" in base.columns:
        if not base.empty and str(base.iloc[0].get("ID_CLIENTE (RUT)", "")).strip().upper() == "PRB":
            base = base.iloc[1:].copy()
    seed_df = pd.DataFrame(
        [
            {
                "TELEFONO": f"56{row['phone_local']}",
                "MENSAJE": row["message"],
                "ID_CLIENTE (RUT)": "PRB",
                "OPCIONAL": " ",
                "CAMPO1": " ",
                "CAMPO2": " ",
                "CAMPO3": " ",
            }
            for row in selected
        ]
    )
    final_df = pd.concat([seed_df, base], ignore_index=True)
    return final_df, len(seed_df)
