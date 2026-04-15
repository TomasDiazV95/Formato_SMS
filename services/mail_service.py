# services/mail_service.py
import pandas as pd
from datetime import datetime, timedelta, date, time

REQUIRED_COLUMNS = {
    "RUT": {"rut", "id_cliente", "id cliente"},
    "NOMBRE": {"nombre", "cliente", "contacto"},
    "OPERACION": {"operacion", "operación", "op", "ope", "oper", "nro_documento", "nro documento", "documento", "id_credito"},
    "MAIL": {"mail", "correo", "email", "e-mail", "dest_email", "dest_mail", "mail_cliente", "email_cliente"},
}

def _find_col(df: pd.DataFrame, logical: str, *, exclude_keywords: set[str] | None = None) -> str | None:
    exclude_keywords = {kw.lower() for kw in (exclude_keywords or set())}
    targets = {logical.lower()} | {alias.lower() for alias in REQUIRED_COLUMNS.get(logical, set())}
    for col in df.columns:
        key = str(col).strip().lower()
        if exclude_keywords and any(keyword in key for keyword in exclude_keywords):
            continue
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

    rango_seg = int((dt_fin - dt_ini).total_seconds())
    if n > (rango_seg + 1):
        raise ValueError(
            f"El rango {hora_inicio}-{hora_fin} no alcanza para {n} registros. "
            f"Con precision de segundos, la capacidad maxima es {rango_seg + 1}."
        )

    if n == 1:
        return [dt_ini.strftime("%Y-%m-%d %H:%M:%S")]

    span = (dt_fin - dt_ini).total_seconds()
    offsets = [int(round((span * i) / (n - 1))) for i in range(n)]
    return [
        (dt_ini + timedelta(seconds=offset)).strftime("%Y-%m-%d %H:%M:%S")
        for offset in offsets
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
    mail_col = _find_col(base, "MAIL", exclude_keywords={"agente"})

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


def sample_mail_crm_output() -> pd.DataFrame:
    sample_df = pd.DataFrame({
        "RUT": ["11.111.111-1", "22.222.222-2"],
        "OPERACION": ["OP123456", "OP654321"],
        "MAIL": ["cliente1@example.com", "cliente2@example.com"],
    })
    fecha = datetime.now().date()
    return build_mail_crm_output(
        df=sample_df,
        fecha=fecha,
        hora_inicio="09:00",
        hora_fin="10:00",
        usuario_value="demo_user",
        observacion_value="Mail CRM de ejemplo",
        intervalo_segundos=5,
    )
