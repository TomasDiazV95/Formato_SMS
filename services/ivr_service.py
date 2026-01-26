
import pandas as pd
from datetime import datetime, timedelta, date, time
import io

# Opciones para el select del front
CAMPO1_CHOICES = [
    ("ITAÚ VENCIDA",         "PHOENIXIVRITAUVENCIDA"),
    ("ITAÚ CASTIGO",         "PHOENIXIVRITAUCASTIGO"),
    ("CAJA 18",              "PHOENIXIVRCAJA18_3"),
    ("BANCO INTERNACIONAL",  "PHOENIX_BINTERNACIONAL"),
    ("SANTANDER HIPOTECARIO","PHOENIXIVRSANTANDERHIPO"),
    ("SANTANDER CONSUMER",   "PHOENIXSC_ICOMERCIAL"),
    ("GENERAL MOTORS",       "PHOENIXGMPREJUDICIAL"),
]

POSSIBLE_NAMES = {
    "TELEFONO": {"telefono", "teléfono", "fono", "celular", "movil", "móvil", "telefono1"},
    "RUT": {"rut", "id_cliente", "id cliente", "id_cliente (rut)", "id cliente (rut)"},
    "OP": {"op", "operacion", "operación", "nro_documento", "nro documento", "documento", "operacion1"},
    "NOMBRE": {"nombre", "name", "cliente", "contacto"}
}

def _pick_col(df: pd.DataFrame, logical_name: str) -> str | None:
    """Devuelve el nombre real de la columna que matchea el logical_name usando sinónimos."""
    targets = {s.lower().strip() for s in POSSIBLE_NAMES.get(logical_name, set())}
    for col in df.columns:
        key = str(col).lower().strip()
        if key in targets:
            return col
    return None

def _as_text(series: pd.Series) -> pd.Series:
    """Normaliza a texto, quita sufijo '.0' y espacios laterales."""
    return series.astype(str).str.replace(r"\.0$", "", regex=True).str.strip()

def _parse_hora(s: str) -> time:
    """Parsea hora HH:MM o HH:MM:SS."""
    s = (s or "").strip()
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(s, fmt).time()
        except ValueError:
            pass
    raise ValueError("Formato de hora inválido (usa HH:MM o HH:MM:SS).")


def _generate_schedule(n: int, fecha: date, hora_inicio: str, hora_fin: str, intervalo_segundos: int | None) -> list[str]:
    """
    Genera una lista de timestamps 'YYYY-MM-DD HH:MM:SS' para n registros,
    dentro del rango [inicio, fin]. Si intervalo es None, se auto-ajusta para que quepan todos.
    """
    t_ini = _parse_hora(hora_inicio)
    t_fin = _parse_hora(hora_fin)
    dt_ini = datetime.combine(fecha, t_ini)
    dt_fin = datetime.combine(fecha, t_fin)
    if dt_fin <= dt_ini:
        raise ValueError("La hora fin debe ser mayor a la hora inicio.")
    rango_seg = int((dt_fin - dt_ini).total_seconds())
    if n <= 0:
        return []
    if intervalo_segundos is not None and intervalo_segundos > 0:
        capacidad = rango_seg // intervalo_segundos + 1  # incluye el inicio
        if n > capacidad:
            raise ValueError(
                f"El rango {hora_inicio}–{hora_fin} no alcanza para {n} registros con intervalo de {intervalo_segundos}s "
                f"(capacidad: {capacidad}). Ajusta el intervalo o amplía el rango."
            )
        step = intervalo_segundos
    else:
        # Auto-ajuste: distribución homogénea para que entren todos
        step = 1 if n == 1 else max(1, rango_seg // (n - 1))
    schedule = [dt_ini + timedelta(seconds=i * step) for i in range(n)]
    schedule = [min(dt, dt_fin) for dt in schedule]  # no pasar la hora fin
    return [dt.strftime("%Y-%m-%d %H:%M:%S") for dt in schedule]


def build_ivr_output(df: pd.DataFrame, campo1_value: str) -> pd.DataFrame:
    base = df.copy()
    tel_col = _pick_col(base, "TELEFONO")
    rut_col = _pick_col(base, "RUT")
    op_col  = _pick_col(base, "OP")
    nom_col = _pick_col(base, "NOMBRE")
    if not tel_col:
        raise ValueError("Falta columna de TELEFONO (acepta: Telefono, Teléfono, Fono, Celular, Móvil).")

    telefono = _as_text(base[tel_col])
    rut      = _as_text(base[rut_col]) if rut_col else pd.Series([""] * len(base), index=base.index)
    oper     = _as_text(base[op_col])  if op_col  else pd.Series([""] * len(base), index=base.index)

    # ---- Cambio solicitado: MENSAJE = nombre si existe; si no existe o viene vacío por fila, usar RUT ----
    if nom_col:
        nombre = _as_text(base[nom_col])
        # Fallback por fila: si nombre queda vacío, usar RUT
        nombre = nombre.where(nombre.str.len() > 0, rut)
    else:
        # Si no existe columna de nombre, usar directamente el RUT
        nombre = rut

    final_cols = ["TELEFONO", "MENSAJE", "ID_CLIENTE", "", "OPCIONAL", "CAMPO1", "CAMPO2"]
    out = pd.DataFrame(columns=final_cols)
    out["TELEFONO"]   = "56" + telefono
    out["MENSAJE"]    = nombre
    out["ID_CLIENTE"] = rut
    out[""]           = ""
    out["OPCIONAL"]   = oper
    out["CAMPO1"]     = campo1_value
    out["CAMPO2"]     = ""
    return out

def build_crm_output(df: pd.DataFrame, fecha: date, hora_inicio: str, hora_fin: str, usuario_value: str, intervalo_segundos: int | None) -> pd.DataFrame:
    base = df.copy()
    tel_col = _pick_col(base, "TELEFONO")
    rut_col = _pick_col(base, "RUT")
    op_col  = _pick_col(base, "OP")  # NRO_DOCUMENTO
    faltantes = []
    if not rut_col: faltantes.append("RUT")
    if not op_col:  faltantes.append("NRO_DOCUMENTO/OP")
    if not tel_col: faltantes.append("TELEFONO")
    if faltantes:
        raise ValueError("Faltan columnas requeridas en el Excel base: " + ", ".join(faltantes))
    rut      = _as_text(base[rut_col])
    nro_doc  = _as_text(base[op_col])
    telefono = _as_text(base[tel_col])
    n = len(base)
    fechas = _generate_schedule(n, fecha, hora_inicio, hora_fin, intervalo_segundos)
    out_cols = ["RUT", "NRO_DOCUMENTO", "FECHA_GESTION", "TELEFONO", "OBSERVACION", "USUARIO", "CORREO"]
    out = pd.DataFrame(columns=out_cols, index=base.index)
    out["RUT"]            = rut
    out["NRO_DOCUMENTO"]  = nro_doc
    out["FECHA_GESTION"]  = fechas
    out["TELEFONO"]       = telefono       # tal cual origen (sin 56)
    out["OBSERVACION"]    = "IVR"
    out["USUARIO"]        = usuario_value
    out["CORREO"]         = " "            # espacio para no vacío
    return out
