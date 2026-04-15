from __future__ import annotations

import os
from datetime import date
from typing import Any, cast

from utils.db_resultantes import get_resultantes_connection


Row = dict[str, Any]

TANNER_QUERY = """
SELECT
    cliente.rut AS rut,
    doc.nroDocumento AS datadocu,
    '200' AS columna3,
    IFNULL(DATE_FORMAT(compromiso.fechaCompromiso, '%d-%m-%Y'), '') AS fecha,
    respuesta.codigo AS respuesta_gestion,
    gestion.observaciones AS observaciones,
    '2' AS columna7,
    DATE_FORMAT(gestion.fechaInsert, '%d-%m-%Y') AS gestion_fecha,
    DATE_FORMAT(gestion.fechaInsert, '%T') AS gestion_hora,
    usu.rut AS usuario_gestion,
    CONCAT('56', IF(telefono.telefono IS NULL, gestion.fono, telefono.telefono)) AS telefono,
    ma.email AS email,
    '1' AS columna13,
    '2' AS columna14
FROM gestion
LEFT JOIN cliente
    ON gestion.rut = cliente.rut
LEFT JOIN respuesta
    ON gestion.idRespuesta = respuesta.idRespuesta
LEFT JOIN telefono
    ON gestion.idTelefono = telefono.idTelefono
LEFT JOIN compromiso
    ON gestion.idGestion = compromiso.idGestion
LEFT JOIN usuario usu
    ON usu.username = gestion.username
LEFT JOIN (
    SELECT rut, MAX(email) AS email
    FROM email
    GROUP BY rut
) ma
    ON ma.rut = gestion.rut
LEFT JOIN (
    SELECT rut, MAX(nroDocumento) AS nroDocumento
    FROM documento
    WHERE idCartera = %s
    GROUP BY rut
) doc
    ON doc.rut = gestion.rut
WHERE gestion.idCartera = %s
  AND gestion.fechaInsert BETWEEN CONCAT(%s, ' 00:00:00')
                              AND CONCAT(%s, ' 23:59:59')
  AND gestion.observaciones NOT IN ('__INTENTO_LLAMADA__')

UNION ALL

SELECT
    cliente.rut AS rut,
    doc.nroDocumento AS datadocu,
    '200' AS columna3,
    '' AS fecha,
    '401' AS respuesta_gestion,
    'Llamada por Discador' AS observaciones,
    '2' AS columna7,
    DATE_FORMAT(vicidial_log.call_date, '%d-%m-%Y') AS gestion_fecha,
    DATE_FORMAT(vicidial_log.call_date, '%T') AS gestion_hora,
    usu2.rut AS usuario_gestion,
    CONCAT('56', vicidial_log.phone_number) AS telefono,
    ma.email AS email,
    '1' AS columna13,
    '2' AS columna14
FROM vicidial_log
LEFT JOIN vicidial_list
    ON vicidial_log.lead_id = vicidial_list.lead_id
LEFT JOIN cliente
    ON vicidial_list.vendor_lead_code = cliente.rut
LEFT JOIN usuario usu2
    ON usu2.username = vicidial_log.user
LEFT JOIN (
    SELECT rut, MAX(email) AS email
    FROM email
    GROUP BY rut
) ma
    ON ma.rut = cliente.rut
LEFT JOIN (
    SELECT rut, MAX(nroDocumento) AS nroDocumento
    FROM documento
    WHERE idCartera = %s
    GROUP BY rut
) doc
    ON doc.rut = cliente.rut
WHERE vicidial_log.user = %s
  AND vicidial_list.postal_code = %s
  AND vicidial_log.call_date BETWEEN CONCAT(%s, ' 00:00:00')
                                 AND CONCAT(%s, ' 23:59:59')
"""


def _resultantes_enabled() -> bool:
    return os.getenv("RESULT_DB_ENABLED", "0").lower() in {"1", "true", "yes"}


def fetch_tanner_resultantes(fecha_inicio: date, fecha_fin: date) -> list[Row]:
    """Consulta resultantes Tanner entre fechas (inclusive)."""
    if not _resultantes_enabled():
        return []

    cartera = int(os.getenv("RESULTANTES_TANNER_CARTERA", "519"))
    discador_user = (os.getenv("RESULTANTES_TANNER_DISCADOR_USER") or "VDAD").strip() or "VDAD"
    query = (os.getenv("RESULTANTES_TANNER_QUERY") or TANNER_QUERY).strip()
    fecha_inicio_txt = fecha_inicio.strftime("%Y-%m-%d")
    fecha_fin_txt = fecha_fin.strftime("%Y-%m-%d")

    params = (
        cartera,
        cartera,
        fecha_inicio_txt,
        fecha_fin_txt,
        cartera,
        discador_user,
        cartera,
        fecha_inicio_txt,
        fecha_fin_txt,
    )

    with get_resultantes_connection() as conn:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(query, params)
            rows = cur.fetchall() or []
    return cast(list[Row], rows)
