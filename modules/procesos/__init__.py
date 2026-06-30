from modules.procesos.crm import crm_bp
from modules.procesos.gm_mail import gm_mail_bp
from modules.procesos.ivr import ivr_bp
from modules.procesos.mail import mail_bp
from modules.procesos.santander_consumer import santander_consumer_bp
from modules.procesos.sc_telefonia_mail import sc_telefonia_mail_bp
from modules.procesos.sms import sms_bp

__all__ = ["sms_bp", "ivr_bp", "mail_bp", "crm_bp", "gm_mail_bp", "santander_consumer_bp", "sc_telefonia_mail_bp"]
