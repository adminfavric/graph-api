import datetime as dt
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import config, graph

app = FastAPI(title="TabletRoom Agenda API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _parse(graph_dt: dict) -> dt.datetime:
    # Graph entrega {"dateTime": "2026-06-25T15:00:00.0000000", "timeZone": "America/Santiago"}
    raw = graph_dt["dateTime"].split(".")[0]
    tz = ZoneInfo(graph_dt.get("timeZone", config.TIMEZONE))
    return dt.datetime.fromisoformat(raw).replace(tzinfo=tz)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/agenda")
async def agenda():
    try:
        raw_events = await graph.fetch_room_events()
    except Exception as exc:  # noqa: BLE001
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
