from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any


DEFAULT_CAMPO1_ITEMS = [
    {"label": "ITAU VENCIDA", "value": "PHOENIXIVRITAUVENCIDA", "active": True},
    {"label": "ITAU CASTIGO", "value": "PHOENIXIVRITAUCASTIGO", "active": True},
    {"label": "CAJA 18", "value": "PHOENIXIVRCAJA18_3", "active": True},
    {"label": "BANCO INTERNACIONAL", "value": "PHOENIX_BINTERNACIONAL", "active": True},
    {"label": "SANTANDER HIPOTECARIO", "value": "PHOENIXIVRSANTANDERHIPO", "active": True},
    {"label": "SANTANDER CONSUMER TERRENO", "value": "PHOENIXSC_ICOMERCIAL", "active": True},
    {"label": "SANTANDER CONSUMER TELEFONIA", "value": "PHOENIXSC_ICOMERCIAL", "active": True},
    {"label": "SANTANDER CONSUMER JUDICIAL", "value": "PHOENIXSC_ICOMERCIAL", "active": True},
    {"label": "GENERAL MOTORS", "value": "PHOENIXGMPREJUDICIAL", "active": True},
    {"label": "LA ARAUCANA", "value": "PHOENIXIVRARAUCANA", "active": True},
    {"label": "TANNER", "value": "PHOENIXTANNER_IVR", "active": True},
]


_CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "campo1_catalog.json"
_LOCK = threading.Lock()


def _clean_text(value: str) -> str:
    return " ".join(str(value or "").strip().split())


def _next_id(items: list[dict[str, Any]]) -> int:
    return max((int(item.get("id") or 0) for item in items), default=0) + 1


def _bootstrap_catalog() -> None:
    if _CATALOG_PATH.exists():
        return
    _CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    items = []
    for idx, row in enumerate(DEFAULT_CAMPO1_ITEMS, start=1):
        items.append(
            {
                "id": idx,
                "label": row["label"],
                "value": row["value"],
                "active": bool(row.get("active", True)),
            }
        )
    _CATALOG_PATH.write_text(json.dumps(items, ensure_ascii=True, indent=2), encoding="utf-8")


def _read_catalog() -> list[dict[str, Any]]:
    _bootstrap_catalog()
    raw = json.loads(_CATALOG_PATH.read_text(encoding="utf-8") or "[]")
    items: list[dict[str, Any]] = []
    for row in raw if isinstance(raw, list) else []:
        label = _clean_text(str(row.get("label") or ""))
        value = _clean_text(str(row.get("value") or ""))
        if not label or not value:
            continue
        items.append(
            {
                "id": int(row.get("id") or 0),
                "label": label,
                "value": value,
                "active": bool(row.get("active", True)),
            }
        )
    items.sort(key=lambda item: item["id"])
    return items


def _write_catalog(items: list[dict[str, Any]]) -> None:
    _CATALOG_PATH.write_text(json.dumps(items, ensure_ascii=True, indent=2), encoding="utf-8")


def list_items(*, active_only: bool = False) -> list[dict[str, Any]]:
    with _LOCK:
        items = _read_catalog()
    if active_only:
        return [item for item in items if item["active"]]
    return items


def list_choices(*, active_only: bool = True) -> list[tuple[str, str]]:
    items = list_items(active_only=active_only)
    return [(item["label"], item["value"]) for item in items]


def create_item(*, label: str, value: str, active: bool = True) -> dict[str, Any]:
    clean_label = _clean_text(label)
    clean_value = _clean_text(value)
    if not clean_label or not clean_value:
        raise ValueError("Label y value son obligatorios.")

    with _LOCK:
        items = _read_catalog()
        if any(item["label"].lower() == clean_label.lower() for item in items):
            raise ValueError("Ya existe un CAMPO1 con ese label.")
        item = {
            "id": _next_id(items),
            "label": clean_label,
            "value": clean_value,
            "active": bool(active),
        }
        items.append(item)
        _write_catalog(items)
        return item


def update_item(item_id: int, *, label: str | None = None, value: str | None = None, active: bool | None = None) -> dict[str, Any]:
    with _LOCK:
        items = _read_catalog()
        target = next((item for item in items if item["id"] == item_id), None)
        if not target:
            raise ValueError("CAMPO1 no encontrado.")

        if label is not None:
            clean_label = _clean_text(label)
            if not clean_label:
                raise ValueError("Label no puede estar vacio.")
            for item in items:
                if item["id"] != item_id and item["label"].lower() == clean_label.lower():
                    raise ValueError("Ya existe un CAMPO1 con ese label.")
            target["label"] = clean_label

        if value is not None:
            clean_value = _clean_text(value)
            if not clean_value:
                raise ValueError("Value no puede estar vacio.")
            target["value"] = clean_value

        if active is not None:
            target["active"] = bool(active)

        _write_catalog(items)
        return target


def delete_item(item_id: int) -> None:
    with _LOCK:
        items = _read_catalog()
        next_items = [item for item in items if item["id"] != item_id]
        if len(next_items) == len(items):
            raise ValueError("CAMPO1 no encontrado.")
        _write_catalog(next_items)
