from __future__ import annotations

import pandas as pd

from services.constants import MANDANTE_SPECIAL_RULES, COLUMN_MAP


def _normalize_key(value: str) -> str:
    return (
        (value or "")
        .strip()
        .lower()
        .replace(" ", "")
        .replace("_", "")
        .replace("-", "")
    )


def _find_column(df: pd.DataFrame, logical: str) -> str | None:
    normalized = {_normalize_key(col): col for col in df.columns}
    logical_key = logical.lower()
    candidates = {logical_key}
    aliases = COLUMN_MAP.get(logical_key) or set()
    candidates |= {_normalize_key(alias) for alias in aliases}
    for candidate in candidates:
        if candidate in normalized:
            return normalized[candidate]
    return None


def apply_mandante_rules(df: pd.DataFrame, mandante_nombre: str | None) -> pd.DataFrame:
    if not mandante_nombre:
        return df
    rules = MANDANTE_SPECIAL_RULES.get(mandante_nombre.strip().lower())
    if not rules:
        return df

    df = df.copy()
    op_length = rules.get("op_length")
    if op_length:
        target_col = "OP" if "OP" in df.columns else _find_column(df, "operacion")
        if target_col:
            series = (
                df[target_col]
                .fillna("")
                .astype(str)
                .str.replace(r"\.0$", "", regex=True)
                .str.strip()
            )
            mask = series != ""
            series.loc[mask] = series.loc[mask].str.zfill(op_length)
            df[target_col] = series
    return df
