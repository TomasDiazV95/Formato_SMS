from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional
import logging

from utils.db_sqlserver import get_stc_connection

logger = logging.getLogger(__name__)

EJECUTIVOS_TABLE = "dbo.tbl_ejecutivos_phoenix"
ALIAS_TABLE = "dbo.tbl_alias_ejecutivos"


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


def _fetchone_dict(cur) -> dict[str, Any] | None:
    row = cur.fetchone()
    if not row:
        return None
    columns = [column[0] for column in cur.description]
    return dict(zip(columns, row))


def _fetchall_dicts(cur) -> list[dict[str, Any]]:
    rows = cur.fetchall() or []
    columns = [column[0] for column in cur.description]
    return [dict(zip(columns, row)) for row in rows]


def fetch_by_mandante_and_nombre(mandante: str, nombre: str) -> Optional[Ejecutivo]:
    if not mandante or not nombre:
        return None
    query = (
        f"SELECT TOP 1 * FROM {EJECUTIVOS_TABLE} "
        "WHERE mandante = ? AND nombre_clave = ? AND activo = 1"
    )
    try:
        with get_stc_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, (mandante, nombre))
            row = _fetchone_dict(cur)
            if row:
                return _row_to_ejecutivo(row)

            alias_query = (
                f"SELECT TOP 1 e.* FROM {EJECUTIVOS_TABLE} e "
                f"JOIN {ALIAS_TABLE} a ON a.ejecutivo_id = e.id "
                "WHERE e.mandante = ? AND a.alias = ? AND e.activo = 1"
            )
            cur.execute(alias_query, (mandante, nombre))
            alias_row = _fetchone_dict(cur)
            if alias_row:
                return _row_to_ejecutivo(alias_row)
    except Exception as exc:  # pragma: no cover - fallback when tabla no existe
        logger.debug("No se pudo obtener ejecutivo (%s, %s): %s", mandante, nombre, exc)
    return None


def list_ejecutivos(*, mandante: Optional[str] = None, activos: Optional[bool] = None) -> list[Ejecutivo]:
    clauses: list[str] = []
    params: list[Any] = []
    if mandante:
        clauses.append("mandante = ?")
        params.append(mandante)
    if activos is not None:
        clauses.append("activo = ?")
        params.append(1 if activos else 0)
    where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"SELECT * FROM {EJECUTIVOS_TABLE} {where_clause} ORDER BY mandante, nombre_clave"
    with get_stc_connection() as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        rows = _fetchall_dicts(cur)
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
        f"INSERT INTO {EJECUTIVOS_TABLE} "
        "(mandante, nombre_clave, nombre_mostrar, correo, telefono, reenviador, metadata_json) "
        "OUTPUT INSERTED.id "
        "VALUES (?, ?, ?, ?, ?, ?, ?)"
    )
    metadata_json = json.dumps(metadata) if metadata else None
    params = (mandante, nombre_clave, nombre_mostrar, correo, telefono, reenviador, metadata_json)
    with get_stc_connection() as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        new_id = cur.fetchone()[0]
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
        fields.append("nombre_clave = ?")
        params.append(nombre_clave)
    if nombre_mostrar is not None:
        fields.append("nombre_mostrar = ?")
        params.append(nombre_mostrar)
    if correo is not None:
        fields.append("correo = ?")
        params.append(correo)
    if telefono is not None:
        fields.append("telefono = ?")
        params.append(telefono)
    if reenviador is not None:
        fields.append("reenviador = ?")
        params.append(reenviador)
    if metadata is not None:
        fields.append("metadata_json = ?")
        params.append(json.dumps(metadata))
    if activo is not None:
        fields.append("activo = ?")
        params.append(1 if activo else 0)
    if not fields:
        return
    params.append(ejecutivo_id)
    query = f"UPDATE {EJECUTIVOS_TABLE} SET {', '.join(fields)}, fecha_actualizacion = SYSDATETIME() WHERE id = ?"
    with get_stc_connection() as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()


def add_alias(ejecutivo_id: int, alias: str) -> None:
    query = (
        f"IF NOT EXISTS (SELECT 1 FROM {ALIAS_TABLE} WHERE ejecutivo_id = ? AND alias = ?) "
        f"INSERT INTO {ALIAS_TABLE} (ejecutivo_id, alias) VALUES (?, ?)"
    )
    with get_stc_connection() as conn:
        cur = conn.cursor()
        cur.execute(query, (ejecutivo_id, alias, ejecutivo_id, alias))
        conn.commit()


def remove_alias(ejecutivo_id: int, alias: str) -> None:
    query = f"DELETE FROM {ALIAS_TABLE} WHERE ejecutivo_id = ? AND alias = ?"
    with get_stc_connection() as conn:
        cur = conn.cursor()
        cur.execute(query, (ejecutivo_id, alias))
        conn.commit()
