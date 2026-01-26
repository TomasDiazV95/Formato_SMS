# config.py
import re

MASIVIDAD_COLUMNS = [
    'INSTITUCIÓN','SEGMENTOINSTITUCIÓN','message_id','NOMBRE','RUT','OPERACION',
    'FECHA_VENCIMIENTO_CUOTA','MONTO_CUOTA','FECHA_ARCHIVO','FONO_EJECUTIVA',
    'FECHA_ENTREGA','dest_email','name_from','mail_from','CORREO_EJECUTIVA'
]

EJECUTIVOS = [
    {"name_from": "Daniela Cañicul", "CORREO_EJECUTIVA": "dcanicul@phoenixservice.cl", "mail_from": "dcanicul@info.phoenixserviceinfo.cl"},
    {"name_from": "Paula Alarcon",   "CORREO_EJECUTIVA": "palarcon@phoenixservice.cl", "mail_from": "palarcon@info.phoenixserviceinfo.cl"},
    {"name_from": "Claudia Sandoval","CORREO_EJECUTIVA": "csandoval@phoenixservice.cl","mail_from": "csandoval@info.phoenixserviceinfo.cl"},
    {"name_from": "Erika Alderete",  "CORREO_EJECUTIVA": "Ealderete@phoenixservice.cl","mail_from": "Ealderete@info.phoenixserviceinfo.cl"},
    {"name_from": "Yessenia Salinas","CORREO_EJECUTIVA": "ysalinas@phoenixservice.cl", "mail_from": "ysalinas@info.phoenixserviceinfo.cl"},
    {"name_from": "Paulina Ortiz",   "CORREO_EJECUTIVA": "portiz@phoenixservice.cl",  "mail_from": "portiz@estandar.phoenixserviceinfo.cl"},
    {"name_from": "Pamela Alamos",   "CORREO_EJECUTIVA": "palamos@phoenixservice.cl", "mail_from": "palamos@info.phoenixserviceinfo.cl"},
    {"name_from": "Luis Toledo",     "CORREO_EJECUTIVA": "ltoledo@phoenixservice.cl", "mail_from": "ltoledo@info.phoenixserviceinfo.cl"},
]

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
