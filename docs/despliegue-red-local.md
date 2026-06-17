# Despliegue En Red Local

## URL operativa

Con IP fija del servidor:

```text
http://192.168.1.6:5013
```

## Backend

Desde la raiz del proyecto:

```bash
python app.py
```

La app escucha en `0.0.0.0:5013`, por lo que acepta conexiones desde otros equipos de la red.

## Frontend

`react-frontend/.env.production` debe apuntar a la IP fija:

```env
VITE_API_BASE_URL=http://192.168.1.6:5013
```

Recompilar despues de cambiar esa URL:

```bash
cd react-frontend
npm run build
```

## Firewall

En Windows, permitir entrada TCP al puerto `5013` en red privada/local.

## Variables locales

El archivo `.env` debe existir en la raiz del proyecto y contener las variables `STC_DB_*` y `RESULT_DB_*` necesarias.

No subir `.env` a Git.

## Prueba rapida

Desde otro PC:

```text
http://192.168.1.6:5013
```

Si la pagina carga pero los procesos fallan, revisar `.env` y conectividad a SQL Server/MySQL Resultantes desde el servidor.
