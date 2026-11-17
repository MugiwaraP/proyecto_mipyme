from typing import List, Optional
from models.database import Database


class Cliente:
    """Modelo POO de la tabla 'clientes' (HU-02: Expediente Único por Cédula/NIT)."""

    def __init__(
        self,
        id: Optional[int],
        cedula: str,
        nombre: str,
        telefono: str,
        direccion: str = "",
        hilos_corporativos: str = "",
        acepta_ley1581: int = 1,
        fecha_registro: str = "",
        total_pedidos: int = 0,
        total_prendas: int = 0,
    ):
        self.id = id
        self.cedula = cedula
        self.nombre = nombre
        self.telefono = telefono
        self.direccion = direccion
        self.hilos_corporativos = hilos_corporativos
        self.acepta_ley1581 = acepta_ley1581
        self.fecha_registro = fecha_registro
        self.total_pedidos = total_pedidos
        self.total_prendas = total_prendas

    @classmethod
    def from_row(cls, row) -> Optional["Cliente"]:
        if row is None:
            return None
        keys = row.keys()
        return cls(
            id=row["id"],
            cedula=row["cedula"],
            nombre=row["nombre"],
            telefono=row["telefono"],
            direccion=row["direccion"] if "direccion" in keys else "",
            hilos_corporativos=row["hilos_corporativos"] if "hilos_corporativos" in keys else "",
            acepta_ley1581=row["acepta_ley1581"] if "acepta_ley1581" in keys else 1,
            fecha_registro=row["fecha_registro"] if "fecha_registro" in keys else "",
            total_pedidos=row["total_pedidos"] if "total_pedidos" in keys else 0,
            total_prendas=row["total_prendas"] if "total_prendas" in keys else 0,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "cedula": self.cedula,
            "nombre": self.nombre,
            "telefono": self.telefono,
            "direccion": self.direccion,
            "hilos_corporativos": self.hilos_corporativos,
            "acepta_ley1581": bool(self.acepta_ley1581),
            "fecha_registro": self.fecha_registro,
        }

    @classmethod
    def obtener_por_cedula(cls, db: Database, cedula: str) -> Optional["Cliente"]:
        conn = db.get_connection()
        row = conn.execute(
            "SELECT * FROM clientes WHERE cedula = ?", (cedula.strip(),)
        ).fetchone()
        return cls.from_row(row)

    @classmethod
    def buscar_coincidente(cls, db: Database, termino: str) -> Optional["Cliente"]:
        conn = db.get_connection()
        row = conn.execute(
            "SELECT * FROM clientes WHERE cedula = ? OR cedula LIKE ? ORDER BY id LIMIT 1",
            (termino.strip(), f"%{termino.strip()}%"),
        ).fetchone()
        return cls.from_row(row)

    @classmethod
    def listar_todos(cls, db: Database, filtro_q: str = "") -> List["Cliente"]:
        conn = db.get_connection()
        if filtro_q:
            rows = conn.execute(
                """
                SELECT c.*, COUNT(p.id) AS total_pedidos, COALESCE(SUM(p.cantidad), 0) AS total_prendas
                FROM clientes c
                LEFT JOIN pedidos p ON c.id = p.cliente_id
                WHERE c.cedula LIKE ? OR LOWER(c.nombre) LIKE ?
                GROUP BY c.id
                ORDER BY total_pedidos DESC, c.id DESC
                """,
                (f"%{filtro_q}%", f"%{filtro_q.lower()}%"),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT c.*, COUNT(p.id) AS total_pedidos, COALESCE(SUM(p.cantidad), 0) AS total_prendas
                FROM clientes c
                LEFT JOIN pedidos p ON c.id = p.cliente_id
                GROUP BY c.id
                ORDER BY total_pedidos DESC, c.id DESC
                """
            ).fetchall()
        return [cls.from_row(r) for r in rows if r is not None]

    def guardar_o_actualizar(self, db: Database) -> int:
        conn = db.get_connection()
        existente = self.obtener_por_cedula(db, self.cedula)
        if existente and existente.id is not None:
            nuevos_hilos = (
                self.hilos_corporativos
                if self.hilos_corporativos
                else existente.hilos_corporativos
            )
            nueva_dir = self.direccion if self.direccion else existente.direccion
            conn.execute(
                """
                UPDATE clientes
                SET nombre = ?, telefono = ?, direccion = ?, hilos_corporativos = ?
                WHERE id = ?
                """,
                (self.nombre, self.telefono, nueva_dir, nuevos_hilos, existente.id),
            )
            conn.commit()
            return existente.id
        else:
            cur = conn.execute(
                """
                INSERT INTO clientes
                (cedula, nombre, telefono, direccion, hilos_corporativos, acepta_ley1581, fecha_registro)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self.cedula,
                    self.nombre,
                    self.telefono,
                    self.direccion,
                    self.hilos_corporativos,
                    self.acepta_ley1581,
                    self.fecha_registro,
                ),
            )
            conn.commit()
            return cur.lastrowid
