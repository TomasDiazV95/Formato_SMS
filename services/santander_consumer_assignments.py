from __future__ import annotations

import json
import unicodedata
from difflib import SequenceMatcher

import pandas as pd

from repositories import ejecutivos_repo
from services import config_store
from utils.paths import config_path


SC_EXECUTIVE_MANDANTE = "Santander Consumer Terreno"


def normalize_agent_text(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def ascii_fold(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return text.encode("ascii", "ignore").decode("ascii")


def token_key(value: object) -> str:
    parts = [part for part in ascii_fold(value).lower().split() if part]
    parts.sort()
    return " ".join(parts)


def resolve_ejecutivo(nombre: str, exec_cache: dict[str, ejecutivos_repo.Ejecutivo | None]) -> ejecutivos_repo.Ejecutivo | None:
    raw = normalize_agent_text(nombre)
    if not raw:
        return None

    cache_key = ascii_fold(raw).lower()
    if cache_key in exec_cache:
        return exec_cache[cache_key]

    candidates = [
        raw,
        raw.lower(),
        raw.upper(),
        ascii_fold(raw),
        ascii_fold(raw).lower(),
        ascii_fold(raw).upper(),
    ]

    found = None
    seen: set[str] = set()
    for candidate in candidates:
        candidate = normalize_agent_text(candidate)
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        found = ejecutivos_repo.fetch_by_mandante_and_nombre(SC_EXECUTIVE_MANDANTE, candidate)
        if found:
            break

    if not found:
        target = ascii_fold(raw).lower().strip()
        target_tokens = token_key(raw)
        best_match = None
        best_score = 0.0
        for ejecutivo in ejecutivos_repo.list_ejecutivos(mandante=SC_EXECUTIVE_MANDANTE, activos=True):
            options = [
                ascii_fold(ejecutivo.nombre_mostrar or "").lower().strip(),
                (ejecutivo.nombre_clave or "").replace("_", " ").lower().strip(),
                token_key(ejecutivo.nombre_mostrar or ""),
                token_key((ejecutivo.nombre_clave or "").replace("_", " ")),
            ]
            for option in options:
                if not option:
                    continue
                score = max(
                    SequenceMatcher(None, target, option).ratio(),
                    SequenceMatcher(None, target_tokens, option).ratio(),
                )
                if score > best_score:
                    best_score = score
                    best_match = ejecutivo
        found = best_match if best_match and best_score >= 0.92 else None

    exec_cache[cache_key] = found
    return found


_DEFAULT_SUPERVISOR_REGIONES = {
    "name_from": "Maricel Galvez",
    "mail_from": "mgalvez@info.phoenixserviceinfo.cl",
    "CORREO": "mgalvez@phoenixservice.cl",
    "CELULAR": "967581695",
}

_DEFAULT_SUPERVISOR_RM = {
    "name_from": "Juan Pablo Rios",
    "mail_from": "jrios@info.phoenixserviceinfo.cl",
    "CORREO": "jrios@phoenixservice.cl",
    "CELULAR": "972194298",
}


def load_supervisors() -> dict[str, dict[str, str]]:
    defaults = {
        "supervisor_regiones": _DEFAULT_SUPERVISOR_REGIONES,
        "supervisor_rm": _DEFAULT_SUPERVISOR_RM,
    }
    path = config_path("santander_consumer_supervisors.json")
    if not path.exists():
        return defaults

    try:
        raw = config_store.read_json("santander_consumer_supervisors.json")
        loaded = {}
        for key, fallback in defaults.items():
            item = raw.get(key) or {}
            loaded[key] = {
                field: str(item.get(field) or fallback[field]).strip()
                for field in fallback
            }
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return defaults
    return loaded


_SUPERVISORS = load_supervisors()
SUPERVISOR_REGIONES = _SUPERVISORS["supervisor_regiones"]
SUPERVISOR_RM = _SUPERVISORS["supervisor_rm"]


def apply_supervisor_override(df: pd.DataFrame, asignacion_mode: str) -> pd.DataFrame:
    mode = (asignacion_mode or "normal").strip().lower()
    if mode not in {"normal", "supervisor_regiones", "supervisor_rm"}:
        mode = "normal"
    if mode == "normal" or df.empty:
        return df

    out = df.copy()
    region_series = out["REGION"].fillna("").astype(str).str.strip().str.upper()
    is_rm = region_series.eq("REGION METROPOLITANA")

    if mode == "supervisor_regiones":
        mask = ~is_rm
        supervisor = SUPERVISOR_REGIONES
    else:
        mask = is_rm
        supervisor = SUPERVISOR_RM

    out.loc[mask, "name_from"] = supervisor["name_from"]
    out.loc[mask, "EJECUTIVO"] = supervisor["name_from"]
    out.loc[mask, "mail_from"] = supervisor["mail_from"]
    out.loc[mask, "CORREO"] = supervisor["CORREO"]
    out.loc[mask, "CELULAR"] = supervisor["CELULAR"]
    return out
