from functools import wraps
from flask import Flask, flash, redirect, render_template, request, session, url_for
from services.auth_service import AuthService


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            if request.endpoint == "dashboard":
                return redirect(url_for("portal_cotizacion"))
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        if session.get("rol") != "admin":
            flash(
                "Acceso restringido: Tu rol de Operario solo permite consultar órdenes y actualizar su estado en planta.",
                "warning",
            )
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)

    return decorated_function


class AuthController:
    """Controlador de autenticación y cierre de sesión (HU-01)."""

    def __init__(self, auth_service: AuthService):
        self.auth_service = auth_service

    def register_routes(self, app: Flask) -> None:
        app.add_url_rule("/login", "login", self.login, methods=["GET", "POST"])
        app.add_url_rule("/logout", "logout", self.logout, methods=["POST"])

    def login(self):
        if "user_id" in session:
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            username = request.form.get("username", "")
            password = request.form.get("password", "")
            usuario = self.auth_service.autenticar(username, password)
            if usuario:
                session["user_id"] = usuario.id
                session["nombre"] = usuario.nombre
                session["username"] = usuario.username
                session["rol"] = usuario.rol
                flash(
                    f"Bienvenido(a), {usuario.nombre} ({usuario.rol.upper()}).",
                    "success",
                )
                if usuario.es_operario:
                    return redirect(url_for("vista_tv"))
                return redirect(url_for("dashboard"))
            flash(
                "Usuario o contraseña incorrectos. Verifica tus credenciales.",
                "danger",
            )
        return render_template("login.html")

    @staticmethod
    def logout():
        session.clear()
        flash("Sesión cerrada correctamente.", "info")
        return redirect(url_for("login"))
