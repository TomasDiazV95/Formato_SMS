# Formato_SMS

Aplicacion operativa Flask + React para generar archivos de SMS, IVR, Mail, CRM, cargas, Santander Consumer y Resultantes.

## Documentacion

- `docs/arquitectura.md`: estructura backend/frontend y decisiones principales.
- `docs/datos.md`: fuentes de datos, conexiones, recursos runtime y respaldos.
- `docs/procesos-activos.md`: modulos activos, retirados y validacion minima.
- `docs/despliegue-red-local.md`: uso con IP fija en red local.
- `RUNBOOK_OPERATIVO.md`: guia rapida de operacion y troubleshooting.

## Estructura principal

- `app.py`: entrada Flask y registro de blueprints.
- `frontend.py`: servidor del build React.
- `modules/`: endpoints backend por dominio.
- `services/`: reglas de negocio y generacion de archivos.
- `repositories/`: acceso a datos SQL Server/MySQL externo.
- `config/`: configuracion JSON de plantillas y parametros operativos.
- `utils/`: conexiones, exportadores y utilidades compartidas.
- `react-frontend/`: SPA React/Vite.
- `data/`: persistencia local simple, actualmente CAMPO1.
- `storage/`: salidas generadas locales, ignoradas por Git.
- `archive/`: respaldos historicos/legacy locales, ignorados por Git.
- `scripts/`: validaciones tecnicas de configuracion y runtime.

## Modulos activos

- Procesos: SMS, IVR, Mail, CRM, Santander Consumer.
- Cargas: GM, BIT, Tanner, Porsche, Santander Hipotecario.
- Resultantes: Tanner y Porsche.
- Backoffice: CAMPO1 y catalogos operativos.

## Datos

- SQL Server (`STC_DB_*`): Santander Consumer y ejecutivos/alias.
- MySQL externo (`RESULT_DB_*`): Resultantes.
- JSON local: `data/campo1_catalog.json`.
- Configuracion Itau: `config/sms_itau_vencida.json` y `config/mail_itau_vencida_seeds.json` como fuente principal; TXT/Excel antiguos quedan en `archive/` como fallback temporal.

## Configuracion local

Crear `.env` desde `.env.example` y completar credenciales reales.

No versionar:

- `.env`
- `react-frontend/.env.production`
- `storage/`
- `archive/`
- `outputs/`
- `comparacion/`
- `PRUEBAS/`

## Arranque

Backend:

```bash
python app.py
```

Frontend build:

```bash
cd react-frontend
npm run build
```

URL local:

```text
http://localhost:5013
```

URL red local actual:

```text
http://192.168.1.6:5013
```

## Validacion tecnica

```bash
python -m compileall app.py modules services utils repositories
```

```bash
python scripts/validate_configs.py
```

```bash
python scripts/validate_runtime.py
```

```bash
python scripts/validate_generators.py
```

```bash
cd react-frontend
npm run build
```

## Estado de migracion

- Reportes financieros retirado.
- Depuradores retirado.
- MySQL financiero antiguo retirado.
- Resultantes sigue activo con MySQL externo.
- Ejecutivos y Santander Consumer usan SQL Server.
