import csv
import io
from typing import Dict
from models.database import Database
from models.insumo import Insumo
from models.pedido import Pedido


class InventarioService:
    """Servicio de negocio para el inventario de hilos/interlón, alertas de stock y analítica (HU-04)."""

    def __init__(self, db: Database):
        self.db = db

    def obtener_datos_inventario(self) -> Dict:
        insumos = Insumo.listar_todos(self.db)
        alertas = [i for i in insumos if i.requiere_reposicion]
        demanda_servicios = Pedido.obtener_demanda_por_servicio(self.db)
        total_prendas_global = (
            sum(r["total_prendas"] for r in demanda_servicios) or 1
        )
        return {
            "insumos": insumos,
            "alertas": alertas,
            "demanda_servicios": demanda_servicios,
            "total_prendas_global": total_prendas_global,
        }

    def crear_insumo(
        self,
        codigo_referencia: str,
        nombre_color: str,
        color_hex: str,
        categoria: str,
        stock_actual: int,
        stock_minimo: int,
        unidad: str,
    ) -> int:
        if not nombre_color.strip():
            raise ValueError(
                "El nombre o descripción del hilo/material es obligatorio."
            )
        insumo = Insumo(
            id=None,
            codigo_referencia=codigo_referencia.strip().upper(),
            nombre_color=nombre_color.strip(),
            color_hex=color_hex.strip(),
            categoria=categoria.strip(),
            stock_actual=max(0, stock_actual),
            stock_minimo=max(0, stock_minimo),
            unidad=unidad.strip(),
        )
        return insumo.crear(self.db)

    def ajustar_stock(self, insumo_id: int, accion: str, cantidad_fija: int = None) -> Insumo:
        insumo = Insumo.obtener_por_id(self.db, insumo_id)
        if not insumo:
            raise ValueError("Insumo no encontrado.")
        nuevo_stock = insumo.stock_actual
        if accion == "sumar":
            nuevo_stock += 1
        elif accion == "restar":
            nuevo_stock = max(0, nuevo_stock - 1)
        elif accion == "fijar" and cantidad_fija is not None:
            nuevo_stock = max(0, cantidad_fija)
        insumo.actualizar_stock(self.db, nuevo_stock)
        return insumo

    def eliminar_insumo(self, insumo_id: int) -> Insumo:
        insumo = Insumo.obtener_por_id(self.db, insumo_id)
        if not insumo:
            raise ValueError("Insumo no encontrado.")
        Insumo.eliminar(self.db, insumo_id)
        return insumo

    def generar_backup_csv(self) -> str:
        pedidos = Pedido.listar_filtrados(self.db)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "ID_Pedido",
                "Cedula_NIT",
                "Cliente",
                "Telefono",
                "Tipo_Servicio",
                "Solicitud_Original_Cliente",
                "Descripcion_y_Codigos_Hilo",
                "Acuerdo_WhatsApp_Pruebas",
                "Cantidad",
                "Entrega",
                "Soporte_Fiscal",
                "Estado",
                "Confirmado_Por",
                "Fecha_Confirmacion",
                "Boceto_Cliente_URL",
                "Prueba_Aprobada_URL",
                "Fecha_Creacion",
            ]
        )
        for p in pedidos:
            writer.writerow(
                [
                    p.id,
                    p.cedula,
                    p.cliente_nombre,
                    p.cliente_telefono,
                    p.tipo_servicio,
                    p.solicitud_original,
                    p.descripcion_y_hilos,
                    p.acuerdo_whatsapp,
                    p.cantidad,
                    p.modalidad_entrega,
                    p.soporte_fiscal,
                    p.estado,
                    p.confirmado_por,
                    p.fecha_confirmacion,
                    p.imagen_url,
                    p.evidencia_url,
                    p.fecha_creacion,
                ]
            )
        return "\ufeff" + output.getvalue()
