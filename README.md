# Formato_SMS

Plataforma interna de Phoenix Service para generar cargas masivas (SMS, IVR, Mail, CRM), reportes de costos y descarga de resultantes por mandante.

## Arquitectura

- Backend: Flask (Python) con blueprints en `routes/`.
- Frontend: React + Vite en `react-frontend/`, compilado y servido por Flask.
- Datos: MySQL principal (`utils/db.py`) y, opcionalmente, MySQL externo para resultantes (`utils/db_resultantes.py`).
- Exportaciones: XLSX/TXT/ZIP en memoria, sin archivos temporales en disco.

## Modulos principales

- `SMS`: Athenas/AXIA, mensajes personalizados y continuidad a CRM.
- `IVR`: carga Athenas + continuidad a CRM.
- `Mail`: generador de plantillas + continuidad a CRM.
- `CRM`: unificado para `sms_ivr` y `mail`, con modo multiusuario para SMS/IVR.
- `Reportes`: resumen de costos e historial por proceso.
- `Resultantes`: descarga por mandante y rango/periodo (Tanner y Porsche habilitados).
- `Backoffice`: vista inicial de catalogos (mandantes, procesos, CAMPO1 y plantillas mail).

## Estructura del repositorio

- `app.py`: bootstrap Flask, CORS, registro de blueprints y rutas SPA.
- `routes/`: endpoints HTTP por modulo.
- `services/`: reglas de negocio, builders y repositorios de datos.
- `utils/`: conexion DB, utilidades API y exportaciones Excel/ZIP.
- `react-frontend/src/`: SPA React (pages, api, components, data).
- `cambios/`: bitacora de avances y progreso diario.

## Requisitos

- Python 3.11+
- Node.js 20+
- npm 10+
- MySQL accesible para tablas de masividades

## Variables de entorno

El backend lee `.env` automaticamente en `utils/db.py` y `utils/db_resultantes.py`.

Variables principales:

- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
- `RESULT_DB_ENABLED` (`1/0`)
- `RESULT_DB_HOST`, `RESULT_DB_PORT`, `RESULT_DB_USER`, `RESULT_DB_PASSWORD`, `RESULT_DB_NAME`
- `AUTO_BUILD_FRONTEND` (`1/0`) para compilar React al iniciar Flask
- `NPM_BIN` si el ejecutable npm no esta en PATH

## Levantamiento local

1) Backend

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

2) Frontend (modo desarrollo)

```bash
cd react-frontend
npm install
npm run dev
```

3) Frontend compilado (modo integrado Flask)

```bash
cd react-frontend
npm run build
```

Luego abrir `http://localhost:5013`.

## Endpoints clave

- `POST /sms/athenas`
- `POST /ivr/process`
- `POST /mail/template`
- `POST /crm/session`
- `POST /crm/carga`
- `GET /reportes/costos`
- `GET /reportes/historial`
- `GET /resultantes/download`
- `GET /api/backoffice/catalogos`

## Notas operativas

- Si cambia cualquier codigo React, recompilar con `npm run build` para que Flask sirva la version nueva.
- Para historial de proceso, el frontend consume `/reportes/historial` con `proceso=sms|ivr|mail`.
- Si `RESULT_DB_ENABLED=0`, las resultantes se entregan vacias por diseno.

## Documentacion adicional

- Runbook operativo: `RUNBOOK_OPERATIVO.md`
- Bitacora y progreso: `cambios/`
