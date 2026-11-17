import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")


def _load_dotenv(filepath: str) -> None:
    """Carga variables desde el archivo .env si existe sin requerir paquetes externos."""
    if not os.path.exists(filepath):
        return
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            os.environ.setdefault(key, val)


_load_dotenv(ENV_FILE)


class Config:
    """Configuración base cargada desde variables de entorno (.env)."""

    SECRET_KEY: str = os.environ.get(
        "SECRET_KEY", "sierra-disenos-bordados-santa-marta-2026-key"
    )
    _db_file: str = os.environ.get("SQLITE_PATH", "sierra_taller.db")
    SQLITE_PATH: str = (
        _db_file
        if os.path.isabs(_db_file)
        else os.path.join(BASE_DIR, _db_file)
    )
    PORT: int = int(os.environ.get("PORT", "5000"))
    EMPRESA_NOMBRE: str = os.environ.get(
        "EMPRESA_NOMBRE", "Sierra Diseños y Bordados"
    )
    EMPRESA_NIT: str = os.environ.get("EMPRESA_NIT", "77166736-5")
    EMPRESA_DIRECCION: str = os.environ.get(
        "EMPRESA_DIRECCION", "Calle 18 #6-69, Santa Marta D.T.C.H."
    )
    WHATSAPP_TALLER: str = os.environ.get("WHATSAPP_TALLER", "573114046465")
    UPLOAD_FOLDER: str = os.path.join(BASE_DIR, "static", "uploads")
    MAX_CONTENT_LENGTH: int = 8 * 1024 * 1024  # 8 MB max upload
