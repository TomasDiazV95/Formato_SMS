
import pandas as pd
from datetime import datetime

from services.gm_masividad_service import construir_df_masividad

CAMP_COLS = ["campana_1","campana_2","campana_3","campana_4","campana_5"]

def asegurar_columnas_campana(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in CAMP_COLS:
        if col not in df.columns:
            df[col] = ""
    return df

def copiar_campanas_por_operacion(
    df_nuevo: pd.DataFrame,
    df_antiguo: pd.DataFrame,
    col_operacion: str = "Agreement Number "
) -> pd.DataFrame:
 
    df_nuevo = df_nuevo.copy()
    df_nuevo = asegurar_columnas_campana(df_nuevo)
    df_antiguo = asegurar_columnas_campana(df_antiguo)

    if col_operacion not in df_nuevo.columns:
        raise ValueError(f"El archivo nuevo no contiene la columna de operación: {col_operacion}")
    if col_operacion not in df_antiguo.columns:
        raise ValueError(f"El archivo antiguo no contiene la columna de operación: {col_operacion}")

    # Normaliza operación a string para evitar mismatch por números vs texto
    df_nuevo[col_operacion] = df_nuevo[col_operacion].astype(str).str.strip()
    df_antiguo[col_operacion] = df_antiguo[col_operacion].astype(str).str.strip()

    # Lookup desde antiguo (operación + campañas), sin duplicados por operación
    lookup = df_antiguo[[col_operacion] + CAMP_COLS].copy()
    lookup = lookup.drop_duplicates(subset=[col_operacion], keep="first")
    lookup = lookup.rename(columns={c: f"{c}_old" for c in CAMP_COLS})

    # Merge para traer campañas del antiguo como *_old
    merged = df_nuevo.merge(lookup, on=col_operacion, how="left")

    # Copia campañas: si hay valor en *_old, úsalo; si no, conserva el del nuevo
    for c in CAMP_COLS:
        merged[c] = merged[f"{c}_old"].combine_first(merged[c])
        merged.drop(columns=[f"{c}_old"], inplace=True)

    return merged

def procesar_gm(df_nuevo: pd.DataFrame, df_antiguo: pd.DataFrame | None, comparar: bool, masividades: bool):
    df_nuevo = asegurar_columnas_campana(df_nuevo)

    # Si comparas, copia campañas desde archivo anterior
    if comparar:
        if df_antiguo is None:
            raise ValueError("Activaste comparación pero no se recibió archivo anterior.")
        df_nuevo = copiar_campanas_por_operacion(df_nuevo, df_antiguo, col_operacion="Agreement Number ")

    fecha = datetime.now().strftime("%d-%m")

    named_dfs = []
    named_dfs.append((f"ARCHIVO_COLLECTION_{fecha}.xlsx", df_nuevo))

    if masividades:
        df_m = construir_df_masividad(df_nuevo)
        named_dfs.append((f"MASIVIDADES_GM_{fecha}.xlsx", df_m))

    return named_dfs
