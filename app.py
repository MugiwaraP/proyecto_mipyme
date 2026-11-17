import os
from flask import Flask, flash, redirect, request, url_for
from config import Config
from models.database import Database
from services.auth_service import AuthService
from services.pedido_service import PedidoService
from services.inventario_service import InventarioService
from controllers.auth_controller import AuthController
from controllers.pedido_controller import PedidoController
from controllers.inventario_controller import InventarioController
from controllers.api_controller import ApiController


def create_app(config_class=Config) -> Flask:
    """Inicializa la aplicación Flask conectando las capas models, services y controllers."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 1. Capa de Modelos y Base de Datos (models/)
    db = Database(app.config["SQLITE_PATH"])
    db.init_db()
    app.teardown_appcontext(db.close_connection)

    # 2. Capa de Servicios de Negocio (services/)
    auth_service = AuthService(db)
    pedido_service = PedidoService(db)
    inventario_service = InventarioService(db)

    # 3. Capa de Controladores (controllers/)
    AuthController(auth_service).register_routes(app)
    PedidoController(pedido_service).register_routes(app)
    InventarioController(inventario_service).register_routes(app)
    ApiController(pedido_service, inventario_service).register_routes(app)

    @app.errorhandler(413)
    def archivo_muy_grande(error):
        flash("La imagen es muy pesada (máximo 8 MB). Intenta con una foto más liviana o una captura de pantalla.", "warning")
        return redirect(request.referrer or url_for("portal_cotizacion"))

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
