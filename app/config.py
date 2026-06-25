import os

from dotenv import load_dotenv

load_dotenv()

TENANT_ID = os.environ["TENANT_ID"]
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
ROOM_UPN = os.environ.get("ROOM_UPN", "tabletroom@inarco.cl")
TIMEZONE = os.environ.get("TIMEZONE", "America/Santiago")
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").split(",")

# --- Observabilidad / logs ---
# Carpeta de logs (se monta como volumen en docker-compose → ./logs en el host).
LOG_DIR = os.environ.get("LOG_DIR", "/app/logs")
# Días de retención: se conservan los últimos N archivos diarios y se borran solos.
LOG_RETENTION_DAYS = int(os.environ.get("LOG_RETENTION_DAYS", "3"))
# Cuántos eventos recientes guardar en memoria para el endpoint /debug/recent.
RECENT_BUFFER_SIZE = int(os.environ.get("RECENT_BUFFER_SIZE", "200"))
# Token para proteger /debug/recent. Si está vacío, el endpoint queda deshabilitado (404).
DEBUG_TOKEN = os.environ.get("DEBUG_TOKEN", "")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default"]
GRAPH_BASE = "https://graph.microsoft.com/v1.0"
