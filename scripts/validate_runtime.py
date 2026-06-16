from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    from modules import backoffice_bp, cargas_bp, procesos_bp, resultantes_bp
    from modules.procesos.sms import routes as sms_routes
    from repositories import ejecutivos_repo, resultantes_repo
    from services import mail_templates
    from services import santander_consumer_templates
    from utils import paths

    assert backoffice_bp and cargas_bp and procesos_bp and resultantes_bp
    assert paths.CONFIG_DIR.exists(), "No existe config/"
    assert paths.DATA_DIR.exists(), "No existe data/"
    assert paths.PROJECT_ROOT.exists(), "No existe PROJECT_ROOT"

    assert mail_templates.MAIL_TEMPLATE_OPTIONS, "Sin opciones Mail"
    assert len(mail_templates._load_itau_seed_rows()) > 0, "Sin semillas Mail Itau"
    assert santander_consumer_templates.SANTANDER_CONSUMER_TEMPLATES, "Sin templates Santander Consumer"

    sms_config = sms_routes._load_itau_sms_config()
    assert sms_config and sms_config.get("templates"), "Sin config SMS Itau"
    assert sms_routes._load_itau_seed_rows(), "Sin semillas SMS Itau"

    assert hasattr(ejecutivos_repo, "fetch_by_mandante_and_nombre")
    assert hasattr(resultantes_repo, "fetch_tanner_resultantes")
    print("RUNTIME_OK")


if __name__ == "__main__":
    main()
