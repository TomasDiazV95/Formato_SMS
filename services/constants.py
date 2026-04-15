MANDANTE_CHOICES = [
    "Itau Vencida",
    "Itau Castigo",
    "CAJA18",
    "Banco Internacional",
    "Santander Hipotecario",
    "Santander Consumer Terreno",
    "Santander Consumer Telefonía",
    "Santander Consumer Judicial",
    "General Motors",
    "La Araucana",
    "Tanner",
]

MANDANTE_SPECIAL_RULES = {
    "itau vencida": {
        "op_length": 24,
    },
    "santander hipotecario": {
        "op_length": 12,
    },
}

COLUMN_MAP = {
    "rut": {"rut", "rut+dv", "rut-dv", "rut_cliente", "id_cliente"},
    "dv": {"dv", "digito", "dígito", "dv_rut"},
    "telefono": {"telefono", "teléfono", "fono", "telefono1", "telefono_agente", "phono_agente", "fono_agente"},
    "operacion": {"operacion", "operación", "op", "op1", "ope", "oper", "nro_documento", "id_credito", "nro_operacion"},
    "mail": {"mail", "correo", "email", "dest_mail", "dest_email"},
    "mensaje": {"mensaje", "message", "sms_mensaje", "sms"},
}
