"""MySQL repositories for logging masividades and fetching catalog data."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional, cast
from datetime import datetime
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


def get_cost_summary(mandante_nombre: str | None = None) -> dict[str, Any]:
    filters = []
    params: list[Any] = []
    if mandante_nombre:
        filters.append("m.nombre = %s")
        params.append(mandante_nombre)

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

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
        "resumen_por_proceso": resumen,
        "totales": totales,
    }


def _normalize_decimal(value: Any) -> Any:
    if value is None:
        return 0
    if isinstance(value, Decimal):
        if value == value.to_integral():
            return int(value)
        return round(float(value), 2)
    return value
