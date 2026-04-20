export const mandantes = [
  'Itau Vencida',
  'Itau Castigo',
  'CAJA18',
  'Banco Internacional',
  'Santander Hipotecario',
  'Santander Consumer Terreno',
  'Santander Consumer Telefonía',
  'Santander Consumer Judicial',
  'General Motors',
  'La Araucana',
  'Tanner',
]

export const formatoSalida = [
  { value: 'ATHENAS', label: 'Athenas' },
  { value: 'AXIA', label: 'AXIA' },
]

export const mailTemplates = [
  {
    code: 'ITAU_VENCIDA_MAIL',
    label: 'Itau Vencida - Mail',
    messageId: 84824,
    mandante: 'Itau Vencida',
    institucion: 'BANCO ITAU',
    segmento: 'BANCO ITAU',
  },
  {
    code: 'TANNER_MEDIOS_PAGO',
    label: 'Tanner - Medios de Pago',
    messageId: 91869,
    mandante: 'Tanner',
    institucion: 'TANNER SERVICIOS FINANCIEROS',
    segmento: 'TANNER',
  },
  {
    code: 'TANNER_CASTIGO',
    label: 'Tanner - Castigo',
    messageId: 96830,
    mandante: 'Tanner',
    institucion: 'TANNER SERVICIOS FINANCIEROS',
    segmento: 'TANNER',
  },
  {
    code: 'SCJ_COBRANZA',
    label: 'Santander Consumer Judicial - Cobranza',
    messageId: 86257,
    mandante: 'Santander Consumer Judicial',
    institucion: 'SANTANDER CONSUMER',
    segmento: 'SANTANDER CONSUMER',
  },
  {
    code: 'SC_TELEFONIA_DESCUENTO',
    label: 'Santander Consumer Telefonía - Descuento',
    messageId: 95008,
    mandante: 'Santander Consumer Telefonía',
    institucion: 'Santander Consumer',
    segmento: 'Santander Consumer',
  },
  {
    code: 'SC_TELEFONIA_MEDIOS_PAGO',
    label: 'Santander Consumer Telefonía - Medios de Pago',
    messageId: 96706,
    mandante: 'Santander Consumer Telefonía',
    institucion: 'Santander Consumer',
    segmento: 'Santander Consumer',
  },
]

export const procesosMasividad = [
  'SMS_ATHENAS',
  'SMS_AXIA',
  'IVR_ATHENAS',
  'IVR_CRM',
  'MAIL_CRM',
]

export const resultantesMandantes = [
  { code: 'TANNER', label: 'TANNER', enabled: true },
  { code: 'BIT', label: 'BIT', enabled: false },
  { code: 'LA_ARAUCANA', label: 'LA ARAUCANA', enabled: false },
  { code: 'SANTANDER_CONSUMER', label: 'SANTANDER CONSUMER', enabled: false },
  { code: 'PORSCHE', label: 'PORSCHE', enabled: true },
  { code: 'GENERAL_MOTORS', label: 'GENERAL MOTORS', enabled: false },
]
