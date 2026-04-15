from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional
import logging

from utils.db import get_connection

logger = logging.getLogger(__name__)


@dataclass
class Ejecutivo:
    id: int
    mandante: str
    nombre_clave: str
    nombre_mostrar: Optional[str]
    correo: Optional[str]
    telefono: Optional[str]
    reenviador: Optional[str]
    activo: bool
    metadata: Optional[dict[str, Any]]


def _row_to_ejecutivo(row: dict[str, Any]) -> Ejecutivo:
    metadata = row.get("metadata_json")
    if metadata and isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            metadata = None
    return Ejecutivo(
        id=row["id"],
        mandante=row["mandante"],
        nombre_clave=row["nombre_clave"],
        nombre_mostrar=row.get("nombre_mostrar"),
        correo=row.get("correo"),
        telefono=row.get("telefono"),
        reenviador=row.get("reenviador"),
        activo=bool(row.get("activo", 1)),
        metadata=metadata if isinstance(metadata, dict) else None,
    )


def fetch_by_mandante_and_nombre(mandante: str, nombre: str) -> Optional[Ejecutivo]:
    if not mandante or not nombre:
        return None
    query = (
        "SELECT * FROM ejecutivos_phoenix "
        "WHERE mandante = %s AND nombre_clave = %s AND activo = 1 LIMIT 1"
    )
    try:
        with get_connection() as conn:
            with conn.cursor(dictionary=True) as cur:
                cur.execute(query, (mandante, nombre))
                row = cur.fetchone()
                if row:
                    return _row_to_ejecutivo(row)

                alias_query = (
                    "SELECT e.* FROM ejecutivos_phoenix e "
                    "JOIN ejecutivos_alias a ON a.ejecutivo_id = e.id "
                    "WHERE e.mandante = %s AND a.alias = %s AND e.activo = 1 LIMIT 1"
                )
                cur.execute(alias_query, (mandante, nombre))
                alias_row = cur.fetchone()
                if alias_row:
                    return _row_to_ejecutivo(alias_row)
    except Exception as exc:  # pragma: no cover - fallback when tabla no existe
        logger.debug("No se pudo obtener ejecutivo (%s, %s): %s", mandante, nombre, exc)
    return None


def list_ejecutivos(*, mandante: Optional[str] = None, activos: Optional[bool] = None) -> list[Ejecutivo]:
    clauses: list[str] = []
    params: list[Any] = []
    if mandante:
        clauses.append("mandante = %s")
        params.append(mandante)
    if activos is not None:
        clauses.append("activo = %s")
        params.append(1 if activos else 0)
    where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"SELECT * FROM ejecutivos_phoenix {where_clause} ORDER BY mandante, nombre_clave"
    with get_connection() as conn:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(query, params)
            rows = cur.fetchall() or []
    return [_row_to_ejecutivo(row) for row in rows]


def create_ejecutivo(
    *,
    mandante: str,
    nombre_clave: str,
    nombre_mostrar: Optional[str] = None,
    correo: Optional[str] = None,
    telefono: Optional[str] = None,
    reenviador: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> int:
    query = (
        "INSERT INTO ejecutivos_phoenix (mandante, nombre_clave, nombre_mostrar, correo, telefono, reenviador, metadata_json) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)"
    )
    metadata_json = json.dumps(metadata) if metadata else None
    params = (mandante, nombre_clave, nombre_mostrar, correo, telefono, reenviador, metadata_json)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            new_id = cur.lastrowid
        conn.commit()
    return int(new_id)


def update_ejecutivo(
    ejecutivo_id: int,
    *,
    nombre_clave: Optional[str] = None,
    nombre_mostrar: Optional[str] = None,
    correo: Optional[str] = None,
    telefono: Optional[str] = None,
    reenviador: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
    activo: Optional[bool] = None,
) -> None:
    fields = []
    params: list[Any] = []
    if nombre_clave is not None:
        fields.append("nombre_clave = %s")
        params.append(nombre_clave)
    if nombre_mostrar is not None:
        fields.append("nombre_mostrar = %s")
        params.append(nombre_mostrar)
    if correo is not None:
        fields.append("correo = %s")
        params.append(correo)
    if telefono is not None:
        fields.append("telefono = %s")
        params.append(telefono)
    if reenviador is not None:
        fields.append("reenviador = %s")
        params.append(reenviador)
    if metadata is not None:
        fields.append("metadata_json = %s")
        params.append(json.dumps(metadata))
    if activo is not None:
        fields.append("activo = %s")
        params.append(1 if activo else 0)
    if not fields:
        return
    params.append(ejecutivo_id)
    query = f"UPDATE ejecutivos_phoenix SET {', '.join(fields)} WHERE id = %s"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
        conn.commit()


def add_alias(ejecutivo_id: int, alias: str) -> None:
    query = "INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) VALUES (%s, %s)"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (ejecutivo_id, alias))
        conn.commit()


def remove_alias(ejecutivo_id: int, alias: str) -> None:
    query = "DELETE FROM ejecutivos_alias WHERE ejecutivo_id = %s AND alias = %s"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (ejecutivo_id, alias))
        conn.commit()
