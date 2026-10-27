import pytest

from app.core import notificaciones
from app.core.errors import ApiError
from app.testing import make_user, sql


def filas(id_usuario):
    return sql("SELECT accion, detalle FROM bitacora WHERE id_usuario=%s AND accion LIKE 'notif_%%' ORDER BY id_bitacora",
               (id_usuario,))


def test_enviar_y_parsear(app):
    u = make_user()
    with app.app_context():
        notificaciones.enviar("email", "Recibo", "Tu préstamo vence el lunes", u["id_usuario"], "a@b.mx")
        notificaciones.enviar("tesoreria", "Factura F-1", "Total 100", u["id_usuario"])
        from app.core import db
        db.get_conn().commit()
    f = filas(u["id_usuario"])
    assert [r["accion"] for r in f] == ["notif_email", "notif_tesoreria"]
    assert f[0]["detalle"] == "a@b.mx|Recibo: Tu préstamo vence el lunes"
    assert notificaciones.parsear(f[0]["accion"], f[0]["detalle"]) == {
        "canal": "email", "destino": "a@b.mx", "asunto": "Recibo", "cuerpo": "Tu préstamo vence el lunes"}
    assert notificaciones.parsear("notif_tesoreria", f[1]["detalle"])["destino"] == ""


def test_truncado_y_canal_invalido(app):
    u = make_user()
    with app.app_context():
        notificaciones.enviar("whatsapp", "x", "y" * 500, u["id_usuario"], "55")
        from app.core import db
        db.get_conn().commit()
        with pytest.raises(ApiError):
            notificaciones.enviar("telegrama", "x", "y", u["id_usuario"])
    assert len(filas(u["id_usuario"])[0]["detalle"]) == 200


def test_enviar_a_usuario_resuelve_destino(app):
    u = make_user()
    with app.app_context():
        notificaciones.enviar_a_usuario("email", "Hola", "cuerpo", u["id_usuario"])
        notificaciones.enviar_a_usuario("servicios_escolares", "Aviso", "cuerpo", u["id_usuario"])
        from app.core import db
        db.get_conn().commit()
    d = [r["detalle"] for r in filas(u["id_usuario"])]
    assert d[0].startswith(u["correo"] + "|") and d[1].startswith(u["matricula"] + "|")


def test_validar_canales():
    assert notificaciones.validar_canales(None) == ["email"]
    assert notificaciones.validar_canales(["whatsapp", "email", "whatsapp"]) == ["whatsapp", "email"]
    with pytest.raises(ApiError):
        notificaciones.validar_canales(["sms"])
