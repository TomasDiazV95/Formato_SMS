# services/mail_service.py
import pandas as pd
from datetime import datetime, timedelta, date, time

REQUIRED_COLUMNS = {
    "RUT": {"rut", "id_cliente", "id cliente"},
    "NOMBRE": {"nombre", "cliente", "contacto"},
    "OPERACION": {"operacion", "operación", "op", "nro_documento", "nro documento", "documento"},
    "MAIL": {"mail", "correo", "email", "e-mail"},
}

def _find_col(df: pd.DataFrame, logical: str) -> str | None:
    targets = {logical.lower()} | {alias.lower() for alias in REQUIRED_COLUMNS.get(logical, set())}
    for col in df.columns:
        key = str(col).strip().lower()
        if key in targets:
            return col
    return None


def _normalize_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.replace(r"\.0$", "", regex=True).str.strip()


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
    if n <= 0:
        return []

    step = intervalo_segundos if intervalo_segundos and intervalo_segundos > 0 else 5
    rango_seg = int((dt_fin - dt_ini).total_seconds())
    capacidad = rango_seg // step + 1
    if n > capacidad:
        raise ValueError(
            f"El rango {hora_inicio}-{hora_fin} no alcanza para {n} registros con intervalo de {step}s (capacidad: {capacidad})."
        )

    return [
        (dt_ini + timedelta(seconds=i * step)).strftime("%Y-%m-%d %H:%M:%S")
        for i in range(n)
    ]


def build_mail_crm_output(
    df: pd.DataFrame,
    fecha: date,
    hora_inicio: str,
    hora_fin: str,
    usuario_value: str,
    observacion_value: str,
    intervalo_segundos: int | None = None,
) -> pd.DataFrame:
    base = df.copy()
    rut_col = _find_col(base, "RUT")
    op_col = _find_col(base, "OPERACION")
    mail_col = _find_col(base, "MAIL")

    faltantes = [name for name, col in (("RUT", rut_col), ("OPERACION", op_col), ("MAIL", mail_col)) if col is None]
    if faltantes:
        raise ValueError("Faltan columnas requeridas en el Excel base: " + ", ".join(faltantes))

    rut = _normalize_series(base.loc[:, rut_col])
    operacion = _normalize_series(base.loc[:, op_col])
    correo = _normalize_series(base.loc[:, mail_col])

    fechas = _generate_schedule(len(base), fecha, hora_inicio, hora_fin, intervalo_segundos)

    out_cols = ["RUT", "NRO_DOCUMENTO", "FECHA_GESTION", "TELEFONO", "OBSERVACION", "USUARIO", "CORREO"]
    out = pd.DataFrame({col: pd.Series(dtype=object) for col in out_cols}, index=base.index)
    out["RUT"] = rut
    out["NRO_DOCUMENTO"] = operacion
    out["FECHA_GESTION"] = fechas
    out["TELEFONO"] = ""
    out["OBSERVACION"] = (observacion_value or "").strip()
    out["USUARIO"] = usuario_value
    out["CORREO"] = correo

    return out.reset_index(drop=True)
