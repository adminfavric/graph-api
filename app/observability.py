"""Logging a archivo con rotación diaria + anillo en memoria de eventos recientes.

- Archivo: `LOG_DIR/agenda.log`, rota a medianoche y conserva `LOG_RETENTION_DAYS`
  días (los más viejos se borran solos).
- También escribe a stdout, así que se ve en `docker compose logs`.
- `RECENT` guarda los últimos eventos para inspeccionarlos vía `GET /debug/recent`.
"""
import logging
import os
from collections import deque
from logging.handlers import TimedRotatingFileHandler

from . import config

# Anillo en memoria con los últimos eventos (consultas + errores).
RECENT: deque = deque(maxlen=config.RECENT_BUFFER_SIZE)

logger = logging.getLogger("tabletroom")


def setup_logging() -> None:
    if logger.handlers:  # evitar duplicar handlers en reload
        return
    logger.setLevel(logging.INFO)

    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    # Consola → visible en `docker compose logs`.
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    # Archivo con rotación diaria. Si el volumen no se puede escribir, seguimos
    # solo con consola (no tumbamos la app por un problema de logs).
    try:
        os.makedirs(config.LOG_DIR, exist_ok=True)
        file_handler = TimedRotatingFileHandler(
            os.path.join(config.LOG_DIR, "agenda.log"),
            when="midnight",
            backupCount=config.LOG_RETENTION_DAYS,
            encoding="utf-8",
        )
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)
    except OSError as exc:  # noqa: BLE001
        logger.warning("No se pudo abrir el log de archivo en %s: %r", config.LOG_DIR, exc)


def record(event: dict) -> None:
    """Agrega un evento al anillo en memoria."""
    RECENT.append(event)
