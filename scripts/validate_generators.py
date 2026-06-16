from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from repositories.ejecutivos_repo import Ejecutivo
from services.mail_templates import TEMPLATE_COLUMNS_ITAU_VENCIDA, build_mail_template
from services.sant_hipotecario_masividad_service import generar_masividad
from services.sant_hipotecario_service import generar_crm
from services.santander_consumer_service import OUTPUT_COLUMNS, build_santander_consumer_terreno_output


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
    finally:
        sms_itau_vencida.ejecutivos_repo.fetch_by_mandante_and_nombre = original_fetch
        sms_itau_vencida.ejecutivos_repo.list_ejecutivos = original_list

    assert len(messages) == 1, "SMS Itau debe generar un mensaje"
    assert "Itau" in messages.iloc[0], "SMS Itau no contiene texto esperado"
    assert "56912345678" in messages.iloc[0], "SMS Itau no agrega telefono de ejecutivo"
    print("SMS_ITAU_OK")


def validate_mail_itau() -> None:
    from services import mail_templates

    original_fetch = mail_templates.ejecutivos_repo.fetch_by_mandante_and_nombre
    original_list = mail_templates.ejecutivos_repo.list_ejecutivos
    try:
        mail_templates.ejecutivos_repo.fetch_by_mandante_and_nombre = lambda mandante, nombre: _fake_ejecutivo(nombre)
        mail_templates.ejecutivos_repo.list_ejecutivos = lambda mandante=None, activos=True: [_fake_ejecutivo()]
        df = pd.DataFrame(
            {
                "Oper": ["2046954"],
                "RUT": ["13433958"],
                "DV1": ["6"],
                "Nombre": ["CLIENTE PRUEBA"],
                "MASIVIDAD": ["EMAIL"],
                "EMAIL": ["cliente@example.com"],
                "CARTERIZADO": ["Ariel Silva"],
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
    print("MAIL_ITAU_OK")


def validate_santander_consumer() -> None:
    from services import santander_consumer_service as sc_service

    original_bench = sc_service._fetch_tmp_bench_rows
    original_emails = sc_service._fetch_emails_by_rut
    original_fetch = sc_service.ejecutivos_repo.fetch_by_mandante_and_nombre
    original_list = sc_service.ejecutivos_repo.list_ejecutivos
    try:
        sc_service._fetch_tmp_bench_rows = lambda operaciones: {
            "123456": {
                "fld_RUT": "11111111-1",
                "fld_OPERACION": "123456",
                "fld_NOMBRE": "CLIENTE SC",
                "fld_COBRADOR": "Ariel Silva",
                "fld_MARCA": "MARCA",
                "fld_PATENTE": "AA1111",
                "fld_DEUDA_INI": "100000",
                "fld_COMUNA": "SANTIAGO",
                "fld_REGION": "RM",
                "fld_FECHA": "20260616",
                "fecha_carga": "20260616",
            }
        }
        sc_service._fetch_emails_by_rut = lambda ruts: {"111111111": "cliente.sc@example.com"}
        sc_service.ejecutivos_repo.fetch_by_mandante_and_nombre = lambda mandante, nombre: _fake_ejecutivo(nombre)
        sc_service.ejecutivos_repo.list_ejecutivos = lambda mandante=None, activos=True: [_fake_ejecutivo()]
        output = build_santander_consumer_terreno_output(
            pd.DataFrame({"OPERACION": ["123456"]}),
            template_key="vigente",
        )
    finally:
        sc_service._fetch_tmp_bench_rows = original_bench
        sc_service._fetch_emails_by_rut = original_emails
        sc_service.ejecutivos_repo.fetch_by_mandante_and_nombre = original_fetch
        sc_service.ejecutivos_repo.list_ejecutivos = original_list

    assert list(output.columns) == OUTPUT_COLUMNS, "Santander Consumer columnas inesperadas"
    assert output.loc[0, "ENCONTRADO_DB"] == "SI", "Santander Consumer no marco encontrado"
    assert output.loc[0, "dest_email"] == "cliente.sc@example.com", "Santander Consumer no asigno email"
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
        assert masividad["df"].loc[0, "dest_email"] == "cliente.hipotecario@example.com"
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
    print("SANT_HIPOTECARIO_OK")


def main() -> None:
    validate_sms_itau()
    validate_mail_itau()
    validate_santander_consumer()
    validate_santander_hipotecario()
    print("GENERATORS_OK")


if __name__ == "__main__":
    main()
