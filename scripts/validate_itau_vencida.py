from __future__ import annotations

from io import BytesIO
import sys
from pathlib import Path
import zipfile

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import app
from repositories.ejecutivos_repo import Ejecutivo
from services import mail_templates, sms_itau_vencida
from services.itau_vencida_service import (
    HEADER_ALIASES,
    build_itau_vencida_outputs,
)


def _fake_ejecutivo(nombre: str = "Ariel Silva") -> Ejecutivo:
    return Ejecutivo(
        id=1,
        mandante="Itau Vencida",
        nombre_clave=nombre,
        nombre_mostrar=nombre,
        correo="agente@phoenixservice.cl",
        telefono="56912345678",
        reenviador="agente@info.phoenixserviceinfo.cl",
        activo=True,
        metadata=None,
    )


def _origin_workbook() -> BytesIO:
    source = pd.DataFrame(
        {
            "RUT": ["11111111", "22222222", "33333333", "44444444", "55555555", "66666666"],
            "DV": ["1", "2", "3", "4", "5", "6"],
            "OPERACIÓN": ["OP1", "OP2", "OP3", "OP4", "OP5", "OP6"],
            "NOMBRE": ["CLIENTE 1", "CLIENTE 2", "CLIENTE 3", "CLIENTE 4", "CLIENTE 5", "CLIENTE 6"],
            "CARTERIZADO": ["Ariel Silva"] * 6,
            "MASIVIDADES": [
                "SMS MOROSIDAD",
                "SMS COMPROMISO DE PAGO",
                "SMS COMPROMISO ROTO",
                "SMS CAMPA\u00d1A",
                "ITAU VENCIDA COBRANZA",
                "EMAIL CAMPA\u00d1A ITAU VIGENTE",
            ],
            "EMAIL": [
                "",
                "",
                "",
                "",
                "cliente84824@example.com",
                "cliente100998@example.com",
            ],
            "TELEFONO": ["912345678", "923456789", "934567890", "945678901", "956789012", "967890123"],
        }
    )
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame({"detalle": ["ignorar"]}).to_excel(writer, sheet_name="DETALLE", index=False)
        source.to_excel(writer, sheet_name="MASIVIDAD 1709", index=False)
    buffer.seek(0)
    return buffer


def validate_service() -> BytesIO:
    original_fetch = sms_itau_vencida.ejecutivos_repo.fetch_by_mandante_and_nombre
    original_list = sms_itau_vencida.ejecutivos_repo.list_ejecutivos
    try:
        sms_itau_vencida.ejecutivos_repo.fetch_by_mandante_and_nombre = lambda mandante, nombre: _fake_ejecutivo(nombre)
        sms_itau_vencida.ejecutivos_repo.list_ejecutivos = lambda mandante=None, activos=True: [_fake_ejecutivo()]

        workbook = _origin_workbook()
        outputs = build_itau_vencida_outputs(workbook, "AXIA")
    finally:
        sms_itau_vencida.ejecutivos_repo.fetch_by_mandante_and_nombre = original_fetch
        sms_itau_vencida.ejecutivos_repo.list_ejecutivos = original_list

    assert outputs.sheet_name == "MASIVIDAD 1709"
    assert outputs.sms_output is not None
    assert len(outputs.sms_crm_source) == 4
    assert set(outputs.mail_outputs) == {"ITAU_VENCIDA_MAIL", "ITAU_VENCIDA_MAIL_100998"}
    assert set(outputs.mail_outputs["ITAU_VENCIDA_MAIL"]["message_id"].astype(str)) == {"84824"}
    assert set(outputs.mail_outputs["ITAU_VENCIDA_MAIL_100998"]["message_id"].astype(str)) == {"100998"}
    assert len(outputs.sms_output) == 28, "Cuatro SMS deben incluir 24 semillas mas 4 filas"
    messages = " ".join(outputs.sms_output["MENSAJE"].astype(str).tolist()).lower()
    assert "mora" in messages
    assert "proximo a vencer" in messages
    assert "pendiente" in messages
    assert "alternativa preaprobada" in messages
    return _origin_workbook()


def validate_route(workbook: BytesIO) -> None:
    original_fetch = sms_itau_vencida.ejecutivos_repo.fetch_by_mandante_and_nombre
    original_list = sms_itau_vencida.ejecutivos_repo.list_ejecutivos
    try:
        sms_itau_vencida.ejecutivos_repo.fetch_by_mandante_and_nombre = lambda mandante, nombre: _fake_ejecutivo(nombre)
        sms_itau_vencida.ejecutivos_repo.list_ejecutivos = lambda mandante=None, activos=True: [_fake_ejecutivo()]

        response = app.test_client().post(
            "/itau-vencida/generar",
            data={
                "file": (workbook, "origen.xlsx"),
                "tipo_salida": "AXIA",
                "include_crm_sms": "on",
                "crm_sms_fecha": "2026-09-25",
                "crm_sms_hora_inicio": "10:00",
                "crm_sms_hora_fin": "11:00",
                "include_crm_mail": "on",
                "crm_mail_fecha": "2026-09-25",
                "crm_mail_hora_inicio": "12:00",
                "crm_mail_hora_fin": "13:00",
            },
            content_type="multipart/form-data",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
    finally:
        sms_itau_vencida.ejecutivos_repo.fetch_by_mandante_and_nombre = original_fetch
        sms_itau_vencida.ejecutivos_repo.list_ejecutivos = original_list

    assert response.status_code == 200, response.get_data(as_text=True)
    with zipfile.ZipFile(BytesIO(response.data)) as archive:
        names = set(archive.namelist())
    expected_tokens = {
        "carga_AXIA_SMS_ITAU_VENCIDA_",
        "84824_ITAU_VENCIDA_COBRANZA_",
        "100998_EMAIL_CAMPANA_ITAU_VIGENTE_",
        "carga_CRM_SMS_ITAU_VENCIDA_",
        "carga_CRM_MAIL_ITAU_VENCIDA_",
    }
    for token in expected_tokens:
        assert any(name.startswith(token) for name in names), f"Falta artefacto con prefijo {token}"
    assert any(name.endswith(".csv") and name.startswith("carga_AXIA_SMS") for name in names)
    assert any(name.endswith(".csv") and name.startswith("carga_CRM_SMS") for name in names)
    assert any(name.endswith(".csv") and name.startswith("carga_CRM_MAIL") for name in names)


def validate_header_aliases() -> None:
    months = {
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
    }
    carterizado_aliases = HEADER_ALIASES["CARTERIZADO"]
    assert months.issubset({alias.removeprefix("carterizado") for alias in carterizado_aliases if alias.startswith("carterizado")})
    assert {"telefonott", "fonott"}.issubset(HEADER_ALIASES["TELEFONO"])


def main() -> None:
    validate_header_aliases()
    workbook = validate_service()
    validate_route(workbook)
    print("ITAU_VENCIDA_OK")


if __name__ == "__main__":
    main()
