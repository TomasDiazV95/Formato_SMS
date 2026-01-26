# services/gm_masividad_service.py
import pandas as pd
from datetime import datetime
from itertools import cycle

from config import MASIVIDAD_COLUMNS, EJECUTIVOS, EMAIL_RE
from utils.cleaners import rut_only_numbers

def construir_df_masividad(df_nuevo: pd.DataFrame) -> pd.DataFrame:
    # Layout con espacios al final (tal como viene el Excel)
    required = ["National Id ", "Customer Name ", "Agreement Number ", "Due Date", "EMI", "Email "]
    missing = [c for c in required if c not in df_nuevo.columns]
    if missing:
        raise ValueError("Faltan columnas para masividades: " + ", ".join(missing))

    df_m = pd.DataFrame(index=df_nuevo.index, columns=MASIVIDAD_COLUMNS)

    df_m["RUT"] = rut_only_numbers(df_nuevo["National Id "])
    df_m["NOMBRE"] = df_nuevo["Customer Name "].astype(str).str.strip()
    df_m["OPERACION"] = df_nuevo["Agreement Number "].astype(str).str.strip()
    df_m["FECHA_VENCIMIENTO_CUOTA"] = df_nuevo["Due Date"]
    df_m["MONTO_CUOTA"] = df_nuevo["EMI"]
    df_m["dest_email"] = df_nuevo["Email "].astype(str).str.strip()

    hoy = datetime.now().strftime("%d-%m-%Y")
    df_m["FECHA_ENTREGA"] = hoy
    df_m["FECHA_ARCHIVO"] = hoy
    df_m["FECHA_VENCIMIENTO_CUOTA"] = pd.to_datetime(df_m["FECHA_VENCIMIENTO_CUOTA"], errors='coerce').dt.strftime("%d-%m-%Y")

    # Limpiezas
    df_m = df_m.dropna(subset=["dest_email"])
    df_m = df_m[df_m["dest_email"].astype(str).str.strip() != ""]
    df_m = df_m[df_m["dest_email"].astype(str).str.match(EMAIL_RE, na=False)]
    df_m = df_m[df_m["RUT"].astype(str).str.len() >= 7]
    df_m = df_m.drop_duplicates(subset=["RUT"], keep="first")

    # Fijos
    df_m["INSTITUCIÓN"] = "GENERAL MOTORS"
    df_m["SEGMENTOINSTITUCIÓN"] = "GENERAL MOTORS"
    df_m["message_id"] = 84995
    df_m["FONO_EJECUTIVA"] = 228400433

    # Ejecutivos
    cyc = cycle(EJECUTIVOS)
    asignados = [next(cyc) for _ in range(len(df_m))]
    df_m["name_from"] = [a["name_from"] for a in asignados]
    df_m["CORREO_EJECUTIVA"] = [a["CORREO_EJECUTIVA"] for a in asignados]
    df_m["mail_from"] = [a["mail_from"] for a in asignados]

    return df_m[MASIVIDAD_COLUMNS]
