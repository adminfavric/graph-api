"""Panel web /monitor: render HTML de los últimos eventos (consultas + errores)."""
import html
import secrets

from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials

from . import config, observability


def check_auth(credentials: HTTPBasicCredentials | None) -> None:
    """Valida HTTP Basic Auth contra MONITOR_USER/MONITOR_PASSWORD.

    - Si no hay clave configurada → 404 (panel deshabilitado, no se revela).
    - Si faltan o no coinciden credenciales → 401 con desafío Basic.
    """
    if not config.MONITOR_PASSWORD:
        raise HTTPException(status_code=404, detail="Not Found")
    unauthorized = HTTPException(
        status_code=401,
        detail="No autorizado",
        headers={"WWW-Authenticate": 'Basic realm="TabletRoom Monitor"'},
    )
    if credentials is None:
        raise unauthorized
    user_ok = secrets.compare_digest(credentials.username, config.MONITOR_USER)
    pass_ok = secrets.compare_digest(credentials.password, config.MONITOR_PASSWORD)
    if not (user_ok and pass_ok):
        raise unauthorized


def _status_color(status: int) -> str:
    if status >= 500:
        return "#B3261E"  # rojo
    if status >= 400:
        return "#E8710A"  # naranjo
    return "#1E8E3E"      # verde


def render_html() -> str:
    events = list(observability.RECENT)
    total = len(events)
    errors = [e for e in events if e.get("status", 0) >= 400 or e.get("error")]
    last_error = errors[-1] if errors else None

    rows = []
    for e in reversed(events):  # más recientes arriba
        status = e.get("status", 0)
        err = e.get("error", "")
        rows.append(
            "<tr>"
            f"<td class='mono'>{html.escape(str(e.get('time', '')))}</td>"
            f"<td>{html.escape(str(e.get('method', '')))}</td>"
            f"<td class='mono'>{html.escape(str(e.get('path', '')))}</td>"
            f"<td><span class='badge' style='background:{_status_color(status)}'>{status}</span></td>"
            f"<td class='num'>{html.escape(str(e.get('duration_ms', '')))} ms</td>"
            f"<td class='err'>{html.escape(str(err))}</td>"
            "</tr>"
        )
    rows_html = "\n".join(rows) or (
        "<tr><td colspan='6' class='empty'>Sin eventos todavía. "
        "Haz una consulta a <code>/agenda</code> y refresca.</td></tr>"
    )

    err_banner = ""
    if last_error:
        msg = last_error.get("error") or f"HTTP {last_error.get('status')}"
        err_banner = (
            f"<div class='alert'>Último error ({html.escape(str(last_error.get('time', '')))}): "
            f"{html.escape(str(msg))}</div>"
        )

    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="10">
<title>TabletRoom · Monitor</title>
<style>
  :root {{ color-scheme: dark; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; background:#121212; color:#e8e8e8;
         font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; }}
  header {{ padding:18px 24px; background:#1c1c1c; border-bottom:1px solid #2a2a2a;
           display:flex; align-items:baseline; gap:16px; flex-wrap:wrap; }}
  header h1 {{ font-size:18px; margin:0; }}
  header .sub {{ color:#9aa0a6; font-size:13px; }}
  .cards {{ display:flex; gap:16px; padding:16px 24px; flex-wrap:wrap; }}
  .card {{ background:#1c1c1c; border:1px solid #2a2a2a; border-radius:10px;
          padding:14px 18px; min-width:140px; }}
  .card .k {{ color:#9aa0a6; font-size:12px; text-transform:uppercase; letter-spacing:.04em; }}
  .card .v {{ font-size:26px; font-weight:700; margin-top:4px; }}
  .alert {{ margin:0 24px 8px; background:#3a1413; border:1px solid #B3261E;
           color:#ffd9d6; padding:10px 14px; border-radius:8px; font-size:14px; }}
  table {{ width:calc(100% - 48px); margin:8px 24px 32px; border-collapse:collapse; font-size:13px; }}
  th, td {{ text-align:left; padding:8px 10px; border-bottom:1px solid #262626; vertical-align:top; }}
  th {{ color:#9aa0a6; font-weight:600; position:sticky; top:0; background:#121212; }}
  .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; color:#cfd3d7; }}
  .num {{ text-align:right; white-space:nowrap; color:#cfd3d7; }}
  .err {{ color:#ff9d97; max-width:520px; word-break:break-word; }}
  .badge {{ display:inline-block; min-width:34px; text-align:center; padding:2px 8px;
           border-radius:20px; color:#fff; font-weight:700; }}
  .empty {{ color:#9aa0a6; text-align:center; padding:24px; }}
  code {{ background:#262626; padding:1px 5px; border-radius:4px; }}
  footer {{ color:#6b7177; font-size:12px; padding:0 24px 24px; }}
</style>
</head>
<body>
  <header>
    <h1>TabletRoom · Monitor</h1>
    <span class="sub">Sala: {html.escape(config.ROOM_UPN)} · se refresca cada 10 s</span>
  </header>
  <div class="cards">
    <div class="card"><div class="k">Eventos</div><div class="v">{total}</div></div>
    <div class="card"><div class="k">Errores</div><div class="v" style="color:#ff9d97">{len(errors)}</div></div>
    <div class="card"><div class="k">Buffer</div><div class="v">{config.RECENT_BUFFER_SIZE}</div></div>
  </div>
  {err_banner}
  <table>
    <thead>
      <tr><th>Hora</th><th>Método</th><th>Ruta</th><th>Status</th><th>Duración</th><th>Error</th></tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>
  <footer>Mostrando los últimos {total} eventos en memoria. Los logs en disco se conservan {config.LOG_RETENTION_DAYS} días.</footer>
</body>
</html>"""
