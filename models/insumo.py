from typing import List, Optional
from models.database import Database


class Insumo:
    """Modelo POO de la tabla 'insumos' (HU-04: Conos de Hilo, Interlón y Alertas de Stock)."""

    def __init__(
        self,
        id: Optional[int],
        codigo_referencia: str,
        nombre_color: str,
        color_hex: str,
        categoria: str,
        stock_actual: int,
        stock_minimo: int,
        unidad: str = "Conos",
    ):
        self.id = id
        self.codigo_referencia = codigo_referencia
        self.nombre_color = nombre_color
        self.color_hex = color_hex
        self.categoria = categoria
        self.stock_actual = stock_actual
        self.stock_minimo = stock_minimo
        self.unidad = unidad

    @property
    def requiere_reposicion(self) -> bool:
        return self.stock_actual <= self.stock_minimo

    @property
    def estado_semaforo(self) -> str:
        return "ROJO" if self.requiere_reposicion else "VERDE"

    @classmethod
    def from_row(cls, row) -> Optional["Insumo"]:
        if row is None:
            return None
        return cls(
            id=row["id"],
            codigo_referencia=row["codigo_referencia"] or "",
            nombre_color=row["nombre_color"],
            color_hex=row["color_hex"],
            categoria=row["categoria"],
            stock_actual=row["stock_actual"],
            stock_minimo=row["stock_minimo"],
            unidad=row["unidad"],
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "codigo_referencia": self.codigo_referencia,
            "nombre_color": self.nombre_color,
            "color_hex": self.color_hex,
            "categoria": self.categoria,
            "stock_actual": self.stock_actual,
            "stock_minimo": self.stock_minimo,
            "unidad": self.unidad,
            "requiere_reposicion": self.requiere_reposicion,
            "semaforo": self.estado_semaforo,
        }

    @classmethod
    def listar_todos(cls, db: Database) -> List["Insumo"]:
        conn = db.get_connection()
        rows = conn.execute(
            """
            SELECT * FROM insumos
            ORDER BY (stock_actual <= stock_minimo) DESC, categoria, COALESCE(codigo_referencia, ''), nombre_color
            """
        ).fetchall()
        return [cls.from_row(r) for r in rows if r is not None]

    @classmethod
    def listar_por_categoria(cls, db: Database, categoria: str) -> List["Insumo"]:
        conn = db.get_connection()
        rows = conn.execute(
            "SELECT * FROM insumos WHERE categoria = ? ORDER BY COALESCE(codigo_referencia, ''), nombre_color",
            (categoria,),
        ).fetchall()
        return [cls.from_row(r) for r in rows if r is not None]

    @classmethod
    def obtener_por_id(cls, db: Database, insumo_id: int) -> Optional["Insumo"]:
        conn = db.get_connection()
        row = conn.execute(
            "SELECT * FROM insumos WHERE id = ?", (insumo_id,)
        ).fetchone()
        return cls.from_row(row)

    def crear(self, db: Database) -> int:
        conn = db.get_connection()
        codigo_db = self.codigo_referencia.strip().upper() or None
        cur = conn.execute(
            """
            INSERT INTO insumos
            (codigo_referencia, nombre_color, color_hex, categoria, stock_actual, stock_minimo, unidad)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                codigo_db,
                self.nombre_color,
                self.color_hex,
                self.categoria,
                self.stock_actual,
                self.stock_minimo,
                self.unidad,
            ),
        )
        conn.commit()
        return cur.lastrowid

    @staticmethod
    def eliminar(db: Database, insumo_id: int) -> None:
        conn = db.get_connection()
        conn.execute("DELETE FROM insumos WHERE id = ?", (insumo_id,))
        conn.commit()

    def actualizar_stock(self, db: Database, nuevo_stock: int) -> None:
        self.stock_actual = max(0, nuevo_stock)
        conn = db.get_connection()
        conn.execute(
            "UPDATE insumos SET stock_actual = ? WHERE id = ?",
            (self.stock_actual, self.id),
        )
        conn.commit()
