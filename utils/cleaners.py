# utils/cleaners.py
import pandas as pd
import re

def rut_only_numbers(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    s = s.str.replace(".", "", regex=False)
    s = s.str.split("-").str[0]
    s = s.str.replace(r"\D+", "", regex=True)
    return s
