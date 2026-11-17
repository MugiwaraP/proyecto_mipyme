import sqlite3
from datetime import datetime
from flask import Flask, Response, flash, redirect, render_template, request, url_for
from controllers.auth_controller import admin_required, login_required
from services.inventario_service import InventarioService


class InventarioController:
    """Controlador de inventario de hilos/interlón, alertas de stock y backups CSV (HU-04)."""

    def __init__(self, inventario_service: InventarioService):
        self.inventario_service = inventario_service

    def register_routes(self, app: Flask) -> None:
        app.add_url_rule(
            "/insumos",
            "vista_insumos",
            login_required(self.vista_insumos),
            methods=["GET"],
        )
        app.add_url_rule(
            "/insumos/nuevo",
            "crear_insumo",
            admin_required(self.crear_insumo),
            methods=["POST"],
        )
        app.add_url_rule(
            "/insumos/<int:insumo_id>/stock",
            "ajustar_stock_insumo",
            admin_required(self.ajustar_stock_insumo),
            methods=["POST"],
        )
        app.add_url_rule(
            "/insumos/<int:insumo_id>/eliminar",
            "eliminar_insumo",
            admin_required(self.eliminar_insumo),
            methods=["POST"],
        )
        app.add_url_rule(
            "/backup/csv",
            "backup_csv",
            admin_required(self.backup_csv),
            methods=["GET"],
        )

    def vista_insumos(self):
        datos = self.inventario_service.obtener_datos_inventario()
        return render_template("insumos.html", **datos)

    def crear_insumo(self):
        try:
            stock_actual = int(request.form.get("stock_actual", "0"))
            stock_minimo = int(request.form.get("stock_minimo", "2"))
        except ValueError:
            stock_actual, stock_minimo = 0, 2

        try:
            codigo_ref = request.form.get("codigo_referencia", "").strip().upper()
            nombre_col = request.form.get("nombre_color", "").strip()
            self.inventario_service.crear_insumo(
                codigo_referencia=codigo_ref,
                nombre_color=nombre_col,
                color_hex=request.form.get("color_hex", "#1D4ED8"),
                categoria=request.form.get("categoria", "Hilo"),
                stock_actual=stock_actual,
                stock_minimo=stock_minimo,
                unidad=request.form.get("unidad", "Conos"),
            )
            etiqueta = f"{codigo_ref} ({nombre_col})" if codigo_ref else f"'{nombre_col}' (sin código)"
            flash(
                f"Material {etiqueta} registrado en inventario.",
                "success",
            )
        except sqlite3.IntegrityError:
            flash(
                "Ese código de referencia ya existe en el inventario.",
                "warning",
            )
        except ValueError as exc:
            flash(str(exc), "danger")
        return redirect(url_for("vista_insumos"))

    def eliminar_insumo(self, insumo_id: int):
        try:
            insumo = self.inventario_service.eliminar_insumo(insumo_id)
            etiqueta = f"{insumo.nombre_color} ({insumo.codigo_referencia})" if insumo.codigo_referencia else insumo.nombre_color
            flash(f"Se quitó {etiqueta} del inventario.", "info")
        except ValueError as exc:
            flash(str(exc), "danger")
        return redirect(url_for("vista_insumos"))

    def ajustar_stock_insumo(self, insumo_id: int):
        accion = request.form.get("accion", "")
        cantidad_fija = None
        if accion == "fijar":
            try:
                cantidad_fija = int(request.form.get("stock_actual", ""))
            except ValueError:
                flash("Escribe una cantidad válida.", "warning")
                return redirect(url_for("vista_insumos"))
        try:
            insumo = self.inventario_service.ajustar_stock(insumo_id, accion, cantidad_fija)
            etiqueta = f"{insumo.codigo_referencia} ({insumo.nombre_color})" if insumo.codigo_referencia else insumo.nombre_color
            flash(
                f"Stock de {etiqueta} actualizado a {insumo.stock_actual} {insumo.unidad}.",
                "info",
            )
        except ValueError as exc:
            flash(str(exc), "danger")
        return redirect(url_for("vista_insumos"))

    def backup_csv(self):
        csv_content = self.inventario_service.generar_backup_csv()
        fecha_str = datetime.now().strftime("%Y%m%d")
        return Response(
            csv_content,
            mimetype="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename=respaldo_sierra_bordados_{fecha_str}.csv"
            },
        )
