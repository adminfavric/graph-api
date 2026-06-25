import datetime as dt
import time
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from . import config, graph, monitor, observability

_basic = HTTPBasic(auto_error=False)

observability.setup_logging()

app = FastAPI(title="TabletRoom Agenda API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Registra cada petición (método, ruta, status, duración) en log + anillo."""
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 1)

    # El handler de /agenda deja aquí el detalle si Graph falló.
    error = getattr(request.state, "error", None)

    event = {
        "time": dt.datetime.now(ZoneInfo(config.TIMEZONE)).isoformat(),
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "duration_ms": duration_ms,
    }
    if error:
        event["error"] = error

    observability.record(event)
    log = observability.logger.warning if response.status_code >= 400 else observability.logger.info
    log(
        "%s %s -> %s (%sms)%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        f" ERROR={error}" if error else "",
    )
    return response


def _parse(graph_dt: dict) -> dt.datetime:
    # Graph entrega {"dateTime": "2026-06-25T15:00:00.0000000", "timeZone": "America/Santiago"}
    raw = graph_dt["dateTime"].split(".")[0]
    tz = ZoneInfo(graph_dt.get("timeZone", config.TIMEZONE))
    return dt.datetime.fromisoformat(raw).replace(tzinfo=tz)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/monitor", response_class=HTMLResponse)
async def monitor_page(credentials: HTTPBasicCredentials = Depends(_basic)):
    """Panel web con las últimas consultas y errores. Login por HTTP Basic Auth."""
    monitor.check_auth(credentials)
    return HTMLResponse(monitor.render_html())


@app.get("/debug/recent")
async def debug_recent(token: str = ""):
    """Últimos eventos (consultas y errores). Protegido por DEBUG_TOKEN.

    Si DEBUG_TOKEN no está configurado o el token no coincide, responde 404
    para no revelar la existencia del endpoint.
    """
    if not config.DEBUG_TOKEN or token != config.DEBUG_TOKEN:
        raise HTTPException(status_code=404, detail="Not Found")
    return {
        "count": len(observability.RECENT),
        "events": list(observability.RECENT),
    }


@app.get("/agenda")
async def agenda(request: Request):
    try:
        raw_events = await graph.fetch_room_events()
    except Exception as exc:  # noqa: BLE001
        # Guardar el detalle para que el middleware lo registre y devolver 502.
        request.state.error = str(exc)
        observability.logger.exception("Fallo al consultar Microsoft Graph")
        raise HTTPException(status_code=502, detail=str(exc))

    tz = ZoneInfo(config.TIMEZONE)
    now = dt.datetime.now(tz)

    events = []
    current = None
    next_event = None

    for ev in raw_events:
        start = _parse(ev["start"])
        end = _parse(ev["end"])
        item = {
            "subject": ev.get("subject") or "(Sin título)",
            "organizer": (ev.get("organizer", {})
                          .get("emailAddress", {})
                          .get("name", "")),
            "start": start.isoformat(),
            "end": end.isoformat(),
            "isOnlineMeeting": ev.get("isOnlineMeeting", False),
        }
        events.append(item)

        if start <= now < end and current is None:
            current = item
        elif start > now and next_event is None:
            next_event = item

    return {
        "room": config.ROOM_UPN,
        "now": now.isoformat(),
        "status": "ocupada" if current else "libre",
        "current": current,
        "next": next_event,
        "events": events,
    }
