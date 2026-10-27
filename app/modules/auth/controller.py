from flask import current_app

from app.core.auth import current_user, login_required
from app.core.http import body, ok

from . import bp, service


@bp.post("/api/login")
def login():
    return ok(user=service.login(body()))


@bp.post("/api/visitante")
def visitante():
    return ok(user=service.visitante())


@bp.post("/api/logout")
def logout():
    service.logout(current_user())
    return ok()


@bp.get("/api/me")
@login_required
def me():
    return ok(user=current_user())


@bp.post("/api/recuperar")
def recuperar():
    token = service.recuperar(body())
    # Sin DEMO_MOSTRAR_TOKEN el codigo nunca sale en la respuesta (no revela si el correo existe).
    return ok(ok=True, token=token) if current_app.config["DEMO_MOSTRAR_TOKEN"] else ok()


@bp.post("/api/recuperar/confirmar")
def confirmar():
    service.confirmar(body())
    return ok()
