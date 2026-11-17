from flask import Flask, jsonify
from config import Config
from models.insumo import Insumo
from models.pedido import Pedido
from services.pedido_service import PedidoService
from services.inventario_service import InventarioService


class ApiController:
    """Controlador de Endpoints API REST JSON (Sección 4.3 del Informe)."""

    def __init__(
        self,
        pedido_service: PedidoService,
        inventario_service: InventarioService,
    ):
        self.pedido_service = pedido_service
        self.inventario_service = inventario_service

    def register_routes(self, app: Flask) -> None:
        app.add_url_rule(
            "/api/pedidos", "api_pedidos", self.api_pedidos, methods=["GET"]
        )
        app.add_url_rule(
            "/api/insumos", "api_insumos", self.api_insumos, methods=["GET"]
        )
        app.add_url_rule(
            "/api/clientes/<cedula>",
            "api_cliente_por_cedula",
            self.api_cliente_por_cedula,
            methods=["GET"],
        )

    def api_pedidos(self):
        pedidos = Pedido.listar_filtrados(self.pedido_service.db)
        data = [p.to_dict() for p in pedidos]
        return jsonify(
            {
                "empresa": f"{Config.EMPRESA_NOMBRE} (Santa Marta)",
                "nit": Config.EMPRESA_NIT,
                "total_pedidos": len(data),
                "pedidos": data,
            }
        )

    def api_insumos(self):
        insumos = Insumo.listar_todos(self.inventario_service.db)
        insumos_dict = [i.to_dict() for i in insumos]
        alertas = [i.to_dict() for i in insumos if i.requiere_reposicion]
        return jsonify(
            {
                "empresa": f"{Config.EMPRESA_NOMBRE} (Santa Marta)",
                "total_insumos": len(insumos_dict),
                "total_alertas_stock_minimo": len(alertas),
                "alertas_reposicion": alertas,
                "insumos": insumos_dict,
            }
        )

    def api_cliente_por_cedula(self, cedula: str):
        expediente = self.pedido_service.buscar_expediente_por_cedula(cedula)
        if not expediente:
            return jsonify({"encontrado": False}), 404
        return jsonify(expediente)
