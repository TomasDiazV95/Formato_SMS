# Procesos Activos

## Procesos

- SMS: genera salidas Athenas/AXIA y flujo especial Itau Vencida.
- IVR: genera archivo IVR usando CAMPO1 activo.
- Mail: genera plantillas Mail activas y permite continuar a CRM.
- CRM: genera archivos CRM para SMS/IVR y Mail.
- Santander Consumer: genera Terreno desde SQL Server.

## Cargas

- GM.
- BIT.
- Tanner.
- Porsche.
- Santander Hipotecario.

## Resultantes

- Tanner: activo.
- Porsche: activo.
- Otros mandantes en UI pueden figurar deshabilitados.

## Backoffice

- Catalogo CAMPO1.
- Vista de catalogos base y plantillas Mail.

## Procesos retirados

- Reportes financieros.
- Depuradores.
- MySQL financiero antiguo.

## Validacion minima despues de cambios

Ejecutar:

```bash
python -m compileall app.py modules services utils
```

```bash
cd react-frontend
npm run build
```

Flujos a probar manualmente cuando el cambio toque logica productiva:

- SMS Itau Vencida.
- IVR con CAMPO1.
- Mail Itau/Tanner/Santander Consumer Judicial.
- CRM desde SMS/IVR y Mail.
- Santander Consumer Terreno.
- Resultantes Tanner/Porsche.
