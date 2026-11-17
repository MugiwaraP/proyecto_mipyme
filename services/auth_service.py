from typing import Optional
from werkzeug.security import check_password_hash
from models.database import Database
from models.usuario import Usuario


class AuthService:
    """Servicio de negocio para autenticación y validación de roles RBAC (HU-01)."""

    def __init__(self, db: Database):
        self.db = db

    def autenticar(self, username: str, password: str) -> Optional[Usuario]:
        usuario = Usuario.obtener_por_username(self.db, username)
        if usuario and check_password_hash(usuario.password_hash, password):
            return usuario
        return None
