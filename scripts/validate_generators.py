from __future__ import annotations

import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from repositories.ejecutivos_repo import Ejecutivo
from services.mail_service import build_mail_crm_output
from services.mail_templates import TEMPLATE_COLUMNS_ARAUCANA, TEMPLATE_COLUMNS_BIT, TEMPLATE_COLUMNS_ITAU_CASTIGO, TEMPLATE_COLUMNS_ITAU_VENCIDA, build_mail_template
from services.gm_mail_service import build_gm_mail_crm_output, build_gm_mail_output
from services.sc_telefonia_mail_service import build_sc_telefonia_mail_output
from services.ivr_service import build_ivr_output
from services.sant_hipotecario_masividad_service import generar_masividad
from services.sant_hipotecario_service import generar_crm
from services.santander_consumer_service import OUTPUT_COLUMNS, build_santander_consumer_terreno_output
from services.sms_service import build_athenas_output, build_axia_output, build_crm_output as build_sms_crm_output


def _fake_ejecutivo(nombre: str = "Ariel Silva") -> Ejecutivo:
    return Ejecutivo(
        id=1,
        mandante="TEST",
        nombre_clave=nombre,
        nombre_mostrar=nombre,
        correo="agente@phoenixservice.cl",
        telefono="56912345678",
        reenviador="agente@info.phoenixserviceinfo.cl",
        activo=True,
        metadata=None,
    )


def validate_sms_itau() -> None:
    from services import sms_itau_vencida

    original_fetch = sms_itau_vencida.ejecutivos_repo.fetch_by_mandante_and_nombre
    original_list = sms_itau_vencida.ejecutivos_repo.list_ejecutivos
    try:
        sms_itau_vencida.ejecutivos_repo.fetch_by_mandante_and_nombre = lambda mandante, nombre: _fake_ejecutivo(nombre)
        sms_itau_vencida.ejecutivos_repo.list_ejecutivos = lambda mandante=None, activos=True: [_fake_ejecutivo()]
        df = pd.DataFrame(
            {
                "CARTERIZADO": ["Ariel Silva"],
                "MASIVIDAD": ["SMS MOROSIDAD"],
            }
        )
        messages = sms_itau_vencida.build_itau_carterizado_messages(df, "Itau Vencida")
        axia = build_axia_output(pd.DataFrame({"FONO": ["912345678"], "RUT": ["11111111-1"], "OP": ["OP1"]}), mensaje="base", mensajes_series=messages)
        athenas = build_athenas_output(pd.DataFrame({"TELEFONO": ["912345678"], "RUT": ["11111111-1"], "OP": ["OP1"]}), mensaje="base", mensajes_series=messages)
        axia_seeded, axia_seed_count = sms_itau_vencida.prepend_itau_seed_rows(axia, "AXIA", messages)
        athenas_seeded, athenas_seed_count = sms_itau_vencida.prepend_itau_seed_rows(athenas, "ATHENAS", messages)
    finally:
        sms_itau_vencida.ejecutivos_repo.fetch_by_mandante_and_nombre = original_fetch
        sms_itau_vencida.ejecutivos_repo.list_ejecutivos = original_list

    assert len(messages) == 1, "SMS Itau debe generar un mensaje"
    assert "Itau" in messages.iloc[0], "SMS Itau no contiene texto esperado"
    assert "56912345678" in messages.iloc[0], "SMS Itau no agrega telefono de ejecutivo"
    assert axia_seed_count > 0 and len(axia_seeded) > len(axia), "SMS Itau AXIA no agrega semillas"
    assert athenas_seed_count > 0 and len(athenas_seeded) > len(athenas), "SMS Itau Athenas no agrega semillas"
    print("SMS_ITAU_OK")


def validate_massive_dedupe() -> None:
    ivr = build_ivr_output(
        pd.DataFrame(
            {
                "TELEFONO": ["912345678", "923456789"],
                "RUT": ["11111111-1", "11111111-1"],
                "OP": ["OP1", "OP2"],
                "NOMBRE": ["CLIENTE UNO", "CLIENTE DOS"],
            }
        ),
        campo1_value="PHOENIXIVRITAUVENCIDA",
    )
    assert len(ivr) == 2, "IVR debe conservar 1 contacto duplicado + semilla"
    assert "OP2" not in set(ivr["OPCIONAL"].astype(str)), "IVR no conservo el primer RUT"

    sms_base = pd.DataFrame(
        {
            "FONO": ["912345678", "923456789"],
            "RUT": ["11111111-1", "11111111-1"],
            "OP": ["OP1", "OP2"],
        }
    )
    axia = build_axia_output(sms_base, mensaje="SMS base")
    athenas = build_athenas_output(sms_base, mensaje="SMS base")
    assert len(axia) == 2, "SMS AXIA debe conservar 1 contacto duplicado + semilla"
    assert len(athenas) == 2, "SMS Athenas debe conservar 1 contacto duplicado + semilla"
    assert "923456789" not in set(axia["FONO"].astype(str)), "SMS AXIA no conservo el primer RUT"
    print("MASSIVE_DEDUPE_OK")


def validate_mail_itau() -> None:
    from services import mail_templates

    original_fetch = mail_templates.ejecutivos_repo.fetch_by_mandante_and_nombre
    original_list = mail_templates.ejecutivos_repo.list_ejecutivos
    try:
        mail_templates.ejecutivos_repo.fetch_by_mandante_and_nombre = lambda mandante, nombre: _fake_ejecutivo(nombre)
        mail_templates.ejecutivos_repo.list_ejecutivos = lambda mandante=None, activos=True: [_fake_ejecutivo()]
        df = pd.DataFrame(
            {
                "Oper": ["2046954", "2046955"],
                "RUT": ["13433958", "13433958"],
                "DV1": ["6", "6"],
                "Nombre": ["CLIENTE PRUEBA", "CLIENTE DUPLICADO"],
                "MASIVIDAD": ["EMAIL", "EMAIL"],
                "EMAIL": ["cliente@example.com", "duplicado@example.com"],
                "CARTERIZADO": ["Ariel Silva", "Ariel Silva"],
            }
        )
        output = build_mail_template(df, "ITAU_VENCIDA_MAIL", mandante="Itau Vencida")
    finally:
        mail_templates.ejecutivos_repo.fetch_by_mandante_and_nombre = original_fetch
        mail_templates.ejecutivos_repo.list_ejecutivos = original_list

    assert not output.empty, "Mail Itau no genero filas"
    assert list(output.columns) == TEMPLATE_COLUMNS_ITAU_VENCIDA, "Mail Itau columnas inesperadas"
    assert (output["MES_CURSO"].astype(str).str.strip() != "").any(), "Mail Itau sin MES_CURSO"
    assert "cliente@example.com" in set(output["dest_email"].astype(str)), "Mail Itau no conserva destinatario"
    assert "duplicado@example.com" not in set(output["dest_email"].astype(str)), "Mail Itau no deduplico por RUT"
    print("MAIL_ITAU_OK")


def validate_mail_template_dedupe() -> None:
    tanner_base = pd.DataFrame(
        {
            "RUT+DV": ["11.111.111-1", "11.111.111-1"],
            "OPERACION": ["OP1", "OP2"],
            "dest_email": ["primero@example.com", "duplicado@example.com"],
            "NOMBRE_AGENTE": ["Ariel Silva", "Ariel Silva"],
            "MAIL_AGENTE": ["agente@example.com", "agente@example.com"],
            "PHONO_AGENTE": ["56911111111", "56911111111"],
            "name_from": ["Ariel Silva", "Ariel Silva"],
        }
    )
    tanner_mp = build_mail_template(tanner_base, "TANNER_MEDIOS_PAGO", mandante=None)
    tanner_castigo = build_mail_template(tanner_base, "TANNER_CASTIGO", mandante=None)
    assert len(tanner_mp) == 1 and tanner_mp.loc[0, "OPERACION"] == "OP1", "Tanner Medios Pago no deduplico por RUT"
    assert len(tanner_castigo) == 1 and tanner_castigo.loc[0, "OPERACION"] == "OP1", "Tanner Castigo no deduplico por RUT"

    scj = build_mail_template(
        pd.DataFrame(
            {
                "RUT": ["22.222.222-2", "22.222.222-2"],
                "NUM_OP": ["SCJ1", "SCJ2"],
                "dest_email": ["primero.scj@example.com", "duplicado.scj@example.com"],
                "NOMBRE_AGENTE": ["Ariel Silva", "Ariel Silva"],
                "MAIL_AGENTE": ["agente@example.com", "agente@example.com"],
                "PHONO_AGENTE": ["56911111111", "56911111111"],
                "name_from": ["Ariel Silva", "Ariel Silva"],
            }
        ),
        "SCJ_COBRANZA",
        mandante="Santander Consumer Judicial",
    )
    assert len(scj) == 1 and scj.loc[0, "NUM_OP"] == "SCJ1", "SCJ Cobranza no deduplico por RUT"

    sc_mp = build_mail_template(
        pd.DataFrame(
            {
                "RUT": ["33333333-3", "33333333-3"],
                "MAIL": ["primero.scmp@example.com", "duplicado.scmp@example.com"],
            }
        ),
        "SC_TELEFONIA_MEDIOS_PAGO",
        mandante="Santander Consumer Telefonía",
    )
    assert len(sc_mp) == 2, "SC Telefonia Medios Pago debe conservar 1 contacto + semilla"
    assert "duplicado.scmp@example.com" not in set(sc_mp["dest_email"].astype(str)), "SC Telefonia Medios Pago no deduplico por RUT"

    sc_descuento = build_mail_template(
        pd.DataFrame(
            {
                "NOMBRE_CLIENTE": ["CLIENTE UNO", "CLIENTE DOS"],
                "NRO_OPERACION": ["OP1", "OP2"],
                "MAIL": ["uno@example.com", "dos@example.com"],
            }
        ),
        "SC_TELEFONIA_DESCUENTO",
        mandante="Santander Consumer Telefonía",
    )
    assert len(sc_descuento) == 3, "SC Telefonia Descuento no debe deduplicar"
    print("MAIL_DEDUPE_OK")


def validate_itau_castigo_mail() -> None:
    base = pd.DataFrame(
        {
            "RUT": ["11111111-1", "11111111-1", "22222222-2", "33333333-3"],
            "OPE": ["IC1", "IC2", "IC3", "IC4"],
            "EMAIL": ["primero@example.com", "duplicado-rut@example.com", "PRIMERO@EXAMPLE.COM", "tercero@example.com"],
        }
    )
    ingrid = build_mail_template(base, "ITAU_CASTIGO_SIN_DIRECCION_INGRID", mandante="Itau Castigo")
    jl = build_mail_template(base, "ITAU_CASTIGO_JL", mandante="Itau Castigo")

    assert list(ingrid.columns) == TEMPLATE_COLUMNS_ITAU_CASTIGO, "Itau Castigo columnas inesperadas"
    assert list(ingrid["OPERACION"].astype(str)) == ["1234", "1234", "IC1", "IC4"], "Itau Castigo no deduplico por RUT/email"
    assert list(ingrid["dest_email"].astype(str).head(2)) == ["pipe5550@gmail.com", "jriveros@phoenixservice.cl"], "Itau Castigo sin semillas"
    assert ingrid.loc[0, "message_id"] == 97032, "Itau Castigo Ingrid message_id invalido"
    assert ingrid.loc[0, "PLANTILLA"] == "CASTIGO", "Itau Castigo PLANTILLA invalida"
    assert ingrid.loc[0, "name_from"] == "Ingrid Del Carmen Retamal Garrido", "Itau Castigo Ingrid remitente invalido"
    assert ingrid.loc[0, "mail_from"] == "iretamal@info.phoenixserviceinfo.cl", "Itau Castigo Ingrid mail_from invalido"
    assert jl.loc[0, "message_id"] == 98798, "Itau Castigo JL message_id invalido"
    assert jl.loc[0, "name_from"] == "Jorge Francisco Lopez Cornejo", "Itau Castigo JL remitente invalido"
    assert "PRIMERO@EXAMPLE.COM" not in set(ingrid["dest_email"].astype(str)), "Itau Castigo no deduplico email normalizado"
    print("ITAU_CASTIGO_MAIL_OK")


def validate_bit_mail() -> None:
    base = pd.DataFrame(
        {
            "RUT": ["11111111-1", "11111111-1", "22222222-2", "33333333-3"],
            "OPE": ["BIT1", "BIT2", "BIT3", "BIT4"],
            "CLIENTE": ["CLIENTE UNO", "CLIENTE DUP RUT", "CLIENTE DUP MAIL", "CLIENTE TRES"],
            "EMAIL": ["primero.bit@example.com", "duplicado-rut@example.com", "PRIMERO.BIT@EXAMPLE.COM", "tercero.bit@example.com"],
        }
    )
    castigo = build_mail_template(base, "BIT_CASTIGO", mandante="Banco Internacional")
    vigente = build_mail_template(base, "BIT_VIGENTE", mandante="Banco Internacional")

    assert list(castigo.columns) == TEMPLATE_COLUMNS_BIT, "BIT columnas inesperadas"
    assert list(castigo["OPERACION"].astype(str)) == ["1234", "1234", "BIT1", "BIT4"], "BIT no deduplico por RUT/email"
    assert list(castigo["dest_email"].astype(str).head(2)) == ["pipe5550@gmail.com", "cfuentes@phoenixservice.cl"], "BIT sin semillas"
    assert castigo.loc[0, "message_id"] == 91957, "BIT Castigo message_id invalido"
    assert vigente.loc[0, "message_id"] == 97737, "BIT Vigente message_id invalido"
    assert castigo.loc[0, "mail_from"] == "cfuentes@info.phoenixserviceinfo.cl", "BIT Castigo mail_from debe ser cfuentes"
    assert vigente.loc[0, "mail_from"] == "cfuentes@info.phoenixserviceinfo.cl", "BIT Vigente mail_from invalido"
    assert castigo.loc[0, "MAIL_AGENTE"] == "cfuentes@phoenixservice.cl", "BIT MAIL_AGENTE invalido"
    assert "PRIMERO.BIT@EXAMPLE.COM" not in set(castigo["dest_email"].astype(str)), "BIT no deduplico email normalizado"
    print("BIT_MAIL_OK")


def validate_araucana_mail() -> None:
    base = pd.DataFrame(
        {
            "RUT": ["10117748", "10117748", "10237218", "10333333"],
            "NOMBRE": ["MILTON EDUARDO JARA CIFUENTES", "CLIENTE DUP RUT", "CLIENTE DUP MAIL", "CLIENTE TRES"],
            "EMAIL": ["jaracifuentesmilton@gmail.com", "duplicado-rut@example.com", "JARACIFUENTESMILTON@GMAIL.COM", "cliente3@example.com"],
        }
    )
    cesantes = build_mail_template(base, "ARAUCANA_CESANTES_86391", mandante="La Araucana")
    medio_pago = build_mail_template(base, "ARAUCANA_MEDIO_PAGO_93887", mandante="La Araucana")

    assert list(cesantes.columns) == TEMPLATE_COLUMNS_ARAUCANA, "Araucana columnas inesperadas"
    assert list(cesantes["NOMBRE"].astype(str)) == ["Melanie", "Felipe", "MILTON EDUARDO JARA CIFUENTES", "CLIENTE TRES"], "Araucana no deduplico por RUT/email"
    assert list(cesantes["dest_email"].astype(str).head(2)) == ["mmondiglio@phoenixservice.cl", "pipe5550@gmail.com"], "Araucana sin semillas"
    assert list(cesantes["RUT"].astype(str).head(2)) == ["1", "2"], "Araucana semillas sin RUT esperado"
    assert cesantes.loc[0, "INSTITUCIÓN"] == "CAJA LA ARAUCANA", "Araucana INSTITUCIÓN invalida"
    assert cesantes.loc[0, "SEGMENTOINSTITUCIÓN"] == "ARAUCANA", "Araucana SEGMENTOINSTITUCIÓN invalida"
    assert cesantes.loc[0, "message_id"] == 86391, "Araucana Cesantes message_id invalido"
    assert medio_pago.loc[0, "message_id"] == 93887, "Araucana Medio Pago message_id invalido"
    assert cesantes.loc[0, "name_from"] == "CAJA LA ARAUCANA", "Araucana name_from invalido"
    assert cesantes.loc[0, "mail_from"] == "atencionclientes@estandar.phoenixserviceinfo.cl", "Araucana mail_from invalido"
    assert cesantes.loc[0, "CORREO"] == "mmondiglio@phoenixservice.cl", "Araucana CORREO invalido"
    assert "duplicado-rut@example.com" not in set(cesantes["dest_email"].astype(str)), "Araucana no deduplico RUT"
    assert "JARACIFUENTESMILTON@GMAIL.COM" not in set(cesantes["dest_email"].astype(str)), "Araucana no deduplico email normalizado"
    print("ARAUCANA_MAIL_OK")


def validate_crm_dedupe() -> None:
    crm_sms = build_sms_crm_output(
        pd.DataFrame(
            {
                "RUT": ["11111111-1", "11111111-1"],
                "OP": ["OP1", "OP2"],
                "FONO": ["912345678", "923456789"],
            }
        ),
        usuario="usuario_sms",
        fecha=date(2026, 6, 22),
        hora_inicio="10:00",
        hora_fin="11:00",
        observacion="SMS CRM",
    )
    assert len(crm_sms) == 1, "CRM SMS/IVR debe deduplicar por RUT"
    assert crm_sms.loc[0, "NRO_DOCUMENTO"] == "OP1", "CRM SMS/IVR no conservo la primera fila"

    crm_mail = build_mail_crm_output(
        pd.DataFrame(
            {
                "RUT": ["22222222-2", "22222222-2"],
                "OPERACION": ["MAIL1", "MAIL2"],
                "MAIL": ["primero@example.com", "duplicado@example.com"],
            }
        ),
        fecha=date(2026, 6, 22),
        hora_inicio="10:00",
        hora_fin="11:00",
        usuario_value="usuario_mail",
        observacion_value="MAIL CRM",
    )
    assert len(crm_mail) == 1, "CRM Mail debe deduplicar por RUT"
    assert crm_mail.loc[0, "NRO_DOCUMENTO"] == "MAIL1", "CRM Mail no conservo la primera fila"
    assert crm_mail.loc[0, "CORREO"] == "primero@example.com", "CRM Mail no conservo el primer correo"
    print("CRM_DEDUPE_OK")


def validate_gm_mail() -> None:
    from services import gm_mail_sources

    original_fetch = gm_mail_sources.fetch_tmp_asig_gm_rows
    try:
        gm_mail_sources.fetch_tmp_asig_gm_rows = lambda operaciones: {
            "OP1": {
                "NOMBRE": "CLIENTE UNO",
                "RUT": "11.111.111-1",
                "OPERACION": "OP1",
                "FECHA_VENCIMIENTO_CUOTA": date(2026, 2, 5),
                "MONTO_CUOTA": 12345,
                "dest_email": "primero@example.com",
            },
            "OP2": {
                "NOMBRE": "CLIENTE DUP RUT",
                "RUT": "11.111.111-1",
                "OPERACION": "OP2",
                "FECHA_VENCIMIENTO_CUOTA": date(2026, 2, 6),
                "MONTO_CUOTA": 22222,
                "dest_email": "segundo@example.com",
            },
            "OP3": {
                "NOMBRE": "CLIENTE DUP MAIL",
                "RUT": "22222222-2",
                "OPERACION": "OP3",
                "FECHA_VENCIMIENTO_CUOTA": date(2026, 2, 7),
                "MONTO_CUOTA": 33333,
                "dest_email": "PRIMERO@EXAMPLE.COM",
            },
        }
        output = build_gm_mail_output(
            pd.DataFrame({"operación": ["OP1", "OP2", "OP3", "OP4"]}),
            today=date(2026, 6, 17),
        )
        crm = build_gm_mail_crm_output(
            output,
            fecha=date(2026, 6, 18),
            hora_inicio="10:00",
            hora_fin="11:00",
        )
        extension = build_gm_mail_output(
            pd.DataFrame({"OP": ["OP1"]}),
            template_key="gm_extension_84591",
            today=date(2026, 6, 17),
            delivery_date=date(2026, 6, 25),
        )
        descuento = build_gm_mail_output(
            pd.DataFrame({"OPERACION": ["OP1", "OP2", "OP3", "OP4"]}),
            template_key="gm_descuento_98960",
            today=date(2026, 6, 17),
            delivery_date=date(2026, 6, 30),
        )
        descuento_crm = build_gm_mail_crm_output(
            descuento,
            fecha=date(2026, 6, 18),
            hora_inicio="10:00",
            hora_fin="11:00",
        )
    finally:
        gm_mail_sources.fetch_tmp_asig_gm_rows = original_fetch

    expected_columns = [
        "INSTITUCIÓN",
        "SEGMENTOINSTITUCIÓN",
        "message_id",
        "NOMBRE",
        "RUT",
        "OPERACION",
        "FECHA_VENCIMIENTO_CUOTA",
        "MONTO_CUOTA",
        "FECHA_ARCHIVO",
        "FONO_EJECUTIVA",
        "dest_email",
        "name_from",
        "mail_from",
        "CORREO_EJECUTIVA",
    ]
    assert list(output.columns) == expected_columns, "GM Mail columnas inesperadas"
    assert list(output["dest_email"].astype(str).head(2)) == ["pipe5550@gmail.com", "cfuentes@phoenixservice.cl"], "GM Mail no antepuso semillas"
    assert list(output["OPERACION"].astype(str)) == ["1234", "1234", "OP1", "OP4"], "GM Mail no conservo orden/dedupe esperado"
    assert output.loc[0, "INSTITUCIÓN"] == "GENERAL MOTORS", "GM Mail no aplico fijo INSTITUCIÓN"
    assert output.loc[0, "FONO_EJECUTIVA"] == 962487407, "GM Mail no aplico telefono fijo"
    assert output.loc[0, "name_from"] == "Jesabel Jeldez Fuentez", "GM Mail no aplico name_from fijo"
    assert output.loc[0, "RUT"] == "1-1", "GM Mail semilla sin RUT neutral"
    assert output.loc[1, "RUT"] == "1-2", "GM Mail segunda semilla sin RUT neutral"
    assert output.loc[2, "RUT"] == "11.111.111-1", "GM Mail debe mantener RUT completo en masividad"
    assert output.loc[0, "NOMBRE"] == "PRB", "GM Mail semilla sin nombre neutral"
    assert output.loc[2, "FECHA_VENCIMIENTO_CUOTA"] == "05-02-2026", "GM Mail no formateo vencimiento"
    assert output.loc[0, "FECHA_ARCHIVO"] == "17-06-2026", "GM Mail no aplico fecha archivo"
    assert output.loc[3, "OPERACION"] == "OP4", "GM Mail no conserva operacion sin match"
    assert output.loc[3, "NOMBRE"] == "", "GM Mail operacion sin match debe quedar sin datos SQL"
    assert "PRIMERO@EXAMPLE.COM" not in set(output["dest_email"].astype(str)), "GM Mail no deduplico email normalizado"
    assert list(crm.columns) == ["RUT", "NRO_DOCUMENTO", "FECHA_GESTION", "TELEFONO", "OBSERVACION", "USUARIO", "CORREO"], "GM Mail CRM columnas inesperadas"
    assert len(crm) == 1, "GM Mail CRM debe excluir semillas y operaciones sin datos"
    assert crm.loc[0, "USUARIO"] == "jriveros", "GM Mail CRM usuario fijo invalido"
    assert crm.loc[0, "OBSERVACION"] == "ENVIO MAIL", "GM Mail CRM observacion fija invalida"
    assert crm.loc[0, "NRO_DOCUMENTO"] == "OP1", "GM Mail CRM no conserva operacion"
    assert crm.loc[0, "RUT"] == "11111111", "GM Mail CRM debe quitar DV y guion del RUT"
    assert crm.loc[0, "CORREO"] == "primero@example.com", "GM Mail CRM no conserva correo"
    assert "pipe5550@gmail.com" not in set(crm["CORREO"].astype(str).str.lower()), "GM Mail CRM no excluyo semilla pipe"
    assert "cfuentes@phoenixservice.cl" not in set(crm["CORREO"].astype(str).str.lower()), "GM Mail CRM no excluyo semilla cfuentes"
    assert crm.loc[0, "FECHA_GESTION"] == "2026-06-18 10:00:00", "GM Mail CRM fecha gestion invalida"
    assert "FECHA_ENTREGA" in extension.columns, "GM Extension sin FECHA_ENTREGA"
    assert extension.loc[0, "message_id"] == 84591, "GM Extension no aplica message_id"
    assert extension.loc[0, "FECHA_ENTREGA"] == "25-06-2026", "GM Extension no aplica FECHA_ENTREGA"
    assert list(extension["dest_email"].astype(str).head(2)) == ["pipe5550@gmail.com", "cfuentes@phoenixservice.cl"], "GM Extension no mantiene semillas"
    expected_descuento_columns = [
        "INSTITUCIÓN",
        "SEGMENTOINSTITUCIÓN",
        "message_id",
        "NOMBRE",
        "RUT",
        "OPERACION",
        "FECHA_VENCIMIENTO_CUOTA",
        "MONTO_CUOTA",
        "FECHA_VALIDA",
        "FECHA_ARCHIVO",
        "FONO_EJECUTIVA",
        "dest_email",
        "name_from",
        "mail_from",
        "CORREO_EJECUTIVA",
    ]
    assert list(descuento.columns) == expected_descuento_columns, "GM Descuento columnas inesperadas"
    assert descuento.loc[0, "message_id"] == 98960, "GM Descuento no aplica message_id"
    assert descuento.loc[0, "FECHA_VALIDA"] == "30-06-2026", "GM Descuento no aplica FECHA_VALIDA en semillas"
    assert descuento.loc[2, "FECHA_VALIDA"] == "30-06-2026", "GM Descuento no aplica FECHA_VALIDA en datos SQL"
    assert descuento.loc[0, "FECHA_ARCHIVO"] == "17-06-2026", "GM Descuento no aplica FECHA_ARCHIVO"
    assert list(descuento["dest_email"].astype(str).head(2)) == ["pipe5550@gmail.com", "cfuentes@phoenixservice.cl"], "GM Descuento no mantiene semillas"
    assert list(descuento["OPERACION"].astype(str)) == ["1234", "1234", "OP1", "OP4"], "GM Descuento no deduplico RUT/email"
    assert "PRIMERO@EXAMPLE.COM" not in set(descuento["dest_email"].astype(str)), "GM Descuento no deduplico email normalizado"
    assert len(descuento_crm) == 1, "GM Descuento CRM debe excluir semillas y operaciones sin datos"
    assert descuento_crm.loc[0, "NRO_DOCUMENTO"] == "OP1", "GM Descuento CRM no conserva operacion"
    assert descuento_crm.loc[0, "RUT"] == "11111111", "GM Descuento CRM debe quitar DV y guion del RUT"
    assert descuento_crm.loc[0, "CORREO"] == "primero@example.com", "GM Descuento CRM no conserva correo"
    print("GM_MAIL_OK")


def validate_sc_telefonia_mail() -> None:
    from services import sc_telefonia_mail_sources

    original_fetch_rows = sc_telefonia_mail_sources.fetch_tmp_bench_temp_stc_rows
    original_fetch_exec = sc_telefonia_mail_sources.fetch_executive_by_key
    try:
        sc_telefonia_mail_sources.fetch_tmp_bench_temp_stc_rows = lambda operaciones: {
            "OP1": {"RUT": "11111111-1", "NOMBRE": "CLIENTE UNO", "OPERACION": "OP1", "EMAIL": "uno@example.com"},
            "OP2": {"RUT": "11111111-1", "NOMBRE": "CLIENTE DUP RUT", "OPERACION": "OP2", "EMAIL": "dos@example.com"},
            "OP3": {"RUT": "22222222-2", "NOMBRE": "CLIENTE DUP MAIL", "OPERACION": "OP3", "EMAIL": "UNO@EXAMPLE.COM"},
        }
        sc_telefonia_mail_sources.fetch_executive_by_key = lambda key: _fake_ejecutivo("Alejandra Carolina Diaz Fuentes")

        descuento = build_sc_telefonia_mail_output(
            pd.DataFrame({"OPERACION": ["OP1", "OP4"]}),
            template_key="sc_telefonia_descuento_95008",
            selected_date=date(2026, 6, 25),
        )
        medios_pago = build_sc_telefonia_mail_output(
            pd.DataFrame({"OP": ["OP1", "OP2", "OP3", "OP4"]}),
            template_key="sc_telefonia_medios_pago_96706",
        )
        novacion = build_sc_telefonia_mail_output(
            pd.DataFrame({"N_OPERACION": ["OP1"]}),
            template_key="sc_telefonia_novacion_93500",
            selected_date=date(2026, 6, 25),
            executive_key="alejandra_diaz",
        )
    finally:
        sc_telefonia_mail_sources.fetch_tmp_bench_temp_stc_rows = original_fetch_rows
        sc_telefonia_mail_sources.fetch_executive_by_key = original_fetch_exec

    assert descuento.loc[0, "dest_email"] == "pipe5550@gmail.com", "SC Telefonia descuento sin semilla"
    assert descuento.loc[0, "RUT"] == "1-1" and descuento.loc[0, "CLIENTE"] == "PRB" and descuento.loc[0, "NRO_OPERACION"] == "1234", "SC Telefonia descuento semilla incompleta"
    assert descuento.loc[1, "NRO_OPERACION"] == "OP1", "SC Telefonia descuento no mapea operacion"
    assert descuento.loc[2, "NRO_OPERACION"] == "OP4" and descuento.loc[2, "CLIENTE"] == "", "SC Telefonia descuento sin match invalido"
    assert descuento.loc[1, "DIA"] == "25" and descuento.loc[1, "MES"] == "Junio" and descuento.loc[1, "ANO"] == "2026", "SC Telefonia fecha invalida"

    assert list(medios_pago["N_OPERACION"].astype(str)) == ["1234", "OP1", "OP4"], "SC Telefonia 96706 no deduplico esperado"
    assert medios_pago.loc[0, "RUT"] == "1-1" and medios_pago.loc[0, "NOMBRE"] == "PRB", "SC Telefonia 96706 semilla incompleta"
    assert "dos@example.com" not in set(medios_pago["dest_email"].astype(str)), "SC Telefonia 96706 no deduplico RUT"
    assert "UNO@EXAMPLE.COM" not in set(medios_pago["dest_email"].astype(str)), "SC Telefonia 96706 no deduplico email normalizado"

    assert novacion.loc[0, "dest_email"] == "pipe5550@gmail.com", "SC Telefonia novacion sin semilla"
    assert novacion.loc[0, "RUT"] == "1-1" and novacion.loc[0, "NOMBRE"] == "PRB" and novacion.loc[0, "OPERACION"] == "1234", "SC Telefonia novacion semilla incompleta"
    assert novacion.loc[0, "FONO_EJECUTIVO"] == 967280344, "SC Telefonia novacion fono fijo invalido"
    assert novacion.loc[1, "EJECU"] == "Alejandra Carolina Diaz Fuentes", "SC Telefonia novacion no aplica ejecutiva"
    assert novacion.loc[1, "DIA"] == "25" and novacion.loc[1, "MES"] == "Junio" and novacion.loc[1, "ANO"] == "2026", "SC Telefonia novacion fecha invalida"
    print("SC_TELEFONIA_MAIL_OK")


def validate_santander_consumer() -> None:
    from services import santander_consumer_service as sc_service
    from services import santander_consumer_assignments as sc_assignments
    from services import santander_consumer_sources as sc_sources

    original_bench = sc_sources.fetch_tmp_bench_rows
    original_emails = sc_sources.fetch_emails_by_rut
    original_fetch = sc_assignments.ejecutivos_repo.fetch_by_mandante_and_nombre
    original_list = sc_assignments.ejecutivos_repo.list_ejecutivos
    try:
        sc_sources.fetch_tmp_bench_rows = lambda operaciones: {
            "123456": {
                "fld_RUT": "11111111-1",
                "fld_OPERACION": "123456",
                "fld_NOMBRE": "CLIENTE SC",
                "fld_COBRADOR": "Ariel Silva",
                "fld_MARCA": "MARCA",
                "fld_PATENTE": "AA1111",
                "fld_DEUDA_INI": "100000",
                "fld_COMUNA": "SANTIAGO",
                "fld_REGION": "REGION METROPOLITANA",
                "fld_FECHA": "20260616",
                "fecha_carga": "20260616",
            }
        }
        sc_sources.fetch_emails_by_rut = lambda ruts: {"111111111": "cliente.sc@example.com"}
        sc_assignments.ejecutivos_repo.fetch_by_mandante_and_nombre = lambda mandante, nombre: _fake_ejecutivo(nombre)
        sc_assignments.ejecutivos_repo.list_ejecutivos = lambda mandante=None, activos=True: [_fake_ejecutivo()]
        output = build_santander_consumer_terreno_output(
            pd.DataFrame({"OPERACION": ["123456"]}),
            template_key="vigente",
        )
        output_rm = build_santander_consumer_terreno_output(
            pd.DataFrame({"OPERACION": ["123456"]}),
            template_key="vigente",
            asignacion_mode="supervisor_rm",
        )
        output_offer = build_santander_consumer_terreno_output(
            pd.DataFrame({"OPERACION": ["123456"]}),
            template_key="susceptible",
            offer_deadline=date(2026, 6, 22),
        )
    finally:
        sc_sources.fetch_tmp_bench_rows = original_bench
        sc_sources.fetch_emails_by_rut = original_emails
        sc_assignments.ejecutivos_repo.fetch_by_mandante_and_nombre = original_fetch
        sc_assignments.ejecutivos_repo.list_ejecutivos = original_list

    assert list(output.columns) == OUTPUT_COLUMNS, "Santander Consumer columnas inesperadas"
    assert output.loc[0, "ENCONTRADO_DB"] == "SI", "Santander Consumer no marco encontrado"
    assert output.loc[0, "dest_email"] == "cliente.sc@example.com", "Santander Consumer no asigno email"
    assert output_rm.loc[0, "name_from"] == "Juan Pablo Rios", "Santander Consumer supervisor RM no asigno remitente"
    assert output_offer.loc[0, "DIA_OFERTA"] == "22", "Santander Consumer no asigno DIA_OFERTA"
    assert output_offer.loc[0, "MES_OFERTA"] == "Junio", "Santander Consumer no asigno MES_OFERTA"
    assert output_offer.loc[0, "ANO_OFERTA"] == "2026", "Santander Consumer no asigno ANO_OFERTA"
    print("SANTANDER_CONSUMER_OK")


def _santander_hipotecario_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "numero_operacion": ["12345"],
            "rut": ["11111111"],
            "dv_cliente": ["1"],
            "nombre_cliente": ["CLIENTE HIPOTECARIO"],
            "nombre_producto": ["HIPOTECARIO"],
            "perfil_riesgo": ["BAJO"],
            "ciclo": ["1"],
            "dias_atraso": ["5"],
            "telefono_1": ["912345678"],
            "direccion": ["CALLE 123"],
            "estrategia_1": ["NORMAL"],
            "nro_cuotas_pagadas": ["10"],
            "total_cuotas": ["20"],
            "nro_cuotas_en_mora": ["1"],
            "fecha_vcto_cuota": ["20260616"],
            "monto_cuota": ["100000"],
            "tipo_campana": ["HIPOTECARIO"],
            "total_arrastre": ["200000"],
            "mail": ["cliente.hipotecario@example.com"],
        }
    )


def validate_santander_hipotecario() -> None:
    (ROOT / "storage").mkdir(exist_ok=True)
    output_dir = tempfile.mkdtemp(prefix="sant_hipotecario_", dir=str(ROOT / "storage"))
    try:
        df = _santander_hipotecario_df()
        crm = generar_crm(df, output_dir)
        masividad = generar_masividad(df, output_dir)

        assert Path(crm["crm_path"]).exists(), "Santander Hipotecario no creo CRM"
        assert Path(masividad["masiv_path"]).exists(), "Santander Hipotecario no creo masividad"
        assert not masividad["df"].empty, "Santander Hipotecario masividad vacia"
        assert {"RUT", "CLIENTE", "dest_email", "message_id"}.issubset(masividad["df"].columns)
        assert masividad["df"].loc[0, "dest_email"] == "cliente.hipotecario@example.com"
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
    print("SANT_HIPOTECARIO_OK")


def main() -> None:
    validate_sms_itau()
    validate_massive_dedupe()
    validate_mail_itau()
    validate_mail_template_dedupe()
    validate_itau_castigo_mail()
    validate_bit_mail()
    validate_araucana_mail()
    validate_crm_dedupe()
    validate_gm_mail()
    validate_sc_telefonia_mail()
    validate_santander_consumer()
    validate_santander_hipotecario()
    print("GENERATORS_OK")


if __name__ == "__main__":
    main()
