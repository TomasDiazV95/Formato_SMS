from modules.procesos import crm_bp, ivr_bp, mail_bp, santander_consumer_bp, sms_bp
from modules.cargas import bit_bp, gm_bp, porsche_bp, sant_hipotecario_bp, tanner_bp
from modules.reportes import reports_bp
from modules.resultantes import resultantes_bp
from modules.backoffice import backoffice_bp

__all__ = [
    "sms_bp",
    "ivr_bp",
    "mail_bp",
    "crm_bp",
    "santander_consumer_bp",
    "gm_bp",
    "bit_bp",
    "tanner_bp",
    "porsche_bp",
    "sant_hipotecario_bp",
    "reports_bp",
    "resultantes_bp",
    "backoffice_bp",
]
