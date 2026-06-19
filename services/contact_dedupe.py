from __future__ import annotations

import pandas as pd


def dedupe_by_column_keep_first(df: pd.DataFrame, column: str | None) -> pd.DataFrame:
    if not column or column not in df.columns or df.empty:
        return df

    keys = df[column].fillna("").astype(str).str.strip()
    duplicate_mask = keys.ne("") & keys.duplicated(keep="first")
    if not duplicate_mask.any():
        return df
    return df.loc[~duplicate_mask].copy()


def dedupe_by_column_keep_first_normalized(df: pd.DataFrame, column: str | None) -> pd.DataFrame:
    if not column or column not in df.columns or df.empty:
        return df

    keys = df[column].fillna("").astype(str).str.strip().str.lower()
    duplicate_mask = keys.ne("") & keys.duplicated(keep="first")
    if not duplicate_mask.any():
        return df
    return df.loc[~duplicate_mask].copy()
