from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from utils.paths import PROJECT_ROOT, archive_path, config_path


@dataclass(frozen=True)
class ConfigStatus:
    filename: str
    path: Path
    exists: bool
    valid_json: bool
    item_count: int
    error: str = ""


def _resolve_config_path(filename: str) -> Path:
    safe_name = filename.strip().replace("\\", "/")
    if not safe_name or safe_name.startswith("/") or ".." in safe_name.split("/"):
        raise ValueError("Nombre de archivo de configuracion invalido.")
    path = config_path(safe_name)
    try:
        path.relative_to(PROJECT_ROOT / "config")
    except ValueError as exc:
        raise ValueError("Ruta de configuracion fuera de config/.") from exc
    return path


def item_count(data: Any) -> int:
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        if "templates" in data and isinstance(data["templates"], dict):
            return len(data["templates"])
        return len(data)
    return 0


def read_json(filename: str, *, default: Any = None) -> Any:
    path = _resolve_config_path(filename)
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def status(filename: str) -> ConfigStatus:
    path = _resolve_config_path(filename)
    if not path.exists():
        return ConfigStatus(filename=filename, path=path, exists=False, valid_json=False, item_count=0)
    try:
        raw = read_json(filename)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return ConfigStatus(filename=filename, path=path, exists=True, valid_json=False, item_count=0, error=str(exc))
    return ConfigStatus(filename=filename, path=path, exists=True, valid_json=True, item_count=item_count(raw))


def write_json(filename: str, data: Any, *, backup: bool = True) -> Path:
    path = _resolve_config_path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    if backup and path.exists():
        backup_dir = archive_path("config_backups")
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"{path.name}.{timestamp}.bak"
        backup_path.write_bytes(path.read_bytes())

    payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
        os.replace(tmp_name, path)
    finally:
        tmp_path = Path(tmp_name)
        if tmp_path.exists():
            tmp_path.unlink()
    return path
