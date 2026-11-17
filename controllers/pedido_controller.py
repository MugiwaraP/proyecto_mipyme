from flask import Flask, flash, redirect, render_template, request, session, url_for
from controllers.auth_controller import admin_required, login_required
from models.cliente import Cliente
from models.insumo import Insumo
from models.pedido import Pedido
from services.pedido_service import PedidoService


class PedidoController:
    """Controlador de pedidos, bocetos de referencia, expediente por cédula y Modo TV."""

    def __init__(self, pedido_service: PedidoService):
        self.pedido_service = pedido_service

    def register_routes(self, app: Flask) -> None:
        app.add_url_rule(
            "/", "dashboard", login_required(self.dashboard), methods=["GET"]
        )
        app.add_url_rule(
            "/pedidos/nuevo",
            "crear_pedido",
            admin_required(self.crear_pedido),
            methods=["POST"],
        )
        app.add_url_rule(
            "/pedidos/<int:pedido_id>/editar",
            "editar_pedido",
            admin_required(self.editar_pedido),
            methods=["POST"],
        )
        app.add_url_rule(
            "/pedidos/<int:pedido_id>/estado",
            "cambiar_estado_pedido",
            login_required(self.cambiar_estado_pedido),
            methods=["POST"],
        )
        app.add_url_rule(
            "/pedidos/<int:pedido_id>/eliminar",
            "eliminar_pedido",
            admin_required(self.eliminar_pedido),
            methods=["POST"],
        )
        app.add_url_rule(
            "/tv", "vista_tv", login_required(self.vista_tv), methods=["GET"]
        )
        app.add_url_rule(
            "/clientes",
            "vista_clientes",
            login_required(self.vista_clientes),
            methods=["GET"],
        )
        app.add_url_rule(
            "/cotizar",
            "portal_cotizacion",
            self.portal_cotizacion,
            methods=["GET", "POST"],
        )

    def dashboard(self):
        q_cedula = request.args.get("cedula", "").strip()
        filtro_estado = request.args.get("estado", "").strip()
        datos = self.pedido_service.obtener_datos_dashboard(q_cedula, filtro_estado)
        return render_template(
            "dashboard.html",
            q_cedula=q_cedula,
            filtro_estado=filtro_estado,
            **datos,
        )

    def crear_pedido(self):
        try:
            cantidad = int(request.form.get("cantidad", "1"))
        except ValueError:
            cantidad = 1

        try:
            usuario_nombre = session.get("nombre", "Administrador")
            archivo_img = request.files.get("imagen_referencia")
            imagen_url = self.pedido_service.guardar_archivo_adjunto(
                archivo_img, prefijo="boceto"
            )
            archivo_prueba = request.files.get("evidencia_archivo")
            evidencia_url = self.pedido_service.guardar_archivo_adjunto(
                archivo_prueba, prefijo="prueba"
            )

            self.pedido_service.crear_pedido_y_cliente(
                cedula=request.form.get("cedula", ""),
                nombre=request.form.get("nombre", ""),
                telefono=request.form.get("telefono", ""),
                direccion=request.form.get("direccion", ""),
                hilos_corporativos=request.form.get("hilos_corporativos", ""),
                acepta_ley1581=1 if request.form.get("acepta_ley1581") else 0,
                tipo_servicio=request.form.get("tipo_servicio", "Solo Bordado"),
                descripcion_y_hilos=request.form.get("descripcion_y_hilos", ""),
                cantidad=cantidad,
                modalidad_entrega=request.form.get("modalidad_entrega", "Local"),
                soporte_fiscal=request.form.get("soporte_fiscal", "Recibo de Caja"),
                estado=request.form.get("estado", "Pendiente"),
                imagen_url=imagen_url,
                acuerdo_whatsapp=request.form.get("acuerdo_whatsapp", ""),
                evidencia_url=evidencia_url,
                autor_evento=usuario_nombre,
                confirmado_por=usuario_nombre,
            )
            flash(
                f"Pedido registrado para {request.form.get('nombre')} (C.C./NIT {request.form.get('cedula')}).",
                "success",
            )
        except ValueError as exc:
            flash(str(exc), "danger")
        return redirect(url_for("dashboard"))

    def editar_pedido(self, pedido_id: int):
        try:
            cantidad = int(request.form.get("cantidad", "1"))
        except ValueError:
            cantidad = 1

        try:
            usuario_nombre = session.get("nombre", "Administrador")
            archivo_prueba = request.files.get("evidencia_archivo")
            nueva_evidencia_url = self.pedido_service.guardar_archivo_adjunto(
                archivo_prueba, prefijo="prueba"
            )
            fue_confirmado = self.pedido_service.editar_pedido(
                pedido_id=pedido_id,
                tipo_servicio=request.form.get("tipo_servicio", "Solo Bordado"),
                descripcion_y_hilos=request.form.get("descripcion_y_hilos", ""),
                cantidad=cantidad,
                modalidad_entrega=request.form.get("modalidad_entrega", "Local"),
                soporte_fiscal=request.form.get("soporte_fiscal", "Recibo de Caja"),
                estado=request.form.get("estado", "Pendiente"),
                guardar_como_hilos_cliente=bool(
                    request.form.get("guardar_hilos_cliente")
                ),
                acuerdo_whatsapp=request.form.get("acuerdo_whatsapp", ""),
                nueva_evidencia_url=nueva_evidencia_url,
                usuario_nombre=usuario_nombre,
            )
            msg = (
                f"Pedido #{pedido_id} confirmado y acuerdo guardado en el historial."
                if fue_confirmado
                else f"Pedido #{pedido_id} actualizado correctamente."
            )
            flash(msg, "success")
        except ValueError as exc:
            flash(str(exc), "danger")
        return redirect(url_for("dashboard"))

    def cambiar_estado_pedido(self, pedido_id: int):
        nuevo_estado = request.form.get("estado", "").strip()
        origen = request.form.get("origen", "dashboard")
        usuario_nombre = session.get("nombre", "Personal del Taller")
        try:
            self.pedido_service.cambiar_estado(
                pedido_id, nuevo_estado, usuario_nombre=usuario_nombre
            )
            flash(
                f"Pedido #{pedido_id} actualizado al estado '{nuevo_estado}'.",
                "success",
            )
        except ValueError as exc:
            flash(str(exc), "danger")

        if origen == "tv":
            return redirect(url_for("vista_tv"))
        return redirect(url_for("dashboard"))

    def eliminar_pedido(self, pedido_id: int):
        self.pedido_service.eliminar_pedido(pedido_id)
        flash(f"Pedido #{pedido_id} eliminado.", "info")
        return redirect(url_for("dashboard"))

    def vista_tv(self):
        pedidos = Pedido.listar_para_tv(self.pedido_service.db)
        insumos_hilos = Insumo.listar_por_categoria(self.pedido_service.db, "Hilo")
        return render_template(
            "tv.html", pedidos=pedidos, insumos_hilos=insumos_hilos
        )

    def vista_clientes(self):
        q = request.args.get("q", "").strip()
        clientes = Cliente.listar_todos(self.pedido_service.db, q)
        return render_template("clientes.html", clientes=clientes, q=q)

    def portal_cotizacion(self):
        insumos_hilos = Insumo.listar_por_categoria(self.pedido_service.db, "Hilo")
        resumen_whatsapp_url = None
        orden_creada = None

        if request.method == "POST":
            try:
                cantidad = int(request.form.get("cantidad", "1"))
            except ValueError:
                cantidad = 1

            try:
                archivo_img = request.files.get("imagen_referencia")
                imagen_url = self.pedido_service.guardar_imagen_referencia(archivo_img)

                orden_creada, resumen_whatsapp_url = (
                    self.pedido_service.crear_precotizacion_whatsapp(
                        cedula=request.form.get("cedula", ""),
                        nombre=request.form.get("nombre", ""),
                        telefono=request.form.get("telefono", ""),
                        direccion=request.form.get("direccion", ""),
                        tipo_servicio=request.form.get(
                            "tipo_servicio", "Solo Bordado"
                        ),
                        tipo_prenda=request.form.get(
                            "tipo_prenda", "Camisa tipo Polo"
                        ),
                        cantidad=cantidad,
                        ubicacion_logo=request.form.get(
                            "ubicacion_logo", "Pecho Izquierdo"
                        ),
                        detalle_diseno=request.form.get("detalle_diseno", ""),
                        modalidad_entrega=request.form.get(
                            "modalidad_entrega", "Local"
                        ),
                        soporte_fiscal=request.form.get(
                            "soporte_fiscal", "Recibo de Caja"
                        ),
                        acepta_ley1581=1 if request.form.get("acepta_ley1581") else 0,
                        imagen_url=imagen_url,
                        host_url=request.host_url,
                    )
                )
                flash(
                    f"¡Tu idea y boceto quedaron guardados en el Pedido #{orden_creada['id']}! Ahora dale al botón verde para abrir WhatsApp y hablar con el dueño.",
                    "success",
                )
            except ValueError as exc:
                flash(str(exc), "danger")

        return render_template(
            "cotizar.html",
            insumos_hilos=insumos_hilos,
            resumen_whatsapp_url=resumen_whatsapp_url,
            orden_creada=orden_creada,
        )
