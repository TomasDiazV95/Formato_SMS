# Frontend React (Vite)

SPA para los modulos operativos del sistema Formato_SMS.

## Scripts

- `npm run dev`: levanta Vite en modo desarrollo.
- `npm run build`: compila a `dist/`.
- `npm run preview`: sirve build local para validacion.
- `npm run lint`: ejecuta ESLint.

## Integracion con Flask

- Flask sirve el build desde `react-frontend/dist`.
- Rutas SPA principales: `/`, `/procesos/*`, `/cargas/*`, `/reportes`, `/resultantes`, `/backoffice/catalogos`.
- APIs se consumen con Axios usando `VITE_API_BASE_URL` (default: `http://localhost:5013`).

## Estructura principal

- `src/pages/`: vistas por modulo.
- `src/api/`: clientes Axios por dominio (`sms`, `ivr`, `mail`, `crm`, `reports`, `resultantes`, `backoffice`).
- `src/components/`: componentes UI reutilizables.
- `src/data/`: constantes de mandantes, plantillas y opciones.

## Flujo recomendado de cambios

1) Desarrollar en `npm run dev`.
2) Validar con `npm run lint`.
3) Compilar con `npm run build`.
4) Probar en Flask (`python app.py`) para confirmar integracion final.
