from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pandas as pd

from services import resultantes_repo
from utils.excel_export import df_to_xlsx_bytes


SUPPORTED_RESULTANTES_MANDANTES = [
    "TANNER",
    "BIT",
    "LA ARAUCANA",
    "SANTANDER CONSUMER",
    "PORSCHE",
    "GENERAL MOTORS",
]


TANNER_OUTPUT_FIELDS = [
    "datadocu",
    "rut",
    "columna3",
    "fecha",
    "respuesta_gestion",
    "observaciones",
    "columna7",
    "gestion_fecha",
    "gestion_hora",
    "usuario_gestion",
    "telefono",
    "email",
    "columna13",
    "columna14",
]

PORSCHE_OUTPUT_COLUMNS = [
    "Nombre de Agencia",
    "Nro Contrato",
    "Nombre de Cliente",
    "RUT",
    "Tramo de mora",
    "Tipo de Cobranza",
    "Fecha de Gestion",
    "Telefono",
    "Codigo de Accion",
    "Descripcion de Accion",
    "Codigo de Resultado",
    "Descripcion de Resultado",
    "Fecha de Agendamiento",
    "Comentario de Gestion",
    "Hora de Gestion",
]


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.strftime("%d-%m-%Y")
    return str(value).strip()


def _sanitize_field(value: Any) -> str:
    text = _as_text(value)
    return text.replace("\r", " ").replace("\n", " ").replace("|", "/")


def _build_tanner_txt(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""

    lines: list[str] = []
    for row in rows:
        values = [_sanitize_field(row.get(field, "")) for field in TANNER_OUTPUT_FIELDS]
        lines.append("|".join(values) + "|")

    return ("\n".join(lines) + "\n").encode("latin-1", errors="replace")


def _build_porsche_xlsx(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        df = pd.DataFrame(columns=PORSCHE_OUTPUT_COLUMNS)
    else:
        df = pd.DataFrame(rows)
        df = df.reindex(columns=PORSCHE_OUTPUT_COLUMNS)
    return df_to_xlsx_bytes(df, sheet_name="Gestiones")


def build_resultante_file(
    mandante: str,
    fecha_inicio: date,
    fecha_fin: date,
    modo: str = "rango",
) -> tuple[bytes, str, str]:
    mandante_key = (mandante or "").strip().upper()
    if mandante_key not in SUPPORTED_RESULTANTES_MANDANTES:
        raise ValueError("Mandante de resultantes no soportado.")

    fecha_tag = fecha_inicio.strftime("%Y%m%d")

    if mandante_key == "TANNER":
        rows = resultantes_repo.fetch_tanner_resultantes(fecha_inicio, fecha_fin)
        payload = _build_tanner_txt(rows)
        filename = f"{fecha_tag}_BaseGestiones2_200.txt"
        return payload, filename, "text/plain; charset=latin-1"

    if mandante_key == "PORSCHE":
        rows = resultantes_repo.fetch_porsche_resultantes(fecha_inicio, fecha_fin)
        payload = _build_porsche_xlsx(rows)
        filename = f"Gestiones_{fecha_fin.strftime('%Y%m%d')}.xlsx"
        return payload, filename, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    payload = b""
    filename = f"resultantes_{mandante_key.replace(' ', '_')}_{fecha_tag}.txt"
    return payload, filename, "text/plain; charset=utf-8"
