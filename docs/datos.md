# Arquitectura De Datos

Este documento separa datos productivos, configuracion, respaldos y archivos generados.

## SQL Server

Usado por:

- Santander Consumer Terreno.
- Catalogo de ejecutivos Phoenix.
- Alias de ejecutivos.

Variables requeridas:

- `STC_DB_SERVER`
- `STC_DB_NAME`
- `STC_DB_USER`
- `STC_DB_PASSWORD`
- `STC_DB_DRIVER`

Tablas relevantes:

- `dbo.tbl_ejecutivos_phoenix`
- `dbo.tbl_alias_ejecutivos`
- `dbo.tmp_bench_STC`
- `dbo.emails_carga`

Codigo relacionado:

- `utils/db_sqlserver.py`
- `repositories/ejecutivos_repo.py`
- `services/santander_consumer_sources.py`
- `services/santander_consumer_assignments.py`
- `services/santander_consumer_service.py`

## MySQL externo Resultantes

Usado solo por Resultantes.

Variables requeridas:

- `RESULT_DB_ENABLED`
- `RESULT_DB_HOST`
- `RESULT_DB_PORT`
- `RESULT_DB_NAME`
- `RESULT_DB_USER`
- `RESULT_DB_PASSWORD`

Codigo relacionado:

- `utils/db_resultantes.py`
- `repositories/resultantes_repo.py`
- `services/resultantes_queries/`

## JSON local

`data/campo1_catalog.json` guarda el catalogo CAMPO1 usado por IVR y administrado desde Backoffice.

## Configuracion JSON

`config/` contiene parametros editables que antes estaban hardcodeados en Python:

- `config/santander_consumer_templates.json`: plantillas Santander Consumer Terreno.
- `config/santander_consumer_supervisors.json`: supervisores para override RM/regiones.
- `config/mail_templates.json`: opciones activas de plantillas Mail.
- `config/sms_itau_vencida.json`: mensajes, equivalencias de masividad y semillas SMS Itau Vencida.
- `config/mail_itau_vencida_seeds.json`: semillas editables de Mail Itau Vencida.

Estos archivos tienen fallback en codigo para reducir riesgo operacional, pero deben mantenerse consistentes con la UI y los procesos activos.

El inventario tecnico de estos archivos se mantiene en `services/config_registry.py` y se expone en Backoffice para revisar existencia, validez JSON y cantidad de items.

Las semillas de Mail Itau Vencida actualizan `MES_CURSO` y `ANO_CURSO` en runtime usando el mes y ano actuales, aunque el JSON no incluya esos campos.

## Recursos y fallbacks legacy

La fuente principal para SMS/Mail Itau Vencida esta en `config/`.

Los respaldos legacy quedan en `archive/` y se usan solo como fallback temporal si falta el JSON:

- `archive/sms_itau_vencida_txt/`: textos y semilla TXT para SMS Itau Vencida.
- `archive/mail_itau_vencida_excel_seed/MAIL_VENCIDA_20260413.xlsx`: filas semilla Excel para Mail Itau Vencida.

El codigo conserva busqueda secundaria en `archive/` y en las rutas antiguas por compatibilidad local si reaparecen, pero no deben considerarse fuente principal. Esta decision se mantiene hasta completar pruebas operativas reales de SMS/Mail Itau Vencida.

## Respaldos operativos conservados

Estas carpetas pueden servir para soporte, trazabilidad o reconstruccion de datos, pero no todo su contenido es runtime:

- `archive/agente_phoenix/`
- `archive/asignaciones/`
- `archive/plantillas_mail_legacy/`
- `archive/resultantes_referencias/`
- `archive/cambios/`

Antes de eliminar estas carpetas, confirmar si algun proceso externo a la app las usa directamente.

## Archivos generados o locales

No deben versionarse:

- `.env`
- `react-frontend/.env.production`
- `storage/`
- `archive/`
- `outputs/`
- `comparacion/`
- `PRUEBAS/`
- capturas o imagenes temporales.

Estos archivos pueden existir localmente para operacion, pero deben quedar fuera de Git.
