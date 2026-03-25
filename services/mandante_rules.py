from __future__ import annotations

import pandas as pd

from services.constants import MANDANTE_SPECIAL_RULES


def apply_mandante_rules(df: pd.DataFrame, mandante_nombre: str | None) -> pd.DataFrame:
    if not mandante_nombre:
        return df
    rules = MANDANTE_SPECIAL_RULES.get(mandante_nombre.strip().lower())
    if not rules:
        return df

    df = df.copy()
    op_length = rules.get("op_length")
    if op_length and "OP" in df.columns:
        series = (
            df["OP"]
            .fillna("")
            .astype(str)
            .str.replace(r"\.0$", "", regex=True)
            .str.strip()
        )
        mask = series != ""
        series.loc[mask] = series.loc[mask].str.zfill(op_length)
        df["OP"] = series
    return df
