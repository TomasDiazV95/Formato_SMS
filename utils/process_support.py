from __future__ import annotations

from pathlib import Path
import os
from typing import Iterable

import pandas as pd


class ProcessError(ValueError):
    def __init__(
        self,
        module: str,
        stage: str,
        message: str,
        *,
        detail: str | None = None,
        status: int = 400,
        error_type: str = "input",
    ) -> None:
        self.module = module
        self.stage = stage
        self.message = message
        self.detail = detail
        self.status = status
        self.error_type = error_type
        super().__init__(self.to_user_message())

    def to_user_message(self) -> str:
        prefix = f"[{self.module} | {self.stage}] {self.message}"
        if self.detail:
            return f"{prefix} Detalle: {self.detail}"
        return prefix


def format_column_list(columns: Iterable[object], *, limit: int = 18) -> str:
    values = [str(col).strip() for col in columns if str(col).strip()]
    if not values:
        return "(sin columnas detectadas)"
    preview = values[:limit]
    text = ", ".join(preview)
    if len(values) > limit:
        text += f" ... (+{len(values) - limit} más)"
    return text


def format_alias_map(field_map: dict[str, set[str]]) -> str:
    if not field_map:
        return ""
    parts: list[str] = []
    for logical_name, aliases in field_map.items():
        alias_list = ", ".join(sorted(aliases))
        parts.append(f"{logical_name} ({alias_list})")
    return "; ".join(parts)


def raise_missing_columns(
    *,
    module: str,
    stage: str,
    df: pd.DataFrame,
    missing_fields: list[str],
    alias_map: dict[str, set[str]] | None = None,
) -> None:
    detail_parts = [f"Columnas detectadas: {format_column_list(df.columns)}"]
    if alias_map:
        selected = {field: alias_map[field] for field in missing_fields if field in alias_map}
        if selected:
            detail_parts.append(f"Encabezados aceptados: {format_alias_map(selected)}")
    raise ProcessError(
        module,
        stage,
        f"Faltan columnas requeridas: {', '.join(missing_fields)}.",
        detail=" | ".join(detail_parts),
        status=400,
        error_type="input",
    )


def read_excel_or_raise(file_storage, *, module: str, stage: str = "Lectura Excel") -> pd.DataFrame:
    filename = getattr(file_storage, "filename", "") or "(sin nombre)"
    try:
        df = pd.read_excel(file_storage, dtype=str)
    except Exception as exc:
        raise ProcessError(
            module,
            stage,
            "No se pudo leer el archivo Excel.",
            detail=f"Archivo: {filename}. Error original: {exc}",
            status=400,
            error_type="input",
        ) from exc

    if df.empty:
        raise ProcessError(
            module,
            stage,
            "El archivo Excel está vacío.",
            detail=f"Archivo: {filename}",
            status=400,
            error_type="input",
        )

    return df


def ensure_env_vars(module: str, stage: str, env_keys: Iterable[str]) -> None:
    missing = [key for key in env_keys if not (os.getenv(key) or "").strip()]
    if missing:
        raise ProcessError(
            module,
            stage,
            "Faltan variables de entorno requeridas.",
            detail=", ".join(missing),
            status=500,
            error_type="config",
        )


def ensure_paths_exist(module: str, stage: str, required_paths: Iterable[Path]) -> None:
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        raise ProcessError(
            module,
            stage,
            "Faltan archivos requeridos del proceso.",
            detail=", ".join(missing),
            status=500,
            error_type="config",
        )
