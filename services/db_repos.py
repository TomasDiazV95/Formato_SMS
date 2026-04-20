"""MySQL repositories for logging masividades and fetching catalog data."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional, cast
from datetime import date, datetime
from decimal import Decimal

from utils.db import get_connection

RowDict = dict[str, Any]

@dataclass
class Mandante:
    id: int
    codigo: str
    nombre: str


@dataclass
class Proceso:
    id: int
    codigo: str
    descripcion: str
    tipo: str
    costo_unitario: float


def fetch_all_mandantes() -> list[Mandante]:
    query = "SELECT id, codigo, nombre FROM mandantes WHERE activo = 1 ORDER BY nombre"
    with get_connection() as conn:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(query)
            rows = cast(list[RowDict], cur.fetchall())
    return [Mandante(id=row["id"], codigo=row["codigo"], nombre=row["nombre"]) for row in rows]


def fetch_all_procesos() -> list[str]:
    query = "SELECT codigo FROM procesos WHERE activo = 1 ORDER BY codigo"
    with get_connection() as conn:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(query)
            rows = cast(list[RowDict], cur.fetchall())
    return [row["codigo"] for row in rows]


def fetch_mandantes_catalog() -> list[RowDict]:
    query = "SELECT id, codigo, nombre, activo FROM mandantes ORDER BY nombre"
    with get_connection() as conn:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(query)
            rows = cast(list[RowDict], cur.fetchall())
    return rows


def fetch_procesos_catalog() -> list[RowDict]:
    query = (
        "SELECT id, codigo, descripcion, tipo, costo_unitario, activo "
        "FROM procesos ORDER BY codigo"
    )
    with get_connection() as conn:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(query)
            rows = cast(list[RowDict], cur.fetchall())
    return rows


def fetch_mandante_by_nombre(nombre: str) -> Optional[Mandante]:
    query = "SELECT id, codigo, nombre FROM mandantes WHERE nombre = %s AND activo = 1 LIMIT 1"
    with get_connection() as conn:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(query, (nombre,))
            row = cur.fetchone()
            if not row:
                return None
            row_dict = cast(RowDict, row)
            return Mandante(id=row_dict["id"], codigo=row_dict["codigo"], nombre=row_dict["nombre"])


def fetch_proceso_by_codigo(codigo: str) -> Optional[Proceso]:
    query = (
        "SELECT id, codigo, descripcion, tipo, costo_unitario "
        "FROM procesos WHERE codigo = %s AND activo = 1 LIMIT 1"
    )
    with get_connection() as conn:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(query, (codigo,))
            row = cur.fetchone()
            if not row:
                return None
            row_dict = cast(RowDict, row)
            return Proceso(
                id=row_dict["id"],
                codigo=row_dict["codigo"],
                descripcion=row_dict["descripcion"],
                tipo=row_dict["tipo"],
                costo_unitario=float(row_dict["costo_unitario"]),
            )


def log_masividad(
    *,
    mandante_id: int,
    proceso_id: int,
    total_registros: int,
    costo_unitario: float,
    usuario_app: str,
    archivo_generado: Optional[str] = None,
    observacion: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> int:
    costo_total = total_registros * costo_unitario
    query = (
        "INSERT INTO masividades_log "
        "(mandante_id, proceso_id, total_registros, costo_unitario, costo_total, usuario_app, "
        " archivo_generado, observacion, metadata_json)"
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
    )
    metadata_json = json.dumps(metadata) if metadata else None
    params = (
        mandante_id,
        proceso_id,
        total_registros,
        costo_unitario,
        costo_total,
        usuario_app,
        archivo_generado,
        observacion,
        metadata_json,
    )
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            masividad_id: int = int(cur.lastrowid or 0)
        conn.commit()
    return masividad_id


def bulk_insert_masividad_detalle(
    *,
    masividad_log_id: int,
    proceso_codigo: str,
    mandante_nombre: str,
    registros: list[dict[str, Any]],
) -> None:
    if not registros:
        return

    query = (
        "INSERT INTO masividades_detalle "
        "(masividad_log_id, proceso_codigo, mandante_nombre, rut, telefono, mail, operacion, plantilla, mensaje, extra_json) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    )

    params = []
    for registro in registros:
        extra = registro.get("extra")
        params.append(
            (
                masividad_log_id,
                proceso_codigo,
                mandante_nombre,
                registro.get("rut"),
                registro.get("telefono"),
                registro.get("mail"),
                registro.get("operacion"),
                registro.get("plantilla"),
                registro.get("mensaje"),
                json.dumps(extra) if extra else None,
            )
        )

    chunk_size = 500
    with get_connection() as conn:
        with conn.cursor() as cur:
            for i in range(0, len(params), chunk_size):
                batch = params[i:i + chunk_size]
                cur.executemany(query, batch)
        conn.commit()


def fetch_masividades_detalle(
    *,
    mandante_nombre: str | None = None,
    proceso_codigo: str | None = None,
    fecha_inicio: datetime | None = None,
    fecha_fin: datetime | None = None,
    limit: int | None = 50000,
) -> list[RowDict]:
    query = (
        "SELECT md.id, md.mandante_nombre, md.proceso_codigo, md.rut, md.telefono, md.mail, md.operacion, md.plantilla, md.mensaje, md.extra_json, "
        "ml.fecha_ejecucion, ml.usuario_app, ml.archivo_generado "
        "FROM masividades_detalle md "
        "JOIN masividades_log ml ON md.masividad_log_id = ml.id"
    )
    conditions: list[str] = []
    params: list[Any] = []
    if mandante_nombre:
        conditions.append("md.mandante_nombre = %s")
        params.append(mandante_nombre)
    if proceso_codigo:
        conditions.append("md.proceso_codigo = %s")
        params.append(proceso_codigo)
    if fecha_inicio:
        conditions.append("ml.fecha_ejecucion >= %s")
        params.append(fecha_inicio)
    if fecha_fin:
        conditions.append("ml.fecha_ejecucion <= %s")
        params.append(fecha_fin)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY ml.fecha_ejecucion DESC, md.id DESC"
    if limit:
        query += " LIMIT %s"
        params.append(limit)

    with get_connection() as conn:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(query, params)
            rows = cast(list[RowDict], cur.fetchall())
    return rows


def fetch_process_history(*, usuario_app: str, limit: int = 20) -> list[RowDict]:
    query = (
        "SELECT ml.id, ml.total_registros, ml.archivo_generado, ml.fecha_ejecucion, "
        "p.codigo AS proceso_codigo, p.descripcion AS proceso_descripcion, "
        "m.nombre AS mandante_nombre "
        "FROM masividades_log ml "
        "JOIN procesos p ON ml.proceso_id = p.id "
        "JOIN mandantes m ON ml.mandante_id = m.id "
        "WHERE ml.usuario_app = %s "
        "ORDER BY ml.fecha_ejecucion DESC, ml.id DESC "
        "LIMIT %s"
    )

    safe_limit = max(1, min(limit, 100))
    with get_connection() as conn:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(query, (usuario_app, safe_limit))
            rows = cast(list[RowDict], cur.fetchall())
    return rows


def _build_cost_filters(
    *,
    mandante_nombre: str | None = None,
    proceso_codigo: str | None = None,
    fecha_inicio: datetime | None = None,
    fecha_fin: datetime | None = None,
) -> tuple[str, list[Any]]:
    filters: list[str] = []
    params: list[Any] = []
    if mandante_nombre:
        filters.append("m.nombre = %s")
        params.append(mandante_nombre)
    if proceso_codigo:
        filters.append("p.codigo = %s")
        params.append(proceso_codigo)
    if fecha_inicio:
        filters.append("ml.fecha_ejecucion >= %s")
        params.append(fecha_inicio)
    if fecha_fin:
        filters.append("ml.fecha_ejecucion <= %s")
        params.append(fecha_fin)
    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    return where_clause, params


def get_cost_summary(
    *,
    mandante_nombre: str | None = None,
    proceso_codigo: str | None = None,
    fecha_inicio: datetime | None = None,
    fecha_fin: datetime | None = None,
) -> dict[str, Any]:
    where_clause, params = _build_cost_filters(
        mandante_nombre=mandante_nombre,
        proceso_codigo=proceso_codigo,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
    )

    query = f"""
        SELECT
            p.codigo AS proceso,
            p.descripcion AS descripcion,
            SUM(ml.total_registros) AS total_registros,
            SUM(ml.costo_total) AS costo_total
        FROM masividades_log ml
        JOIN procesos p ON ml.proceso_id = p.id
        JOIN mandantes m ON ml.mandante_id = m.id
        {where_clause}
        GROUP BY p.id
        ORDER BY p.codigo
    """

    total_query = f"""
        SELECT
            SUM(ml.total_registros) AS total_registros,
            SUM(ml.costo_total) AS costo_total
        FROM masividades_log ml
        JOIN mandantes m ON ml.mandante_id = m.id
        {where_clause}
    """

    with get_connection() as conn:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(query, params)
            resumen = cast(list[RowDict], cur.fetchall())
            cur.execute(total_query, params)
            totales_row = cast(RowDict, cur.fetchone() or {"total_registros": 0, "costo_total": 0})

    for row in resumen:
        row["total_registros"] = int(row.get("total_registros") or 0)
        row["costo_total"] = _normalize_decimal(row.get("costo_total"))

    totales = {
        "total_registros": int(totales_row.get("total_registros") or 0),
        "costo_total": _normalize_decimal(totales_row.get("costo_total")),
    }

    return {
        "mandante": mandante_nombre,
        "proceso": proceso_codigo,
        "resumen_por_proceso": resumen,
        "totales": totales,
    }


def get_monthly_cost_trend(
    *,
    months: int = 12,
    mandante_nombre: str | None = None,
    proceso_codigo: str | None = None,
    end_year: int | None = None,
    end_month: int | None = None,
) -> list[RowDict]:
    safe_months = max(1, min(months, 24))
    if end_year is None or end_month is None:
        ref = datetime.now()
        end_year = ref.year
        end_month = ref.month

    end_period = date(end_year, end_month, 1)
    month_list: list[tuple[int, int]] = []
    cursor = end_period
    for _ in range(safe_months):
        month_list.append((cursor.year, cursor.month))
        if cursor.month == 1:
            cursor = date(cursor.year - 1, 12, 1)
        else:
            cursor = date(cursor.year, cursor.month - 1, 1)
    month_list.reverse()
    start_year, start_month = month_list[0]
    end_year_safe, end_month_safe = month_list[-1]

    where_clause, params = _build_cost_filters(
        mandante_nombre=mandante_nombre,
        proceso_codigo=proceso_codigo,
    )
    period_clause = (
        "(YEAR(ml.fecha_ejecucion) > %s OR (YEAR(ml.fecha_ejecucion) = %s AND MONTH(ml.fecha_ejecucion) >= %s)) "
        "AND (YEAR(ml.fecha_ejecucion) < %s OR (YEAR(ml.fecha_ejecucion) = %s AND MONTH(ml.fecha_ejecucion) <= %s))"
    )
    if where_clause:
        where_clause += f" AND {period_clause}"
    else:
        where_clause = f"WHERE {period_clause}"

    params.extend([start_year, start_year, start_month, end_year_safe, end_year_safe, end_month_safe])
    query = f"""
        SELECT
            YEAR(ml.fecha_ejecucion) AS anio,
            MONTH(ml.fecha_ejecucion) AS mes,
            SUM(ml.total_registros) AS total_registros,
            SUM(ml.costo_total) AS costo_total
        FROM masividades_log ml
        JOIN mandantes m ON ml.mandante_id = m.id
        JOIN procesos p ON ml.proceso_id = p.id
        {where_clause}
        GROUP BY YEAR(ml.fecha_ejecucion), MONTH(ml.fecha_ejecucion)
        ORDER BY YEAR(ml.fecha_ejecucion), MONTH(ml.fecha_ejecucion)
    """

    with get_connection() as conn:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(query, params)
            rows = cast(list[RowDict], cur.fetchall())

    row_map: dict[tuple[int, int], RowDict] = {}
    for row in rows:
        key = (int(row.get("anio") or 0), int(row.get("mes") or 0))
        row_map[key] = {
            "anio": key[0],
            "mes": key[1],
            "periodo": f"{key[0]:04d}-{key[1]:02d}",
            "total_registros": int(row.get("total_registros") or 0),
            "costo_total": _normalize_decimal(row.get("costo_total")),
        }

    result: list[RowDict] = []
    for year, month in month_list:
        existing = row_map.get((year, month))
        if existing:
            result.append(existing)
            continue
        result.append(
            {
                "anio": year,
                "mes": month,
                "periodo": f"{year:04d}-{month:02d}",
                "total_registros": 0,
                "costo_total": 0,
            }
        )
    return result


def get_mandante_ranking(
    *,
    fecha_inicio: datetime,
    fecha_fin: datetime,
    proceso_codigo: str | None = None,
    limit: int = 10,
) -> list[RowDict]:
    safe_limit = max(1, min(limit, 50))
    where_clause, params = _build_cost_filters(
        proceso_codigo=proceso_codigo,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
    )
    query = f"""
        SELECT
            m.nombre AS mandante,
            SUM(ml.total_registros) AS total_registros,
            SUM(ml.costo_total) AS costo_total
        FROM masividades_log ml
        JOIN mandantes m ON ml.mandante_id = m.id
        JOIN procesos p ON ml.proceso_id = p.id
        {where_clause}
        GROUP BY m.id
        ORDER BY SUM(ml.costo_total) DESC, SUM(ml.total_registros) DESC
        LIMIT %s
    """
    params.append(safe_limit)
    with get_connection() as conn:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(query, params)
            rows = cast(list[RowDict], cur.fetchall())
    for row in rows:
        row["total_registros"] = int(row.get("total_registros") or 0)
        row["costo_total"] = _normalize_decimal(row.get("costo_total"))
    return rows


def get_process_month_matrix(
    *,
    months: int = 6,
    mandante_nombre: str | None = None,
    end_year: int | None = None,
    end_month: int | None = None,
) -> list[RowDict]:
    safe_months = max(1, min(months, 12))
    if end_year is None or end_month is None:
        ref = datetime.now()
        end_year = ref.year
        end_month = ref.month

    trend_months = get_monthly_cost_trend(
        months=safe_months,
        mandante_nombre=mandante_nombre,
        end_year=end_year,
        end_month=end_month,
    )
    month_keys = [str(item["periodo"]) for item in trend_months]

    end_period = date(end_year, end_month, 1)
    start_period = end_period
    for _ in range(safe_months - 1):
        if start_period.month == 1:
            start_period = date(start_period.year - 1, 12, 1)
        else:
            start_period = date(start_period.year, start_period.month - 1, 1)

    where_clause, params = _build_cost_filters(mandante_nombre=mandante_nombre)
    period_clause = (
        "(YEAR(ml.fecha_ejecucion) > %s OR (YEAR(ml.fecha_ejecucion) = %s AND MONTH(ml.fecha_ejecucion) >= %s)) "
        "AND (YEAR(ml.fecha_ejecucion) < %s OR (YEAR(ml.fecha_ejecucion) = %s AND MONTH(ml.fecha_ejecucion) <= %s))"
    )
    if where_clause:
        where_clause += f" AND {period_clause}"
    else:
        where_clause = f"WHERE {period_clause}"
    params.extend([start_period.year, start_period.year, start_period.month, end_year, end_year, end_month])

    query = f"""
        SELECT
            p.codigo AS proceso,
            YEAR(ml.fecha_ejecucion) AS anio,
            MONTH(ml.fecha_ejecucion) AS mes,
            SUM(ml.costo_total) AS costo_total,
            SUM(ml.total_registros) AS total_registros
        FROM masividades_log ml
        JOIN procesos p ON ml.proceso_id = p.id
        JOIN mandantes m ON ml.mandante_id = m.id
        {where_clause}
        GROUP BY p.codigo, YEAR(ml.fecha_ejecucion), MONTH(ml.fecha_ejecucion)
        ORDER BY p.codigo, YEAR(ml.fecha_ejecucion), MONTH(ml.fecha_ejecucion)
    """

    with get_connection() as conn:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(query, params)
            rows = cast(list[RowDict], cur.fetchall())

    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        process_code = str(row.get("proceso") or "")
        if process_code not in grouped:
            grouped[process_code] = {
                "proceso": process_code,
                "periodos": {key: {"costo_total": 0, "total_registros": 0} for key in month_keys},
                "total_costo": 0,
                "total_registros": 0,
            }
        period_key = f"{int(row.get('anio') or 0):04d}-{int(row.get('mes') or 0):02d}"
        bucket = grouped[process_code]["periodos"].get(period_key)
        costo = _normalize_decimal(row.get("costo_total"))
        regs = int(row.get("total_registros") or 0)
        if bucket is not None:
            bucket["costo_total"] = costo
            bucket["total_registros"] = regs
        grouped[process_code]["total_costo"] += float(costo or 0)
        grouped[process_code]["total_registros"] += regs

    result = list(grouped.values())
    result.sort(key=lambda item: item.get("total_costo", 0), reverse=True)
    return result


def _normalize_decimal(value: Any) -> Any:
    if value is None:
        return 0
    if isinstance(value, Decimal):
        if value == value.to_integral():
            return int(value)
        return round(float(value), 2)
    return value
