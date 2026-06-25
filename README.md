# TabletRoom Agenda — Backend FastAPI

Microservicio que lee el calendario del *room mailbox* `tabletroom@inarco.cl` vía
Microsoft Graph (OAuth2 client credentials) y expone un JSON limpio para la tablet.

> **Regla de oro:** el `client_secret` de Microsoft vive **solo aquí**, en el backend.
> La APK Android nunca contiene credenciales; solo consume este JSON.

## Prerrequisitos en Microsoft 365 (los hace el admin del tenant)

Estos pasos NO se automatizan; se asumen resueltos antes de desplegar:

1. **App registrada en Microsoft Entra ID** (single-tenant). Obtienes `TENANT_ID`
   (Directory ID) y `CLIENT_ID` (Application ID).
2. **Permiso de aplicación `Calendars.Read`** (tipo **Application**, no Delegated)
   + **Grant admin consent**. Mínimo privilegio: NO pedir `Calendars.ReadWrite`.
3. **Client secret** generado en *Certificados y secretos* → se usa como `CLIENT_SECRET`.
4. **Acotar el acceso a solo esa sala** (recomendado): `Application Access Policy`
   restringiendo la app a leer únicamente `tabletroom@inarco.cl`. Sin esto la app
   podría leer todos los calendarios del tenant.

## Estructura

```
backend/
├── app/
│   ├── main.py      # endpoints /health y /agenda
│   ├── graph.py     # MSAL + llamada a Graph calendarView
│   └── config.py    # variables de entorno
├── requirements.txt
├── .env.example
├── Dockerfile
└── README.md
```

## Configuración

Copia `.env.example` a `.env` y rellena las credenciales. **`.env` está en
`.gitignore` y jamás se commitea.**

| Variable          | Descripción                                            |
| ----------------- | ------------------------------------------------------ |
| `TENANT_ID`       | Directory ID del tenant INARCO                         |
| `CLIENT_ID`       | Application ID de la app registrada                     |
| `CLIENT_SECRET`   | Secret de la app (solo backend)                        |
| `ROOM_UPN`        | Buzón de la sala (default `tabletroom@inarco.cl`)      |
| `TIMEZONE`        | Zona horaria IANA (default `America/Santiago`)         |
| `ALLOWED_ORIGINS` | Orígenes CORS permitidos, separados por coma (`*` = todos) |

## Ejecución local

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # rellenar credenciales
uvicorn app.main:app --reload
# Probar:
curl http://localhost:8000/health
curl http://localhost:8000/agenda
```

## Despliegue con Docker

```bash
cd backend
docker build -t tabletroom-agenda .
docker run -d --env-file .env -p 8000:8000 --name tabletroom-agenda tabletroom-agenda
```

Despliega en un host accesible por la tablet (p. ej. `https://agenda-api.inarco.cl`).
Se recomienda un reverse proxy con TLS delante de Uvicorn.

## Endpoints

- `GET /health` → `{"status": "ok"}` (liveness check).
- `GET /agenda` → JSON de la agenda del día. Contrato:

```json
{
  "room": "tabletroom@inarco.cl",
  "now": "2026-06-25T15:42:00-04:00",
  "status": "ocupada",
  "current": {
    "subject": "Reunión Favric",
    "organizer": "Favric",
    "start": "2026-06-25T15:30:00-04:00",
    "end": "2026-06-25T16:00:00-04:00",
    "isOnlineMeeting": true
  },
  "next": {
    "subject": "Comité técnico",
    "organizer": "...",
    "start": "2026-06-25T16:30:00-04:00",
    "end": "2026-06-25T17:00:00-04:00",
    "isOnlineMeeting": false
  },
  "events": [ "...lista completa del día..." ]
}
```

## Notas técnicas

- Se usa **`calendarView`** (no `events`) porque expande automáticamente las
  reuniones periódicas en sus instancias reales del día.
- El header `Prefer: outlook.timezone="America/Santiago"` hace que Graph devuelva
  los horarios ya convertidos a hora de Chile.
- MSAL cachea el token en memoria y lo renueva solo cuando expira: el backend no
  necesita reiniciarse para refrescar el token.
- Si Graph falla, `/agenda` responde `502` con el detalle del error.
