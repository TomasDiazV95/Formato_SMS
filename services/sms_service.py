# services/sms_service.py
import pandas as pd
from datetime import datetime, timedelta, date, time

REQUIRED_COLUMNS = {"RUT", "OP", "FONO"}

def build_outputs(df: pd.DataFrame, mensaje: str, usuario: str):
    # Normaliza columnas esperadas
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas en el Excel: {', '.join(sorted(missing))}")

    # Copia para no mutar el original
    df = df.copy()

    # Inputs -> columnas
    df["MENSAJE"] = mensaje
    df["USERNAME"] = usuario

    # FONO_2: "56" + FONO como string (asegurando sin .0 si venía como número)
    df["FONO"] = df["FONO"].astype(str).str.replace(r"\.0$", "", regex=True)
    df["FONO_2"] = "56" + df["FONO"]

    # ---------------------------
    # Carga CRM
    # ---------------------------
    cargaCRM_df = pd.DataFrame(columns=[
        "RUT", "NRO_DOCUMENTO", "FECHA_GESTION", "TELEFONO",
        "OBSERVACION", "USUARIO", "CORREO"
    ])

    df1 = df[["RUT", "OP", "FONO", "USERNAME"]].rename(columns={
        "OP": "NRO_DOCUMENTO",
        "FONO": "TELEFONO",
        "USERNAME": "USUARIO"
    })

    cargaCRM_df = pd.concat([cargaCRM_df, df1], ignore_index=True)
    cargaCRM_df["OBSERVACION"] = "ACCIONES COMERCIALES"

    # Fecha de gestión: hoy a las 10:00:00
    fecha_gestion = datetime.combine(date.today(), time(10, 0, 0))
    cargaCRM_df["FECHA_GESTION"] = fecha_gestion

    # Asegurar NRO_DOCUMENTO como texto
    cargaCRM_df["NRO_DOCUMENTO"] = cargaCRM_df["NRO_DOCUMENTO"].astype(str)

    cargaCRM_df["CORREO"] = " "

    # ---------------------------
    # Carga Athenas
    # ---------------------------
    cargaAthenas_df = pd.DataFrame(columns=[
        "TELEFONO", "MENSAJE", "ID_CLIENTE (RUT)", "OPCIONAL",
        "CAMPO1", "CAMPO2", "CAMPO3"
    ])

    df2 = df[["RUT", "FONO_2", "MENSAJE"]].rename(columns={
        "FONO_2": "TELEFONO",
        "RUT": "ID_CLIENTE (RUT)"
    })

    cargaAthenas_df = pd.concat([cargaAthenas_df, df2], ignore_index=True)
    cargaAthenas_df["OPCIONAL"] = " "
    cargaAthenas_df["CAMPO1"] = " "
    cargaAthenas_df["CAMPO2"] = " "
    cargaAthenas_df["CAMPO3"] = " "

    return cargaCRM_df, cargaAthenas_df