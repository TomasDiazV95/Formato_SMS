from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    from modules import (
        backoffice_bp,
        bit_bp,
        crm_bp,
        gm_bp,
        gm_mail_bp,
        ivr_bp,
        mail_bp,
        porsche_bp,
        resultantes_bp,
        sant_hipotecario_bp,
        santander_consumer_bp,
        sc_telefonia_mail_bp,
        sms_bp,
        tanner_bp,
    )
    from services import sms_itau_vencida
    from repositories import ejecutivos_repo, resultantes_repo
    from services import mail_templates
    from services import gm_mail_templates
    from services import sc_telefonia_mail_templates
    from services import santander_consumer_templates
    from modules.procesos.sms.routes import _crm_rule_for_sms
    from modules.procesos.ivr.routes import _crm_rule_for_ivr
    from modules.procesos.mail.routes import _crm_rule_for_mail
    from utils import paths

    assert all(
        [
            backoffice_bp,
            bit_bp,
            crm_bp,
            gm_bp,
            gm_mail_bp,
            ivr_bp,
            mail_bp,
            porsche_bp,
            resultantes_bp,
            sant_hipotecario_bp,
            santander_consumer_bp,
            sc_telefonia_mail_bp,
            sms_bp,
            tanner_bp,
        ]
    )
    assert paths.CONFIG_DIR.exists(), "No existe config/"
    assert paths.DATA_DIR.exists(), "No existe data/"
    assert paths.PROJECT_ROOT.exists(), "No existe PROJECT_ROOT"

    assert mail_templates.MAIL_TEMPLATE_OPTIONS, "Sin opciones Mail"
    assert len(mail_templates._load_itau_seed_rows()) > 0, "Sin semillas Mail Itau"
    assert gm_mail_templates.list_gm_mail_templates(), "Sin templates GM Mail"
    assert sc_telefonia_mail_templates.list_sc_telefonia_mail_templates(), "Sin templates SC Telefonia Mail"
    assert santander_consumer_templates.SANTANDER_CONSUMER_TEMPLATES, "Sin templates Santander Consumer"

    sms_config = sms_itau_vencida.load_itau_sms_config()
    assert sms_config and sms_config.get("templates"), "Sin config SMS Itau"
    assert sms_itau_vencida.load_itau_seed_rows(), "Sin semillas SMS Itau"
    assert _crm_rule_for_sms("General Motors") == ("jriveros", "SMS"), "Regla CRM SMS GM invalida"
    assert _crm_rule_for_sms("CAJA18") is None, "CAJA18 no debe tener regla CRM SMS"
    assert _crm_rule_for_sms("Itau Vencida") == ("VDAD", "ENVIO SIN RESPUESTA"), "Regla CRM SMS Itau invalida"
    assert _crm_rule_for_ivr("Santander Consumer Telefonía") == ("jriveros", ""), "Regla CRM IVR Santander invalida"
    assert _crm_rule_for_ivr("General Motors") == ("jriveros", "IVR"), "Regla CRM IVR GM invalida"
    assert _crm_rule_for_mail("Itau Vencida") == ("VDAD", "ENVIO SIN RESPUESTA"), "Regla CRM Mail Itau invalida"
    assert _crm_rule_for_mail("Santander Consumer Judicial") == ("jriveros", ""), "Regla CRM Mail SCJ invalida"
    assert _crm_rule_for_mail("General Motors") == ("jriveros", "ENVIO MAIL"), "Regla CRM Mail GM invalida"
    assert _crm_rule_for_mail("Santander Consumer Telefonía") is None, "Telefonia no debe generar CRM Mail"

    assert hasattr(ejecutivos_repo, "fetch_by_mandante_and_nombre")
    assert hasattr(resultantes_repo, "fetch_tanner_resultantes")
    print("RUNTIME_OK")


if __name__ == "__main__":
    main()
