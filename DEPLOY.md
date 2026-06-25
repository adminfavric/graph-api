# Despliegue en el VPS — `graph-api.favric.cl`

Guía paso a paso para levantar el backend FastAPI en el VPS con Docker Compose
detrás de Nginx con TLS (Let's Encrypt).

> DNS: `graph-api.favric.cl` ya apunta a la IP del VPS (hecho).
> El contenedor escucha **solo** en `127.0.0.1:8011`; Nginx es el único expuesto.
> (Puerto host 8011 porque el 8000 ya lo usa `ms-catalogue-web-1` en este VPS;
> el puerto interno del contenedor sigue siendo 8000.)

---

## 1. Requisitos en el VPS (una sola vez)

```bash
# Docker + plugin de Compose
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # re-loguear para que aplique

# Nginx + Certbot
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx git
```

## 2. Clonar el repositorio

```bash
cd /opt
sudo git clone https://github.com/adminfavric/graph-api.git
sudo chown -R $USER:$USER graph-api
cd graph-api
```

## 3. Crear el archivo `.env` en el servidor

El `.env` **no** viene en el repo (está en `.gitignore`). Se crea a mano en el VPS:

```bash
cat > .env <<'EOF'
TENANT_ID=55f789bd-7963-434e-8edc-71bf2c6fbd9d
CLIENT_ID=d5887325-e459-49e9-9726-f3f5436acfbd
CLIENT_SECRET=pega-aqui-el-secret
ROOM_UPN=tabletroom@inarco.cl
TIMEZONE=America/Santiago
ALLOWED_ORIGINS=*
EOF

chmod 600 .env   # solo el dueño puede leerlo
```

> ⚠️ Si el `CLIENT_SECRET` se expuso en algún chat/log, **rótalo** en
> Entra ID → *Certificados y secretos* y pega el nuevo aquí.

## 4. Levantar el contenedor

```bash
docker compose up -d --build
docker compose ps          # debe verse "healthy" tras ~15 s
docker compose logs -f     # Ctrl-C para salir

# Probar localmente (dentro del VPS):
curl http://127.0.0.1:8011/health     # {"status":"ok"}
curl http://127.0.0.1:8011/agenda     # JSON real de la sala
```

Si `/agenda` devuelve 502, revisar credenciales del `.env` y que el admin haya
dado **admin consent** al permiso `Calendars.Read` (Application).

## 5. Nginx + certificado TLS

```bash
# 5a. Obtener el certificado (el sitio por defecto de Nginx sirve el reto ACME)
sudo certbot certonly --webroot -w /var/www/html -d graph-api.favric.cl

# 5b. Activar la conf del reverse proxy (incluida en el repo)
sudo cp deploy/nginx-graph-api.favric.cl.conf \
        /etc/nginx/sites-available/graph-api.favric.cl
sudo ln -s /etc/nginx/sites-available/graph-api.favric.cl \
           /etc/nginx/sites-enabled/graph-api.favric.cl
sudo rm -f /etc/nginx/sites-enabled/default   # opcional: quitar el sitio por defecto

# 5c. Validar y recargar
sudo nginx -t
sudo systemctl reload nginx
```

La renovación del certificado es automática (timer de certbot). Probar con:
`sudo certbot renew --dry-run`.

## 6. Verificación final (desde fuera del VPS)

```bash
curl https://graph-api.favric.cl/health    # {"status":"ok"}
curl https://graph-api.favric.cl/agenda     # JSON de la agenda
```

Esta es la URL que ya viene compilada dentro de la APK
(`--dart-define=BACKEND_URL=https://graph-api.favric.cl`).

---

## Operación

| Acción                         | Comando                                             |
| ------------------------------ | --------------------------------------------------- |
| Ver estado                     | `docker compose ps`                                 |
| Ver logs                       | `docker compose logs -f`                            |
| Reiniciar                      | `docker compose restart`                            |
| Actualizar tras `git pull`     | `git pull && docker compose up -d --build`          |
| Detener                        | `docker compose down`                               |
| Editar credenciales            | editar `.env` y `docker compose up -d` (re-lee env) |

> El token de Microsoft Graph se renueva solo (MSAL lo cachea en memoria); no hay
> que reiniciar el contenedor para refrescarlo.
