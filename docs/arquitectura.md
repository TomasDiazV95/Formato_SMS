# Arquitectura - Formato_SMS

Este proyecto es una aplicacion Flask + React para generar archivos operativos de SMS, IVR, Mail, CRM, cargas y resultantes.

## Componentes principales

- `app.py`: crea la app Flask, registra blueprints y sirve la SPA React.
- `frontend.py`: sirve `react-frontend/dist` y assets compilados.
- `modules/`: capa HTTP/backend por dominio.
- `services/`: reglas de negocio, transformaciones de archivos y consultas de apoyo.
- `repositories/`: acceso a datos y repositorios de consultas.
- `config/`: configuracion editable en JSON para plantillas y parametros operativos.
- `utils/`: utilidades compartidas, conexiones y exportacion Excel.
- `react-frontend/`: frontend React/Vite.
- `data/`: persistencia local pequena, actualmente catalogo CAMPO1.
- `storage/`: salidas generadas locales ignoradas por Git.
- `archive/`: respaldos historicos/legacy locales ignorados por Git.
- `scripts/`: validaciones tecnicas de configuracion y runtime.

## Backend

Los blueprints activos se registran desde `modules/__init__.py` en `app.py`.

- `modules/procesos/`: SMS, IVR, Mail, CRM y Santander Consumer.
- `modules/cargas/`: GM, BIT, Tanner, Porsche y Santander Hipotecario.
- `modules/resultantes/`: descarga de resultantes desde fuente externa.
- `modules/backoffice/`: catalogos operativos y CAMPO1.

Regla de diseno actual:

- Las rutas reciben archivos/parametros HTTP.
- Los `services/` construyen los DataFrames y archivos de salida.
- Los `repositories/` encapsulan lecturas/escrituras en bases de datos.
- `config/*.json` contiene parametros simples que no requieren cambio de codigo.
- `utils/excel_export.py` centraliza exportacion XLSX/ZIP.
- `utils/paths.py` centraliza rutas principales del proyecto.

La capa de datos activa es `repositories/`. Los wrappers legacy `services/*_repo.py` fueron retirados.

## Frontend

La UI esta en `react-frontend/src/modules/` y se enruta desde `react-frontend/src/App.jsx`.

- `/`: portal principal.
- `/procesos/*`: procesos SMS, IVR, Mail, CRM y Santander Consumer.
- `/cargas/*`: cargas GM, BIT, Tanner, Porsche y Santander Hipotecario.
- `/resultantes`: resultantes Tanner/Porsche.
- `/backoffice/catalogos`: catalogos operativos.

El build productivo queda en `react-frontend/dist` y Flask lo sirve como SPA.

## Datos y conexiones

- SQL Server (`STC_DB_*`): Santander Consumer y catalogo de ejecutivos/alias.
- MySQL externo (`RESULT_DB_*`): Resultantes.
- JSON local (`data/campo1_catalog.json`): catalogo CAMPO1.
- JSON operativo (`config/*.json`): plantillas, semillas y parametros editables.
- Fallbacks legacy en `archive/`: insumos antiguos usados solo si falta el JSON principal.

## Limites importantes

- No versionar `.env` ni credenciales.
- No versionar salidas generadas en `storage/` ni respaldos locales en `archive/`.
- No mover carpetas usadas por runtime sin actualizar paths y validar salidas.
- Mantener Resultantes activo aunque use MySQL externo.

## Direccion futura

La siguiente mejora arquitectonica recomendada es ampliar gradualmente `config/` o mover parametros administrables a Backoffice/SQL Server cuando exista necesidad operacional.

Antes de refactors mayores, ejecutar `scripts/validate_configs.py`, `scripts/validate_runtime.py`, `scripts/validate_generators.py`, `python -m compileall app.py modules services utils repositories scripts` y `npm run build`.
