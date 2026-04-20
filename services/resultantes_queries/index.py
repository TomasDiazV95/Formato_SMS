from __future__ import annotations

from datetime import date


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


PORSCHE_QUERY = """
select  'Phoenix' as 'Nombre de Agencia'
       --  , LPAD(g.nroDocumento, 8, '0')  as 'Nro Contrato'
       ,CASE
        WHEN CHAR_LENGTH(g.nroDocumento) > 8
        THEN RIGHT(CAST(g.nroDocumento AS CHAR), 8)
        ELSE
        LPAD(CAST(g.nroDocumento AS CHAR), 8, '0')
        END AS 'Nro Contrato'
       , LEFT(COALESCE((SELECT e.nombreCliente FROM cliente e WHERE e.rut = g.rut LIMIT 1), ''), 250) as 'Nombre de Cliente'
     --  , coalesce((select nombreCliente from cliente e where rut = g.rut limit 1), '')  as 'Nombre de Cliente'
       , coalesce((select concat(rut,'-',dv) from cliente e where rut = g.rut limit 1), '')  as 'RUT'
       , coalesce((select tipoDeudor from documento where rut = g.rut and nroDocumento = g.nroDocumento and idCartera = g.idCartera), '') as 'Tramo de mora'
       , 'Prejudicial' as 'Tipo de Cobranza'
       , ifnull(date_format(g.fechaInsert, '%d-%m-%Y'), '')  as 'Fecha de Gestion'
      -- , ifnull(CONCAT('56', t.telefono),g.fono)  as 'Telefono'
       , ifnull(CONCAT('56', t.telefono),CONCAT('56', g.fono))  as 'Telefono'
       , td.codigo as 'Codigo de Accion'
       , td.nombre as 'Descripcion de Accion'
       , r.codigo as 'Codigo de Resultado'
       , r.nombre as 'Descripcion de Resultado'
       , ifnull(date_format(c.fechaCompromiso, '%d-%m-%Y'), '') as 'Fecha de Agendamiento'
      -- , LEFT(IFNULL(g.observaciones, ''), 255) AS Coment_Ges
       , g.observaciones as 'Comentario de Gestion'
       ,ifnull(DATE_FORMAT(g.fechaInsert, '%H:%i:%s'), '') AS 'Hora de Gestion'
 from gestion g
 left join compromiso c on g.idGestion = c.idGestion
 left join tipogestion tg on g.idTipoGestion = tg.idTipoGestion
 left join tipodeudor td on g.idTipoDeudor = td.idTipoDeudor
 left join respuesta r on g.idRespuesta = r.idRespuesta
 left join telefono t on g.idTelefono = t.idTelefono
 left join call_log cl on g.callid = cl.caller_code
where g.idCartera = __CARTERA__
and g.idRespuesta not IN ('1')
and g.fechaInsert BETWEEN '__INICIO__' and '__FIN__'
"""


def build_tanner_params(
    *,
    cartera: int,
    discador_user: str,
    fecha_inicio: date,
    fecha_fin: date,
) -> tuple[object, ...]:
    fecha_inicio_txt = fecha_inicio.strftime("%Y-%m-%d")
    fecha_fin_txt = fecha_fin.strftime("%Y-%m-%d")
    return (
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


def build_porsche_params(*, cartera: int, fecha_inicio: date, fecha_fin: date) -> tuple[str, str, str]:
    inicio = f"{fecha_inicio.strftime('%Y-%m-%d')} 00:00:00"
    fin = f"{fecha_fin.strftime('%Y-%m-%d')} 23:59:59"
    return (str(cartera), inicio, fin)
