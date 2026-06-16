from __future__ import annotations

import os
from datetime import date
from typing import Any, cast

from services.resultantes_queries.index import (
    PORSCHE_QUERY,
    TANNER_QUERY,
    build_porsche_params,
    build_tanner_params,
)
from utils.db_resultantes import get_resultantes_connection


Row = dict[str, Any]


def _resultantes_enabled() -> bool:
    return os.getenv("RESULT_DB_ENABLED", "0").lower() in {"1", "true", "yes"}


def fetch_tanner_resultantes(fecha_inicio: date, fecha_fin: date) -> list[Row]:
    """Consulta resultantes Tanner entre fechas (inclusive)."""
    if not _resultantes_enabled():
        return []

    cartera = int(os.getenv("RESULTANTES_TANNER_CARTERA", "519"))
    discador_user = (os.getenv("RESULTANTES_TANNER_DISCADOR_USER") or "VDAD").strip() or "VDAD"
    query = (os.getenv("RESULTANTES_TANNER_QUERY") or TANNER_QUERY).strip()
    params = build_tanner_params(
        cartera=cartera,
        discador_user=discador_user,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
    )

    with get_resultantes_connection() as conn:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(query, params)
            rows = cur.fetchall() or []
    return cast(list[Row], rows)


def fetch_porsche_resultantes(fecha_inicio: date, fecha_fin: date) -> list[Row]:
    if not _resultantes_enabled():
        return []

    cartera = int(os.getenv("RESULTANTES_PORSCHE_CARTERA", "528"))
    query = (os.getenv("RESULTANTES_PORSCHE_QUERY") or PORSCHE_QUERY).strip()
    params = build_porsche_params(cartera=cartera, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)
    cartera_sql, inicio_sql, fin_sql = params
    rendered_query = query
    rendered_query = rendered_query.replace("__CARTERA__", str(cartera_sql), 1)
    rendered_query = rendered_query.replace("__INICIO__", inicio_sql, 1)
    rendered_query = rendered_query.replace("__FIN__", fin_sql, 1)

    with get_resultantes_connection() as conn:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(rendered_query)
            rows = cur.fetchall() or []
    return cast(list[Row], rows)
