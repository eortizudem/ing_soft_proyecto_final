"""Capa CONTROLLER (HTTP) de auth: endpoints de sesion y recuperacion de contrasena (`/api/login`, `/api/visitante`, `/api/logout`, `/api/me`, `/api/recuperar*`). Delega en `service.py`."""
from flask import current_app

from app.core.auth import current_user, login_required
from app.core.http import body, ok

from . import bp, service


@bp.post("/api/login")
def login():
    """POST /api/login. Publico. Payload `{matricula, password}`. Respuesta 200 `{ok, user}`.
    Errores: 401 credenciales incorrectas; 403 cuenta inactiva.
    """
    return ok(user=service.login(body()))


@bp.post("/api/visitante")
def visitante():
    """POST /api/visitante. Publico. Sin payload. Respuesta 200 `{ok, user}` con el usuario visitante (D-26)."""
    return ok(user=service.visitante())


@bp.post("/api/logout")
def logout():
    """POST /api/logout. Publico (idempotente). Cierra la sesion; respuesta 200 `{ok}`."""
    service.logout(current_user())
    return ok()


@bp.get("/api/me")
@login_required
def me():
    """GET /api/me. Requiere sesion (`login_required`). Respuesta 200 `{ok, user}`; 401 sin sesion."""
    return ok(user=current_user())


@bp.post("/api/recuperar")
def recuperar():
    """POST /api/recuperar. Publico. Payload `{correo}`. Respuesta 200 `{ok}`; con `DEMO_MOSTRAR_TOKEN` activo agrega
    `token` (o `null`). Siempre responde igual exista o no el correo.
    """
    token = service.recuperar(body())
    # Sin DEMO_MOSTRAR_TOKEN el codigo nunca sale en la respuesta (no revela si el correo existe).
    return ok(ok=True, token=token) if current_app.config["DEMO_MOSTRAR_TOKEN"] else ok()


@bp.post("/api/recuperar/confirmar")
def confirmar():
    """POST /api/recuperar/confirmar. Publico. Payload `{token, password}`. Respuesta 200 `{ok}`.
    Errores: 400 token invalido/expirado o contrasena de menos de 6 caracteres.
    """
    service.confirmar(body())
    return ok()
