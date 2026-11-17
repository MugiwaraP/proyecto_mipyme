from typing import Dict, List, Optional
from models.database import Database


class Pedido:
    """Modelo POO de las tablas 'pedidos' y 'historial_pedidos' (órdenes, hilos, acuerdos WhatsApp y pruebas)."""

    ESTADOS_VALIDOS = ("Cotización", "Pendiente", "En Proceso", "Listo", "Entregado")

    def __init__(
        self,
        id: Optional[int],
        cliente_id: int,
        tipo_servicio: str,
        descripcion_y_hilos: str,
        cantidad: int,
        modalidad_entrega: str,
        soporte_fiscal: str,
        estado: str,
        fecha_creacion: str,
        imagen_url: str = "",
        solicitud_original: str = "",
        acuerdo_whatsapp: str = "",
        evidencia_url: str = "",
        confirmado_por: str = "",
        fecha_confirmacion: str = "",
        cedula: str = "",
        cliente_nombre: str = "",
        cliente_telefono: str = "",
        cliente_direccion: str = "",
        hilos_corporativos: str = "",
        historial: Optional[List[Dict]] = None,
    ):
        self.id = id
        self.cliente_id = cliente_id
        self.tipo_servicio = tipo_servicio
        self.descripcion_y_hilos = descripcion_y_hilos
        self.cantidad = cantidad
        self.modalidad_entrega = modalidad_entrega
        self.soporte_fiscal = soporte_fiscal
        self.estado = estado
        self.fecha_creacion = fecha_creacion
        self.imagen_url = imagen_url
        self.solicitud_original = solicitud_original
        self.acuerdo_whatsapp = acuerdo_whatsapp
        self.evidencia_url = evidencia_url
        self.confirmado_por = confirmado_por
        self.fecha_confirmacion = fecha_confirmacion
        self.cedula = cedula
        self.cliente_nombre = cliente_nombre
        self.cliente_telefono = cliente_telefono
        self.cliente_direccion = cliente_direccion
        self.hilos_corporativos = hilos_corporativos
        self.historial = historial if historial is not None else []

    @property
    def esta_activo(self) -> bool:
        return self.estado in ("Cotización", "Pendiente", "En Proceso")

    @classmethod
    def from_row(cls, row) -> Optional["Pedido"]:
        if row is None:
            return None
        keys = row.keys()
        return cls(
            id=row["id"],
            cliente_id=row["cliente_id"] if "cliente_id" in keys else 0,
            tipo_servicio=row["tipo_servicio"],
            descripcion_y_hilos=row["descripcion_y_hilos"],
            cantidad=row["cantidad"],
            modalidad_entrega=row["modalidad_entrega"] if "modalidad_entrega" in keys else "Local",
            soporte_fiscal=row["soporte_fiscal"] if "soporte_fiscal" in keys else "Recibo de Caja",
            estado=row["estado"],
            fecha_creacion=row["fecha_creacion"],
            imagen_url=row["imagen_url"] if "imagen_url" in keys and row["imagen_url"] else "",
            solicitud_original=row["solicitud_original"] if "solicitud_original" in keys and row["solicitud_original"] else "",
            acuerdo_whatsapp=row["acuerdo_whatsapp"] if "acuerdo_whatsapp" in keys and row["acuerdo_whatsapp"] else "",
            evidencia_url=row["evidencia_url"] if "evidencia_url" in keys and row["evidencia_url"] else "",
            confirmado_por=row["confirmado_por"] if "confirmado_por" in keys and row["confirmado_por"] else "",
            fecha_confirmacion=row["fecha_confirmacion"] if "fecha_confirmacion" in keys and row["fecha_confirmacion"] else "",
            cedula=row["cedula"] if "cedula" in keys else "",
            cliente_nombre=row["cliente_nombre"] if "cliente_nombre" in keys else (row["cliente"] if "cliente" in keys else ""),
            cliente_telefono=row["cliente_telefono"] if "cliente_telefono" in keys else (row["telefono"] if "telefono" in keys else ""),
            cliente_direccion=row["cliente_direccion"] if "cliente_direccion" in keys else "",
            hilos_corporativos=row["hilos_corporativos"] if "hilos_corporativos" in keys else "",
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "cedula": self.cedula,
            "cliente": self.cliente_nombre,
            "telefono": self.cliente_telefono,
            "tipo_servicio": self.tipo_servicio,
            "descripcion_y_hilos": self.descripcion_y_hilos,
            "cantidad": self.cantidad,
            "modalidad_entrega": self.modalidad_entrega,
            "soporte_fiscal": self.soporte_fiscal,
            "estado": self.estado,
            "fecha_creacion": self.fecha_creacion,
            "imagen_url": self.imagen_url,
            "solicitud_original": self.solicitud_original,
            "acuerdo_whatsapp": self.acuerdo_whatsapp,
            "evidencia_url": self.evidencia_url,
            "confirmado_por": self.confirmado_por,
            "fecha_confirmacion": self.fecha_confirmacion,
        }

    @classmethod
    def listar_filtrados(
        cls, db: Database, q_cedula: str = "", filtro_estado: str = ""
    ) -> List["Pedido"]:
        conn = db.get_connection()
        query = """
            SELECT p.*, c.cedula, c.nombre AS cliente_nombre, c.telefono AS cliente_telefono,
                   c.direccion AS cliente_direccion, c.hilos_corporativos
            FROM pedidos p
            JOIN clientes c ON p.cliente_id = c.id
            WHERE 1=1
        """
        params = []
        if q_cedula:
            query += " AND (c.cedula LIKE ? OR LOWER(c.nombre) LIKE ? OR LOWER(p.descripcion_y_hilos) LIKE ?)"
            like_val = f"%{q_cedula.lower()}%"
            params.extend([f"%{q_cedula}%", like_val, like_val])

        if filtro_estado:
            query += " AND p.estado = ?"
            params.append(filtro_estado)

        query += """
            ORDER BY
                CASE p.estado
                    WHEN 'En Proceso' THEN 1
                    WHEN 'Pendiente' THEN 2
                    WHEN 'Cotización' THEN 3
                    WHEN 'Listo' THEN 4
                    WHEN 'Entregado' THEN 5
                    ELSE 6
                END,
                p.id DESC
        """
        rows = conn.execute(query, params).fetchall()
        return [cls.from_row(r) for r in rows if r is not None]

    @classmethod
    def listar_para_tv(cls, db: Database) -> List["Pedido"]:
        conn = db.get_connection()
        rows = conn.execute(
            """
            SELECT p.*, c.cedula, c.nombre AS cliente_nombre, c.telefono AS cliente_telefono,
                   c.direccion AS cliente_direccion, c.hilos_corporativos
            FROM pedidos p
            JOIN clientes c ON p.cliente_id = c.id
            WHERE p.estado IN ('En Proceso', 'Pendiente', 'Listo')
            ORDER BY
                CASE p.estado
                    WHEN 'En Proceso' THEN 1
                    WHEN 'Pendiente' THEN 2
                    WHEN 'Listo' THEN 3
                END,
                p.id ASC
            """
        ).fetchall()
        return [cls.from_row(r) for r in rows if r is not None]

    @classmethod
    def obtener_por_cliente(
        cls, db: Database, cliente_id: int, limite: int = 20
    ) -> List["Pedido"]:
        conn = db.get_connection()
        rows = conn.execute(
            "SELECT * FROM pedidos WHERE cliente_id = ? ORDER BY id DESC LIMIT ?",
            (cliente_id, limite),
        ).fetchall()
        return [cls.from_row(r) for r in rows if r is not None]

    def crear(self, db: Database) -> int:
        conn = db.get_connection()
        cur = conn.execute(
            """
            INSERT INTO pedidos
            (cliente_id, tipo_servicio, descripcion_y_hilos, cantidad, modalidad_entrega,
             soporte_fiscal, estado, fecha_creacion, imagen_url, solicitud_original,
             acuerdo_whatsapp, evidencia_url, confirmado_por, fecha_confirmacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self.cliente_id,
                self.tipo_servicio,
                self.descripcion_y_hilos,
                self.cantidad,
                self.modalidad_entrega,
                self.soporte_fiscal,
                self.estado,
                self.fecha_creacion,
                self.imagen_url,
                self.solicitud_original,
                self.acuerdo_whatsapp,
                self.evidencia_url,
                self.confirmado_por,
                self.fecha_confirmacion,
            ),
        )
        conn.commit()
        return cur.lastrowid

    @staticmethod
    def obtener_por_id(db: Database, pedido_id: int) -> Optional["Pedido"]:
        conn = db.get_connection()
        row = conn.execute(
            """
            SELECT p.*, c.cedula, c.nombre AS cliente_nombre, c.telefono AS cliente_telefono,
                   c.direccion AS cliente_direccion, c.hilos_corporativos
            FROM pedidos p
            JOIN clientes c ON p.cliente_id = c.id
            WHERE p.id = ?
            """,
            (pedido_id,),
        ).fetchone()
        return Pedido.from_row(row)

    @staticmethod
    def actualizar(
        db: Database,
        pedido_id: int,
        tipo_servicio: str,
        descripcion_y_hilos: str,
        cantidad: int,
        modalidad_entrega: str,
        soporte_fiscal: str,
        estado: str,
        acuerdo_whatsapp: str = "",
        evidencia_url: str = "",
        confirmado_por: str = "",
        fecha_confirmacion: str = "",
    ) -> None:
        conn = db.get_connection()
        conn.execute(
            """
            UPDATE pedidos
            SET tipo_servicio = ?,
                descripcion_y_hilos = ?,
                cantidad = ?,
                modalidad_entrega = ?,
                soporte_fiscal = ?,
                estado = ?,
                acuerdo_whatsapp = ?,
                evidencia_url = ?,
                confirmado_por = ?,
                fecha_confirmacion = ?
            WHERE id = ?
            """,
            (
                tipo_servicio,
                descripcion_y_hilos,
                max(1, cantidad),
                modalidad_entrega,
                soporte_fiscal,
                estado,
                acuerdo_whatsapp,
                evidencia_url,
                confirmado_por,
                fecha_confirmacion,
                pedido_id,
            ),
        )
        conn.commit()

    @staticmethod
    def actualizar_estado(
        db: Database,
        pedido_id: int,
        nuevo_estado: str,
        confirmado_por: Optional[str] = None,
        fecha_confirmacion: Optional[str] = None,
    ) -> None:
        conn = db.get_connection()
        if confirmado_por is not None and fecha_confirmacion is not None:
            conn.execute(
                """
                UPDATE pedidos
                SET estado = ?, confirmado_por = ?, fecha_confirmacion = ?
                WHERE id = ?
                """,
                (nuevo_estado, confirmado_por, fecha_confirmacion, pedido_id),
            )
        else:
            conn.execute(
                "UPDATE pedidos SET estado = ? WHERE id = ?", (nuevo_estado, pedido_id)
            )
        conn.commit()

    @staticmethod
    def registrar_evento_historial(
        db: Database,
        pedido_id: int,
        fecha_hora: str,
        autor: str,
        accion: str,
        resumen: str,
        archivo_url: str = "",
    ) -> None:
        """Agrega un registro inmutable en la bitácora del pedido como respaldo/prueba."""
        conn = db.get_connection()
        conn.execute(
            """
            INSERT INTO historial_pedidos
            (pedido_id, fecha_hora, autor, accion, resumen, archivo_url)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (pedido_id, fecha_hora, autor, accion, resumen, archivo_url),
        )
        conn.commit()

    @staticmethod
    def listar_historial_por_pedidos(
        db: Database, pedido_ids: List[int]
    ) -> Dict[int, List[Dict]]:
        """Obtiene en un solo query el historial cronológico de múltiples pedidos."""
        if not pedido_ids:
            return {}
        conn = db.get_connection()
        placeholders = ",".join("?" for _ in pedido_ids)
        rows = conn.execute(
            f"""
            SELECT * FROM historial_pedidos
            WHERE pedido_id IN ({placeholders})
            ORDER BY id ASC
            """,
            pedido_ids,
        ).fetchall()
        agrupado: Dict[int, List[Dict]] = {pid: [] for pid in pedido_ids}
        for row in rows:
            agrupado.setdefault(row["pedido_id"], []).append(dict(row))
        return agrupado

    @staticmethod
    def eliminar(db: Database, pedido_id: int) -> None:
        conn = db.get_connection()
        conn.execute("DELETE FROM pedidos WHERE id = ?", (pedido_id,))
        conn.commit()

    @staticmethod
    def obtener_demanda_por_servicio(db: Database) -> List[dict]:
        conn = db.get_connection()
        rows = conn.execute(
            """
            SELECT tipo_servicio,
                   COUNT(*) AS total_ordenes,
                   COALESCE(SUM(cantidad), 0) AS total_prendas
            FROM pedidos
            GROUP BY tipo_servicio
            ORDER BY total_prendas DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]
