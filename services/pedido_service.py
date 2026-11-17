import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote
from flask import current_app, has_app_context
from werkzeug.utils import secure_filename

from config import Config
from models.database import Database
from models.cliente import Cliente
from models.pedido import Pedido
from models.insumo import Insumo


class PedidoService:
    """Servicio de negocio para la gestión de pedidos, bocetos de referencia, expedientes por cédula y WhatsApp."""

    EXTENSIONES_PERMITIDAS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".pdf"}

    def __init__(self, db: Database):
        self.db = db

    def guardar_archivo_adjunto(
        self, archivo_storage, prefijo: str = "boceto"
    ) -> str:
        """Guarda una imagen o PDF en static/uploads y retorna su ruta pública."""
        if not archivo_storage or not archivo_storage.filename:
            return ""
        nombre_original = secure_filename(archivo_storage.filename)
        _, ext = os.path.splitext(nombre_original.lower())
        if ext not in self.EXTENSIONES_PERMITIDAS:
            raise ValueError(
                "Formato no permitido: sube una foto (PNG, JPG, WEBP, GIF) o un archivo PDF."
            )
        upload_folder = (
            current_app.config.get("UPLOAD_FOLDER", Config.UPLOAD_FOLDER)
            if has_app_context()
            else Config.UPLOAD_FOLDER
        )
        os.makedirs(upload_folder, exist_ok=True)
        nombre_unico = f"{prefijo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}{ext}"
        ruta_completa = os.path.join(upload_folder, nombre_unico)
        archivo_storage.save(ruta_completa)
        return f"/static/uploads/{nombre_unico}"

    def guardar_imagen_referencia(self, archivo_storage) -> str:
        """Guarda el boceto inicial enviado por el cliente."""
        return self.guardar_archivo_adjunto(archivo_storage, prefijo="boceto")

    def obtener_datos_dashboard(
        self, q_cedula: str = "", filtro_estado: str = ""
    ) -> Dict:
        pedidos = Pedido.listar_filtrados(self.db, q_cedula, filtro_estado)
        historial_map = Pedido.listar_historial_por_pedidos(
            self.db, [p.id for p in pedidos if p.id is not None]
        )
        for p in pedidos:
            if p.id is not None:
                p.historial = historial_map.get(p.id, [])

        todos_pedidos = Pedido.listar_filtrados(self.db)

        cliente_encontrado: Optional[Cliente] = None
        historial_cliente: List[Pedido] = []
        if q_cedula:
            cliente_encontrado = Cliente.buscar_coincidente(self.db, q_cedula)
            if cliente_encontrado and cliente_encontrado.id is not None:
                historial_cliente = Pedido.obtener_por_cliente(
                    self.db, cliente_encontrado.id
                )

        insumos = Insumo.listar_todos(self.db)
        alertas_insumos = [i for i in insumos if i.requiere_reposicion]

        metricas = {
            "total_activos": sum(1 for p in todos_pedidos if p.esta_activo),
            "cotizaciones": sum(
                1 for p in todos_pedidos if p.estado == "Cotización"
            ),
            "pendientes": sum(
                1 for p in todos_pedidos if p.estado == "Pendiente"
            ),
            "en_proceso": sum(
                1 for p in todos_pedidos if p.estado == "En Proceso"
            ),
            "listos_despacho": sum(
                1 for p in todos_pedidos if p.estado == "Listo"
            ),
            "alertas_stock": len(alertas_insumos),
        }

        return {
            "pedidos": pedidos,
            "insumos": insumos,
            "alertas_insumos": alertas_insumos,
            "metricas": metricas,
            "cliente_encontrado": cliente_encontrado,
            "historial_cliente": historial_cliente,
        }

    def crear_pedido_y_cliente(
        self,
        cedula: str,
        nombre: str,
        telefono: str,
        direccion: str,
        hilos_corporativos: str,
        acepta_ley1581: int,
        tipo_servicio: str,
        descripcion_y_hilos: str,
        cantidad: int,
        modalidad_entrega: str = "Local",
        soporte_fiscal: str = "Recibo de Caja",
        estado: str = "Pendiente",
        imagen_url: str = "",
        guardar_hilos_cliente: bool = True,
        solicitud_original: str = "",
        acuerdo_whatsapp: str = "",
        evidencia_url: str = "",
        autor_evento: str = "Administrador",
        confirmado_por: str = "",
    ) -> int:
        if not cedula.strip() or not nombre.strip() or not descripcion_y_hilos.strip():
            raise ValueError(
                "La Cédula/NIT, el nombre del cliente y la descripción son obligatorios."
            )

        ahora = datetime.now().strftime("%Y-%m-%d %H:%M")
        hilos_a_guardar = ""
        if guardar_hilos_cliente:
            hilos_a_guardar = (hilos_corporativos or descripcion_y_hilos).strip()

        cliente = Cliente(
            id=None,
            cedula=cedula.strip(),
            nombre=nombre.strip(),
            telefono=telefono.strip(),
            direccion=direccion.strip(),
            hilos_corporativos=hilos_a_guardar,
            acepta_ley1581=acepta_ley1581,
            fecha_registro=ahora,
        )
        cliente_id = cliente.guardar_o_actualizar(self.db)

        cant_final = max(1, cantidad)
        estado_limpio = estado.strip()
        acuerdo_limpio = acuerdo_whatsapp.strip()
        solicitud_guardada = solicitud_original.strip()
        if not solicitud_guardada:
            solicitud_guardada = (
                f"{tipo_servicio.strip()} · {cant_final} prendas · "
                f"{descripcion_y_hilos.strip()} "
                f"(Entrega: {modalidad_entrega.strip()}, {soporte_fiscal.strip()})"
            )
            if acuerdo_limpio:
                solicitud_guardada += f" | Acuerdo: {acuerdo_limpio}"

        conf_por = confirmado_por.strip()
        if not conf_por and estado_limpio != "Cotización":
            conf_por = autor_evento
        fecha_conf = ahora if conf_por else ""

        pedido = Pedido(
            id=None,
            cliente_id=cliente_id,
            tipo_servicio=tipo_servicio.strip(),
            descripcion_y_hilos=descripcion_y_hilos.strip(),
            cantidad=cant_final,
            modalidad_entrega=modalidad_entrega.strip(),
            soporte_fiscal=soporte_fiscal.strip(),
            estado=estado_limpio,
            fecha_creacion=ahora,
            imagen_url=imagen_url,
            solicitud_original=solicitud_guardada,
            acuerdo_whatsapp=acuerdo_limpio,
            evidencia_url=evidencia_url,
            confirmado_por=conf_por,
            fecha_confirmacion=fecha_conf,
        )
        pedido_id = pedido.crear(self.db)

        accion_inicial = (
            "Solicitud enviada por el cliente"
            if estado_limpio == "Cotización"
            else "Pedido registrado en taller"
        )
        Pedido.registrar_evento_historial(
            self.db,
            pedido_id=pedido_id,
            fecha_hora=ahora,
            autor=autor_evento,
            accion=accion_inicial,
            resumen=solicitud_guardada,
            archivo_url=evidencia_url or imagen_url,
        )
        return pedido_id

    @staticmethod
    def _construir_resumen_cambios(
        pedido_actual: Pedido,
        tipo_servicio: str,
        cantidad_final: int,
        descripcion_limpia: str,
        entrega_limpia: str,
        fiscal_limpio: str,
        estado_limpio: str,
        acuerdo_limpio: str,
        nueva_evidencia_url: str,
    ) -> str:
        """Resume los cambios y acuerdos aplicados al editar o confirmar un pedido."""
        partes = []
        if pedido_actual.estado != estado_limpio:
            partes.append(f"Estado: '{pedido_actual.estado}' → '{estado_limpio}'")
        if pedido_actual.tipo_servicio != tipo_servicio:
            partes.append(f"Trabajo: '{pedido_actual.tipo_servicio}' → '{tipo_servicio}'")
        if pedido_actual.cantidad != cantidad_final:
            partes.append(f"Cantidad: {pedido_actual.cantidad} → {cantidad_final} prendas")
        if pedido_actual.descripcion_y_hilos.strip() != descripcion_limpia:
            partes.append(f"Especificación/Hilos finales: {descripcion_limpia}")
        if acuerdo_limpio and acuerdo_limpio != (pedido_actual.acuerdo_whatsapp or "").strip():
            partes.append(f"Acuerdo WhatsApp/taller: {acuerdo_limpio}")
        if pedido_actual.modalidad_entrega != entrega_limpia:
            partes.append(f"Entrega: {pedido_actual.modalidad_entrega} → {entrega_limpia}")
        if pedido_actual.soporte_fiscal != fiscal_limpio:
            partes.append(f"Comprobante: {pedido_actual.soporte_fiscal} → {fiscal_limpio}")
        if nueva_evidencia_url:
            partes.append("Se adjuntó imagen/PDF de prueba o aprobación.")
        return " | ".join(partes) if partes else "Revisión guardada sin cambios en los textos."

    def editar_pedido(
        self,
        pedido_id: int,
        tipo_servicio: str,
        descripcion_y_hilos: str,
        cantidad: int,
        modalidad_entrega: str,
        soporte_fiscal: str,
        estado: str,
        guardar_como_hilos_cliente: bool = False,
        acuerdo_whatsapp: str = "",
        nueva_evidencia_url: str = "",
        usuario_nombre: str = "Administrador",
    ) -> bool:
        if not descripcion_y_hilos.strip():
            raise ValueError("La descripción y códigos de hilo no pueden quedar vacíos.")
        if estado not in Pedido.ESTADOS_VALIDOS:
            raise ValueError("Estado no válido.")

        pedido_actual = Pedido.obtener_por_id(self.db, pedido_id)
        if not pedido_actual:
            raise ValueError("Pedido no encontrado.")

        ahora = datetime.now().strftime("%Y-%m-%d %H:%M")
        servicio_limpio = tipo_servicio.strip()
        descripcion_limpia = descripcion_y_hilos.strip()
        cantidad_final = max(1, cantidad)
        entrega_limpia = modalidad_entrega.strip()
        fiscal_limpio = soporte_fiscal.strip()
        estado_limpio = estado.strip()
        acuerdo_limpio = acuerdo_whatsapp.strip()
        evidencia_final = nueva_evidencia_url or pedido_actual.evidencia_url

        confirmado_desde_cotizacion = (
            pedido_actual.estado == "Cotización" and estado_limpio != "Cotización"
        )
        if confirmado_desde_cotizacion or (
            estado_limpio != "Cotización" and not pedido_actual.confirmado_por
        ):
            conf_por = usuario_nombre
            fecha_conf = ahora
        else:
            conf_por = pedido_actual.confirmado_por
            fecha_conf = pedido_actual.fecha_confirmacion

        Pedido.actualizar(
            self.db,
            pedido_id=pedido_id,
            tipo_servicio=servicio_limpio,
            descripcion_y_hilos=descripcion_limpia,
            cantidad=cantidad_final,
            modalidad_entrega=entrega_limpia,
            soporte_fiscal=fiscal_limpio,
            estado=estado_limpio,
            acuerdo_whatsapp=acuerdo_limpio,
            evidencia_url=evidencia_final,
            confirmado_por=conf_por,
            fecha_confirmacion=fecha_conf,
        )

        accion = (
            "Pedido confirmado (Acuerdo registrado)"
            if confirmado_desde_cotizacion
            else "Edición / Actualización de acuerdo"
        )
        resumen = self._construir_resumen_cambios(
            pedido_actual=pedido_actual,
            tipo_servicio=servicio_limpio,
            cantidad_final=cantidad_final,
            descripcion_limpia=descripcion_limpia,
            entrega_limpia=entrega_limpia,
            fiscal_limpio=fiscal_limpio,
            estado_limpio=estado_limpio,
            acuerdo_limpio=acuerdo_limpio,
            nueva_evidencia_url=nueva_evidencia_url,
        )
        Pedido.registrar_evento_historial(
            self.db,
            pedido_id=pedido_id,
            fecha_hora=ahora,
            autor=usuario_nombre,
            accion=accion,
            resumen=resumen,
            archivo_url=nueva_evidencia_url,
        )

        if guardar_como_hilos_cliente and pedido_actual.cedula:
            cliente = Cliente.obtener_por_cedula(self.db, pedido_actual.cedula)
            if cliente:
                cliente.hilos_corporativos = descripcion_limpia
                cliente.guardar_o_actualizar(self.db)

        return confirmado_desde_cotizacion

    def cambiar_estado(
        self, pedido_id: int, nuevo_estado: str, usuario_nombre: str = "Personal del Taller"
    ) -> None:
        if nuevo_estado not in Pedido.ESTADOS_VALIDOS:
            raise ValueError("Estado no válido.")
        pedido_actual = Pedido.obtener_por_id(self.db, pedido_id)
        if not pedido_actual:
            raise ValueError("Pedido no encontrado.")

        ahora = datetime.now().strftime("%Y-%m-%d %H:%M")
        conf_por = None
        fecha_conf = None
        if pedido_actual.estado == "Cotización" and nuevo_estado != "Cotización":
            conf_por = usuario_nombre
            fecha_conf = ahora

        Pedido.actualizar_estado(
            self.db,
            pedido_id,
            nuevo_estado,
            confirmado_por=conf_por,
            fecha_confirmacion=fecha_conf,
        )
        Pedido.registrar_evento_historial(
            self.db,
            pedido_id=pedido_id,
            fecha_hora=ahora,
            autor=usuario_nombre,
            accion="Cambio de estado",
            resumen=f"Estado cambiado de '{pedido_actual.estado}' a '{nuevo_estado}'.",
        )

    def eliminar_pedido(self, pedido_id: int) -> None:
        Pedido.eliminar(self.db, pedido_id)

    def crear_precotizacion_whatsapp(
        self,
        cedula: str,
        nombre: str,
        telefono: str,
        direccion: str,
        tipo_servicio: str,
        tipo_prenda: str,
        cantidad: int,
        ubicacion_logo: str,
        detalle_diseno: str,
        modalidad_entrega: str,
        soporte_fiscal: str,
        acepta_ley1581: int,
        imagen_url: str = "",
        host_url: str = "",
    ) -> Tuple[Dict, str]:
        if not detalle_diseno.strip() and not imagen_url:
            raise ValueError(
                "Cuéntanos brevemente tu idea o sube una imagen de referencia para poder asesorarte."
            )

        texto_detalle = (
            detalle_diseno.strip()
            if detalle_diseno.strip()
            else "Según imagen/boceto adjunto (definir detalles por WhatsApp)."
        )
        nota_imagen = " [Con boceto adjunto]" if imagen_url else ""
        descripcion_estructurada = (
            f"[{tipo_prenda} | Ubicación: {ubicacion_logo}]{nota_imagen} {texto_detalle}"
        )
        solicitud_web = (
            f"Cliente envió por web: {tipo_servicio} en {tipo_prenda} · "
            f"{max(1, cantidad)} prendas · Ubicación: {ubicacion_logo} · "
            f"Detalle/Colores: {texto_detalle} · Entrega: {modalidad_entrega}"
            + (f" ({direccion.strip()})" if direccion.strip() else "")
            + f" · Comprobante: {soporte_fiscal}"
            + (" · Adjuntó archivo de referencia." if imagen_url else " · Sin archivo adjunto.")
        )
        pedido_id = self.crear_pedido_y_cliente(
            cedula=cedula,
            nombre=nombre,
            telefono=telefono,
            direccion=direccion,
            hilos_corporativos="",
            acepta_ley1581=acepta_ley1581,
            tipo_servicio=tipo_servicio,
            descripcion_y_hilos=descripcion_estructurada,
            cantidad=cantidad,
            modalidad_entrega=modalidad_entrega,
            soporte_fiscal=soporte_fiscal,
            estado="Cotización",
            imagen_url=imagen_url,
            guardar_hilos_cliente=False,
            solicitud_original=solicitud_web,
            autor_evento=f"Cliente: {nombre.strip()} (Web)",
        )

        linea_boceto = ""
        if imagen_url:
            base = host_url.rstrip("/") if host_url else ""
            linea_boceto = f"• *Boceto / Referencia subida:* {base}{imagen_url}\n"

        linea_dir = (
            f"• *Dirección recogida/envío:* {direccion.strip()}\n"
            if direccion.strip()
            else ""
        )

        mensaje_wa = (
            f"Hola *{Config.EMPRESA_NOMBRE}*, envié el Pedido/Boceto #{pedido_id} desde la web:\n"
            f"• *Cliente:* {nombre} (C.C./NIT: {cedula})\n"
            f"• *Trabajo:* {tipo_servicio} en *{tipo_prenda}*\n"
            f"• *Cantidad:* {cantidad} unidades\n"
            f"• *Ubicación del diseño:* {ubicacion_logo}\n"
            f"• *Idea y Colores de Hilo:* {texto_detalle}\n"
            f"{linea_boceto}"
            f"• *Entrega:* {modalidad_entrega} | *Soporte:* {soporte_fiscal}\n"
            f"{linea_dir}"
            f"Quedo atento(a) para conversar y afinar los detalles del diseño."
        )
        whatsapp_url = f"https://wa.me/{Config.WHATSAPP_TALLER}?text={quote(mensaje_wa)}"
        orden_creada = {
            "id": pedido_id,
            "nombre": nombre,
            "cedula": cedula,
            "tipo_servicio": tipo_servicio,
            "tipo_prenda": tipo_prenda,
            "cantidad": cantidad,
            "descripcion": descripcion_estructurada,
            "imagen_url": imagen_url,
        }
        return orden_creada, whatsapp_url

    def buscar_expediente_por_cedula(self, cedula: str) -> Optional[Dict]:
        cliente = Cliente.obtener_por_cedula(self.db, cedula)
        if not cliente or cliente.id is None:
            return None
        historial = Pedido.obtener_por_cliente(self.db, cliente.id, limite=5)
        return {
            "encontrado": True,
            "cliente": cliente.to_dict(),
            "historial_pedidos": [p.to_dict() for p in historial],
        }
