import datetime as dt
from zoneinfo import ZoneInfo

import httpx
import msal

from . import config

_msal_app = msal.ConfidentialClientApplication(
    config.CLIENT_ID,
    authority=config.AUTHORITY,
    client_credential=config.CLIENT_SECRET,
)


def _get_token() -> str:
    # MSAL cachea el token en memoria y lo renueva solo cuando expira.
    result = _msal_app.acquire_token_silent(config.SCOPE, account=None)
    if not result:
        result = _msal_app.acquire_token_for_client(scopes=config.SCOPE)
    if "access_token" not in result:
        raise RuntimeError(result.get("error_description", "Fallo de autenticación con Entra"))
    return result["access_token"]


async def fetch_room_events() -> list[dict]:
    tz = ZoneInfo(config.TIMEZONE)
    now = dt.datetime.now(tz)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + dt.timedelta(days=1)

    token = _get_token()
    url = f"{config.GRAPH_BASE}/users/{config.ROOM_UPN}/calendarView"
    params = {
        "startDateTime": start.isoformat(),
        "endDateTime": end.isoformat(),
        "$select": "subject,start,end,organizer,isOnlineMeeting,showAs",
        "$orderby": "start/dateTime",
        "$top": "50",
    }
    headers = {
        "Authorization": f"Bearer {token}",
        # Devuelve los horarios ya en hora de Chile en vez de UTC.
        "Prefer": f'outlook.timezone="{config.TIMEZONE}"',
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, params=params, headers=headers)

    resp.raise_for_status()
    return resp.json().get("value", [])
