"""MySQL repositories for logging masividades and fetching catalog data."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional
from decimal import Decimal

from utils.db import get_connection


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
            rows = cur.fetchall()
    return [Mandante(id=row["id"], codigo=row["codigo"], nombre=row["nombre"]) for row in rows]


def fetch_mandante_by_nombre(nombre: str) -> Optional[Mandante]:
    query = "SELECT id, codigo, nombre FROM mandantes WHERE nombre = %s AND activo = 1 LIMIT 1"
    with get_connection() as conn:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(query, (nombre,))
            row = cur.fetchone()
            return Mandante(id=row["id"], codigo=row["codigo"], nombre=row["nombre"]) if row else None


def fetch_proceso_by_codigo(codigo: str) -> Optional[Proceso]:
    query = (
        "SELECT id, codigo, descripcion, tipo, costo_unitario "
        "FROM procesos WHERE codigo = %s AND activo = 1 LIMIT 1"
    )
    with get_connection() as conn:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(query, (codigo,))
            row = cur.fetchone()
            return Proceso(
                id=row["id"],
                codigo=row["codigo"],
                descripcion=row["descripcion"],
                tipo=row["tipo"],
                costo_unitario=float(row["costo_unitario"]),
            ) if row else None


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
) -> None:
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
        conn.commit()


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
            resumen = cur.fetchall()
            cur.execute(total_query, params)
            totales = cur.fetchone() or {"total_registros": 0, "costo_total": 0}

    for row in resumen:
        row["total_registros"] = int(row.get("total_registros") or 0)
        row["costo_total"] = _normalize_decimal(row.get("costo_total"))

    totales = {
        "total_registros": int(totales.get("total_registros") or 0),
        "costo_total": _normalize_decimal(totales.get("costo_total")),
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
