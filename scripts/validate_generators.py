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
from services.mail_templates import TEMPLATE_COLUMNS_ITAU_VENCIDA, build_mail_template
from services.ivr_service import build_ivr_output
from services.sant_hipotecario_masividad_service import generar_masividad
from services.sant_hipotecario_service import generar_crm
from services.santander_consumer_service import OUTPUT_COLUMNS, build_santander_consumer_terreno_output
from services.sms_service import build_athenas_output, build_axia_output


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
        axia = build_axia_output(pd.DataFrame({"FONO": ["912345678"]}), mensaje="base", mensajes_series=messages)
        athenas = build_athenas_output(pd.DataFrame({"TELEFONO": ["912345678"], "ID_CLIENTE": ["11111111-1"]}), mensaje="base", mensajes_series=messages)
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
    validate_santander_consumer()
    validate_santander_hipotecario()
    print("GENERATORS_OK")


if __name__ == "__main__":
    main()
