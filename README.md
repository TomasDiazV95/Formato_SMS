# Formato_SMS
Formato carga SMS CRM y Proveedor 

## Estructura modular (nueva)

Se agrego una capa de organizacion por dominios para ubicar rapido cada modulo sin romper compatibilidad con el codigo existente.

### Backend

- `modules/procesos/`: acceso modular a SMS, IVR, Mail, CRM y Santander Consumer.
- `modules/cargas/`: acceso modular a GM, Bit, Tanner, Porsche y Santander Hipotecario.
- `modules/reportes/`: modulo de reporteria.
- `modules/resultantes/`: modulo de resultantes.
- `modules/backoffice/`: modulo de catalogos y CRUD CAMPO1.

`app.py` ahora registra blueprints desde `modules/`, por lo que el punto de entrada principal queda agrupado por dominio.

### Frontend

- `react-frontend/src/modules/procesos/`: entradas de UI para SMS, IVR, Mail, CRM, Santander Consumer.
- `react-frontend/src/modules/cargas/`: entradas de UI para GM, Santander, Porsche, Bit, Tanner.
- `react-frontend/src/modules/reportes/`: entrada de Reportes.
- `react-frontend/src/modules/resultantes/`: entrada de Resultantes.
- `react-frontend/src/modules/backoffice/`: entrada de Backoffice.

`react-frontend/src/App.jsx` usa imports desde `src/modules/` para centralizar navegacion por dominio.

## Nota de compatibilidad

Las rutas y servicios existentes se mantienen operativos. Esta reorganizacion es una fase segura para mejorar ubicacion de codigo y mantenimiento.

## Santander Consumer (SQL Server)

Para el proceso `Santander Consumer -> Terreno`, configura estas variables en `.env`:

- `STC_DB_SERVER`
- `STC_DB_NAME`
- `STC_DB_USER`
- `STC_DB_PASSWORD`
- `STC_DB_DRIVER` (ejemplo: `ODBC Driver 17 for SQL Server`)

Opcionales:

- `STC_DB_TIMEOUT` (por defecto `30`)
- `STC_DB_ENCRYPT` (por defecto `no`)
- `STC_DB_TRUST_SERVER_CERT` (por defecto `yes`)
