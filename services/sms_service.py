# services/sms_service.py
import pandas as pd
from datetime import datetime, date, time, timedelta

REQUIRED_COLUMNS = {"RUT", "OP", "FONO"}
SEED_PHONE = "976900353"
SEED_PHONE_INTL = "56" + SEED_PHONE
SEED_ID = "PRB"


def _prepare_base_df(df: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas en el Excel: {', '.join(sorted(missing))}")

    base = df.copy()
    header_mask = (
        base["RUT"].astype(str).str.strip().str.upper().isin({"RUT", "ID", "ID_CLIENTE"})
        & base["OP"].astype(str).str.strip().str.upper().isin({"OP", "OPERACION", "OPERACIÓN", "NRO_DOCUMENTO"})
        & base["FONO"].astype(str).str.strip().str.upper().isin({"FONO", "TELEFONO", "TELÉFONO", "TELEFONO1"})
    )
    if header_mask.any():
        base = base.loc[~header_mask].copy()

    base["FONO"] = (
        base["FONO"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    )
    base["OP"] = base["OP"].astype(str).str.strip()
    base["FONO_2"] = "56" + base["FONO"]
    return base


def _parse_hora(value: str) -> time:
    value = (value or "").strip()
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    raise ValueError("Formato de hora inválido (usa HH:MM o HH:MM:SS).")


def _generate_schedule(n: int, fecha: date, hora_inicio: str, hora_fin: str, intervalo_segundos: int | None) -> list[str]:
    t_ini = _parse_hora(hora_inicio)
    t_fin = _parse_hora(hora_fin)
    dt_ini = datetime.combine(fecha, t_ini)
    dt_fin = datetime.combine(fecha, t_fin)
    if dt_fin <= dt_ini:
        raise ValueError("La hora fin debe ser mayor a la hora inicio.")
    rango_seg = int((dt_fin - dt_ini).total_seconds())
    if n <= 0:
        return []

    step = intervalo_segundos if intervalo_segundos and intervalo_segundos > 0 else 5
    capacidad = rango_seg // step + 1
    if n > capacidad:
        raise ValueError(
            f"El rango {hora_inicio}-{hora_fin} no alcanza para {n} registros con intervalo de {step}s (capacidad: {capacidad})."
        )

    schedule = [dt_ini + timedelta(seconds=i * step) for i in range(n)]
    return [dt.strftime("%Y-%m-%d %H:%M:%S") for dt in schedule]


def _build_crm_from_base(
    base: pd.DataFrame,
    usuario: str,
    fecha: date,
    hora_inicio: str,
    hora_fin: str,
    observacion: str,
    intervalo_segundos: int | None = None,
) -> pd.DataFrame:
    schedule = _generate_schedule(len(base), fecha, hora_inicio, hora_fin, intervalo_segundos)
    df1 = pd.DataFrame({
        "RUT": base["RUT"],
        "NRO_DOCUMENTO": base["OP"].astype(str),
        "FECHA_GESTION": schedule,
        "TELEFONO": base["FONO"],
        "OBSERVACION": observacion,
        "USUARIO": usuario,
        "CORREO": " ",
    })
    return df1.reset_index(drop=True)


def _build_athenas_from_base(base: pd.DataFrame, mensaje: str) -> pd.DataFrame:
    df2 = pd.DataFrame({
        "TELEFONO": base["FONO_2"],
        "MENSAJE": mensaje,
        "ID_CLIENTE (RUT)": base["RUT"],
        "OPCIONAL": " ",
        "CAMPO1": " ",
        "CAMPO2": " ",
        "CAMPO3": " ",
    })

    seed_row = pd.DataFrame([{
        "TELEFONO": SEED_PHONE_INTL,
        "MENSAJE": mensaje,
        "ID_CLIENTE (RUT)": SEED_ID,
        "OPCIONAL": " ",
        "CAMPO1": " ",
        "CAMPO2": " ",
        "CAMPO3": " ",
    }])

    df2 = pd.concat([seed_row, df2], ignore_index=True)
    return df2.reset_index(drop=True)


def build_axia_output(df: pd.DataFrame, mensaje: str) -> pd.DataFrame:
    base = _prepare_base_df(df)
    salida = pd.DataFrame({
        "FONO": base["FONO"],
        "MENSAJE": mensaje,
    })
    seed_row = pd.DataFrame([{"FONO": SEED_PHONE, "MENSAJE": mensaje}])
    salida = pd.concat([seed_row, salida], ignore_index=True)
    return salida.reset_index(drop=True)


def build_crm_output(
    df: pd.DataFrame,
    usuario: str,
    fecha: date,
    hora_inicio: str,
    hora_fin: str,
    observacion: str,
    intervalo_segundos: int | None = None,
) -> pd.DataFrame:
    base = _prepare_base_df(df)
    obs = (observacion or "").strip()
    return _build_crm_from_base(base, usuario, fecha, hora_inicio, hora_fin, obs, intervalo_segundos)


def build_athenas_output(df: pd.DataFrame, mensaje: str) -> pd.DataFrame:
    base = _prepare_base_df(df)
    return _build_athenas_from_base(base, mensaje)


def build_outputs(df: pd.DataFrame, mensaje: str, usuario: str):
    base = _prepare_base_df(df)
    today = date.today()
    crm = _build_crm_from_base(base, usuario, today, "10:00", "18:00", "ACCIONES COMERCIALES", None)
    return crm, _build_athenas_from_base(base, mensaje)


def sample_athenas_df() -> pd.DataFrame:
    data = {
        "TELEFONO": ["56987654321", "56911223344"],
        "MENSAJE": ["Hola Juan, recuerda tu pago hoy.", "Estimada Ana, tenemos una oferta."],
        "ID_CLIENTE (RUT)": ["11.111.111-1", "22.222.222-2"],
        "OPCIONAL": ["123456", "654321"],
        "CAMPO1": ["PROMO", "PROMO"],
        "CAMPO2": ["", ""],
        "CAMPO3": ["", ""],
    }
    df = pd.DataFrame(data)
    seed = pd.DataFrame({
        "TELEFONO": [SEED_PHONE_INTL],
        "MENSAJE": ["Ejemplo Athenas"],
        "ID_CLIENTE (RUT)": [SEED_ID],
        "OPCIONAL": [""],
        "CAMPO1": [""],
        "CAMPO2": [""],
        "CAMPO3": [""],
    })
    return pd.concat([seed, df], ignore_index=True)


def sample_axia_df() -> pd.DataFrame:
    data = {
        "FONO": ["56987654321", "56911223344"],
        "MENSAJE": ["Hola, esta es una muestra AXIA", "Probando layout AXIA"],
    }
    df = pd.DataFrame(data)
    seed = pd.DataFrame({"FONO": [SEED_PHONE], "MENSAJE": ["Ejemplo AXIA"]})
    return pd.concat([seed, df], ignore_index=True)
