# utils/excel_export.py
import io
import zipfile
from typing import cast

import pandas as pd
from pandas._typing import WriteExcelBuffer

def df_to_xlsx_bytes(df: pd.DataFrame, sheet_name: str = "Hoja1", header: bool = True) -> bytes:
    bio = io.BytesIO()
    excel_buffer = cast(WriteExcelBuffer, bio)
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name, header=header)
    return bio.getvalue()

def df_to_xlsx_bytesio(df: pd.DataFrame, sheet_name: str = "Hoja1", header: bool = True) -> io.BytesIO:
    bio = io.BytesIO(df_to_xlsx_bytes(df, sheet_name, header=header))
    bio.seek(0)
    return bio

def zip_named_dfs_bytes(named_dfs: list[tuple[str, pd.DataFrame]]) -> io.BytesIO:
    """
    named_dfs: [(filename.xlsx, dataframe), ...]
    """
    zip_bio = io.BytesIO()
    with zipfile.ZipFile(zip_bio, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for filename, df in named_dfs:
            zf.writestr(filename, df_to_xlsx_bytes(df, sheet_name="Hoja1"))
    zip_bio.seek(0)
    return zip_bio

def zip_two_excels_bytes(a, b) -> io.BytesIO:
    """
    a = (filename, df, sheet_name)
    b = (filename, df, sheet_name)
    """
    zip_bio = io.BytesIO()
    with zipfile.ZipFile(zip_bio, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(a[0], df_to_xlsx_bytes(a[1], a[2]))
        zf.writestr(b[0], df_to_xlsx_bytes(b[1], b[2]))
    zip_bio.seek(0)
    return zip_bio
