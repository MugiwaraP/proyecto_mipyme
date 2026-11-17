from typing import Optional
from models.database import Database


class Usuario:
    """Modelo POO de la tabla 'usuarios' (HU-01: Control de Acceso por Roles)."""

    def __init__(
        self,
        id: Optional[int],
        nombre: str,
        username: str,
        password_hash: str,
        rol: str,
    ):
        self.id = id
        self.nombre = nombre
        self.username = username
        self.password_hash = password_hash
        self.rol = rol

    @property
    def es_admin(self) -> bool:
        return self.rol == "admin"

    @property
    def es_operario(self) -> bool:
        return self.rol == "operario"

    @classmethod
    def from_row(cls, row) -> Optional["Usuario"]:
        if row is None:
            return None
        return cls(
            id=row["id"],
            nombre=row["nombre"],
            username=row["username"],
            password_hash=row["password_hash"],
            rol=row["rol"],
        )

    @classmethod
    def obtener_por_username(cls, db: Database, username: str) -> Optional["Usuario"]:
        conn = db.get_connection()
        row = conn.execute(
            "SELECT * FROM usuarios WHERE LOWER(username) = ?",
            (username.strip().lower(),),
        ).fetchone()
        return cls.from_row(row)
