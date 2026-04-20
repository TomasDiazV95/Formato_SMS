# Formato_SMS
Formato carga SMS CRM y Proveedor 

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
