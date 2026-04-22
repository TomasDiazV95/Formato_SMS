# Runbook Operativo - Formato_SMS

Guia rapida para operar, diagnosticar y recuperar el sistema en ambiente local/operativo.

## 1) Arranque estandar

Backend:

```bash
python app.py
```

Frontend (si se requiere rebuild):

```bash
cd react-frontend
npm run build
```

URL principal:

- `http://localhost:5013`

## 1.1) Mapa rapido de codigo (arquitectura modular)

Backend:

- `modules/procesos/` -> SMS, IVR, Mail, CRM, Santander Consumer.
- `modules/cargas/` -> GM, BIT, Tanner, Porsche, Santander Hipotecario.
- `modules/reportes/`, `modules/resultantes/`, `modules/backoffice/`.

Frontend:

- `react-frontend/src/modules/procesos/`
- `react-frontend/src/modules/cargas/`
- `react-frontend/src/modules/reportes/`
- `react-frontend/src/modules/resultantes/`
- `react-frontend/src/modules/backoffice/`
- `react-frontend/src/modules/home/`

Nota:

- La estructura legacy de `routes/` y `react-frontend/src/pages/` fue retirada en la limpieza final.

## 2) Checklist pre-operacion

- Validar que exista `react-frontend/dist/index.html`.
- Validar acceso a MySQL principal (`DB_HOST`, `DB_PORT`, `DB_NAME`).
- Validar que endpoints base respondan: `/reportes/costos`, `/reportes/historial`.
- Si se usa resultantes, validar `RESULT_DB_ENABLED=1` y credenciales del origen externo.

## 3) Troubleshooting rapido

- `Error React build no encontrado`:
  - Ejecutar `npm install && npm run build` en `react-frontend/`.

- `No se pudo obtener historial/costos`:
  - Revisar conexion DB principal en `.env`.
  - Confirmar tablas `masividades_log` y `masividades_detalle`.

- `CRM multiusuario no genera ZIP`:
  - Confirmar modo `sms_ivr`.
  - Confirmar checkbox `multi_usuarios`.
  - Verificar columna de usuario en archivo (`USUARIO`, `USUARIO_CRM`, `AGENTE`, `EJECUTIVO`).

- `Resultantes vacias`:
  - Verificar `RESULT_DB_ENABLED`.
  - Verificar cartera/queries para mandante.
  - Confirmar rango de fechas con datos reales.

- `Descarga falla o nombre de archivo inesperado`:
  - Revisar `Content-Disposition` del endpoint.
  - Validar que el frontend no este usando build antiguo en cache.

## 4) Monitoreo operativo manual

- Revisar historial por proceso desde UI (`SMS`, `IVR`, `Mail`).
- Revisar resumen de costos en `/reportes`.
- Revisar backoffice de catalogos en `/backoffice/catalogos` para inconsistencias de mandantes/procesos.

## 5) Cambios y despliegue

1. Actualizar codigo backend/frontend.
2. Ejecutar lint/build frontend.
3. Probar flujo minimo: SMS -> CRM, IVR -> CRM, Mail -> CRM, Reportes.
4. Registrar avances en `cambios/` usando la plantilla semanal.
5. Si se mueve codigo de modulo, validar imports cruzados y ejecutar build/import check antes de commit.

## 6) Flujo minimo de validacion funcional

- SMS: generar Athenas/AXIA y descargar.
- IVR: generar archivo y descargar.
- Mail: generar plantilla y descargar.
- CRM: generar en modo `sms_ivr` y `mail`.
- Reportes: descargar totales, por mandante y detalle.
- Resultantes: descargar Tanner/Porsche.

## 7) Contacto tecnico

- Responsable funcional: equipo de operaciones Phoenix.
- Responsable tecnico: equipo de desarrollo del proyecto Formato_SMS.
