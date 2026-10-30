"""Pruebas de reglas de circulacion (RN-01..RN-06, D-24): reglas puras y autorizacion con contexto de BD."""
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from app.core import circulacion as c
from app.core.errors import ApiError, exigir
from app.testing import make_book, make_loan, make_user, sql

POL = {"max_libros": 2}
OK = dict(usuario_activo=True, politica=POL, prestamos_abiertos=0, vencidos=0, adeudos_pendientes=0,
          libro_activo=True, tipo_uso="prestamo_externo", disponibles=1)


def codigos(**over):
    """Codigos de motivo de `evaluar_prestamo` sobre el contexto base `OK` modificado con `over`."""
    return [m["codigo"] for m in c.evaluar_prestamo(**{**OK, **over})]


# ---- reglas puras ----

def test_vencimiento_dias_habiles():
    """El vencimiento cuenta dias habiles desde el prestamo (lunes, viernes, sabado y politica docente)."""
    assert c.fecha_vencimiento(date(2026, 10, 26), 5) == date(2026, 11, 2)       # lunes + 5 habiles
    assert c.fecha_vencimiento(date(2026, 10, 30), 5) == date(2026, 11, 6)       # viernes
    assert c.fecha_vencimiento(date(2026, 10, 31), 5) == date(2026, 11, 6)       # sabado
    assert c.fecha_vencimiento(datetime(2026, 10, 26, 10), 10) == date(2026, 11, 9)   # docente


def test_retraso_y_multa():
    """Los dias de retraso son habiles y la multa es dias x tarifa sin tope; devolver el dia de vencimiento no genera multa."""
    venc = date(2026, 10, 30)                                                     # viernes
    assert c.dias_retraso(venc, venc) == 0
    assert c.dias_retraso(venc, date(2026, 11, 2)) == 1                           # lunes: 1 dia
    assert c.dias_retraso(venc, datetime(2026, 11, 4, 9)) == 3
    assert c.multa_retraso(0, 10) == Decimal("0.00")
    assert c.multa_retraso(3, Decimal("10.00")) == Decimal("30.00")
    assert c.multa_retraso(7, "12.5") == Decimal("87.50")


def test_vencido_d24():
    """Vencido solo si no hay devolucion y el vencimiento es anterior a hoy (D-24)."""
    hoy = date(2026, 10, 27)
    assert c.esta_vencido(date(2026, 10, 26), None, hoy) is True
    assert c.esta_vencido(date(2026, 10, 27), None, hoy) is False                 # el dia de vencimiento no es vencido
    assert c.esta_vencido(date(2026, 10, 1), datetime(2026, 10, 2), hoy) is False  # ya devuelto


def test_prestamo_autorizado_y_cada_regla():
    """Cada regla de RN-01 produce su codigo de motivo y se acumulan cuando fallan varias."""
    assert codigos() == []
    assert codigos(usuario_activo=False) == ["USUARIO_INACTIVO"]
    assert codigos(politica=None) == ["SIN_POLITICA"]
    assert codigos(adeudos_pendientes=1) == ["MULTAS_PENDIENTES"]
    assert codigos(vencidos=1) == ["PRESTAMOS_VENCIDOS"]
    assert codigos(prestamos_abiertos=1) == []
    assert codigos(prestamos_abiertos=2) == ["LIMITE_EJEMPLARES"]                 # alumno: el 3.o se rechaza
    assert codigos(politica={"max_libros": 3}, prestamos_abiertos=2) == []
    assert codigos(politica={"max_libros": 3}, prestamos_abiertos=3) == ["LIMITE_EJEMPLARES"]
    assert codigos(libro_activo=False) == ["LIBRO_INACTIVO"]
    assert codigos(tipo_uso="consulta_interna") == ["LIBRO_NO_PRESTABLE"]
    assert codigos(tipo_uso="reservado") == ["LIBRO_NO_PRESTABLE"]
    assert codigos(disponibles=0) == ["LIBRO_NO_DISPONIBLE"]
    assert codigos(adeudos_pendientes=1, vencidos=1, prestamos_abiertos=2) == [
        "MULTAS_PENDIENTES", "PRESTAMOS_VENCIDOS", "LIMITE_EJEMPLARES"]


def test_prestamo_reservado_por_espera():
    """Los ejemplares reservados por la lista de espera solo los puede prestar quien fue notificado (D-19)."""
    assert codigos(disponibles=1, reservados=1) == ["LIBRO_RESERVADO_OTRO_USUARIO"]
    assert codigos(disponibles=1, reservados=1, usuario_notificado=True) == []
    assert codigos(disponibles=2, reservados=1) == []
    assert codigos(disponibles=0, reservados=1, usuario_notificado=True) == ["LIBRO_NO_DISPONIBLE"]


REN = dict(abierto=True, vencido=False, num_renovaciones=0, max_renovaciones=2, adeudos_pendientes=0, espera_activa=0)


def cod_ren(**over):
    """Codigos de motivo de `evaluar_renovacion` sobre el contexto base `REN` modificado con `over`."""
    return [m["codigo"] for m in c.evaluar_renovacion(**{**REN, **over})]


def test_renovacion():
    """Reglas de renovacion: maximo, vencido, adeudos, lista de espera y prestamo cerrado; la nueva fecha parte del vencimiento actual."""
    assert cod_ren() == [] and cod_ren(num_renovaciones=1) == []
    assert cod_ren(num_renovaciones=2) == ["MAX_RENOVACIONES"]
    assert cod_ren(num_renovaciones=2, max_renovaciones=3) == []
    assert cod_ren(vencido=True) == ["PRESTAMO_VENCIDO"]
    assert cod_ren(adeudos_pendientes=2) == ["MULTAS_PENDIENTES"]
    assert cod_ren(espera_activa=1) == ["LISTA_ESPERA"]
    assert cod_ren(abierto=False, vencido=True) == ["PRESTAMO_CERRADO"]
    assert c.fecha_renovacion(date(2026, 11, 2), 5) == date(2026, 11, 9)           # sobre el vencimiento actual


def test_limite_reserva(app):
    """El limite de reserva es fin del dia tras los dias habiles de espera configurados."""
    with app.app_context():
        assert c.limite_reserva(date(2026, 10, 30)) == datetime(2026, 11, 3, 23, 59, 59)   # viernes + 2 habiles
        assert c.limite_reserva(date(2026, 10, 26)) == datetime(2026, 10, 28, 23, 59, 59)


def test_reposicion_y_danio():
    """Valor de reposicion en MXN con redondeo mitad hacia arriba y monto de dano acotado a 10-100 %."""
    assert c.valor_reposicion_mxn("45.50", "18.00") == Decimal("819.00")
    assert c.valor_reposicion_mxn(10.005, 18.5) == Decimal("185.09")               # mitad hacia arriba
    assert c.monto_danio(Decimal("819.00")) == Decimal("409.50")
    assert c.monto_danio(Decimal("819.00"), 100) == Decimal("819.00")
    assert c.monto_danio(Decimal("100.01"), 10) == Decimal("10.00")
    for p in (9, 101):
        with pytest.raises(ApiError):
            c.monto_danio(100, p)


def test_exigir_422_con_motivos():
    """`exigir` no hace nada sin motivos y con motivos responde 422 con `{error, motivos}`."""
    exigir([])
    with pytest.raises(ApiError) as e:
        exigir(c.evaluar_prestamo(**{**OK, "disponibles": 0}))
    assert e.value.status == 422 and e.value.extra["motivos"][0]["codigo"] == "LIBRO_NO_DISPONIBLE"
    from app import create_app
    app = create_app({"SKIP_SEED": True})
    app.add_url_rule("/api/_t422", "_t422", lambda: exigir([{"codigo": "X", "mensaje": "m"}], "No."))
    j = app.test_client().get("/api/_t422")
    assert j.status_code == 422 and j.get_json() == {"error": "No.", "motivos": [{"codigo": "X", "mensaje": "m"}]}


# ---- contexto desde la BD ----

def test_autorizar_prestamo_bd(app):
    """Un usuario sin bloqueos queda autorizado con politica, dias y vencimiento estimado correctos."""
    u, libro = make_user(), make_book(ejemplares=1)
    with app.app_context():
        r = c.autorizar_prestamo(u["id_usuario"], libro["id_libro"])
        assert r["autorizado"] and r["dias_prestamo"] == 5 and r["politica"]["max_libros"] == 2
        assert r["fecha_vencimiento_estimada"] == c.fecha_vencimiento(date.today(), 5)
        assert r["disponibles"] == 1 and not r["suspendido"]
        assert c.autorizar_prestamo(make_user(rol="docente")["id_usuario"], libro["id_libro"])["dias_prestamo"] == 10
        assert c.autorizar_prestamo(make_user(rol="bibliotecario")["id_usuario"], libro["id_libro"])["motivos"][0][
            "codigo"] == "SIN_POLITICA"


def test_autorizar_prestamo_bloqueos_bd(app):
    """Adeudos pendientes y prestamos vencidos reales en BD bloquean el prestamo y suspenden al usuario; al saldarlos se autoriza."""
    u, a, b = make_user(), make_book(ejemplares=2), make_book(ejemplares=1)
    pid = make_loan(u["id_usuario"], a["id_libro"])
    sql("UPDATE prestamo SET fecha_vencimiento=CURRENT_DATE-1 WHERE id_prestamo=%s", (pid,))
    sql("INSERT INTO adeudo(id_prestamo,tipo,dias_retraso,monto) VALUES (%s,'retraso',1,10)", (pid,))
    with app.app_context():
        r = c.autorizar_prestamo(u["id_usuario"], b["id_libro"])
        assert {m["codigo"] for m in r["motivos"]} == {"MULTAS_PENDIENTES", "PRESTAMOS_VENCIDOS"}
        assert r["vencidos"] == 1 and r["adeudos_pendientes"] == 1 and r["adeudos_monto"] == 10 and r["suspendido"]
    sql("UPDATE adeudo SET estado='pagado' WHERE id_prestamo=%s", (pid,))
    sql("UPDATE prestamo SET fecha_devolucion=now(), estado='devuelto' WHERE id_prestamo=%s", (pid,))
    with app.app_context():
        assert c.autorizar_prestamo(u["id_usuario"], b["id_libro"])["autorizado"]


def test_autorizar_prestamo_reservado_bd(app):
    """Un ejemplar reservado a otro usuario en espera se rechaza, pero se autoriza a quien fue notificado."""
    u, w, libro = make_user(), make_user(), make_book(ejemplares=1)
    sql("INSERT INTO lista_espera(id_usuario,id_libro,estado,fecha_notificacion,fecha_limite_recoger) "
        "VALUES (%s,%s,'notificado',now(),now()+interval '2 days')", (w["id_usuario"], libro["id_libro"]))
    with app.app_context():
        assert c.autorizar_prestamo(u["id_usuario"], libro["id_libro"])["motivos"][0]["codigo"] == "LIBRO_RESERVADO_OTRO_USUARIO"
        assert c.autorizar_prestamo(w["id_usuario"], libro["id_libro"])["autorizado"]
    sql("UPDATE lista_espera SET fecha_limite_recoger=now()-interval '1 hour' WHERE id_libro=%s", (libro["id_libro"],))
    with app.app_context():                                   # reservado vencido ya no bloquea
        assert c.autorizar_prestamo(u["id_usuario"], libro["id_libro"])["autorizado"]


def test_autorizar_renovacion_bd(app):
    """Autorizar renovacion sobre un prestamo real calcula motivos, nueva fecha y retraso."""
    u, libro = make_user(), make_book(ejemplares=1)
    pid = make_loan(u["id_usuario"], libro["id_libro"])
    with app.app_context():
        r = c.autorizar_renovacion(pid)
        assert r["permitido"] and r["max_renovaciones"] == 2
        assert r["nueva_fecha_vencimiento"] == c.fecha_renovacion(r["prestamo"]["fecha_vencimiento"], 5)
    sql("INSERT INTO lista_espera(id_usuario,id_libro) VALUES (%s,%s)", (make_user()["id_usuario"], libro["id_libro"]))
    sql("UPDATE prestamo SET num_renovaciones=2, fecha_vencimiento=CURRENT_DATE-3 WHERE id_prestamo=%s", (pid,))
    with app.app_context():
        r = c.autorizar_renovacion(pid)
        assert {m["codigo"] for m in r["motivos"]} == {"PRESTAMO_VENCIDO", "MAX_RENOVACIONES", "LISTA_ESPERA"}
        assert r["dias_retraso"] >= 2
        with pytest.raises(ApiError):
            c.autorizar_renovacion(0)


def test_valor_reposicion_bd(app):
    """El valor de reposicion usa la ultima compra recibida o, si no hay, el precio de referencia."""
    u, libro = make_user(rol="comprador"), make_book(precio_referencia=20)
    with app.app_context():
        r = c.valor_reposicion(libro["id_libro"])
        assert (r["fuente"], r["valor_usd"], r["monto_mxn"]) == ("precio_referencia", 20, Decimal("360.00"))
        assert c.valor_reposicion(libro["id_libro"], tipo_cambio="17.25")["monto_mxn"] == Decimal("345.00")
    sol = sql("INSERT INTO solicitud_compra(folio,id_usuario,justificacion,estado,fecha_recepcion) "
              "VALUES (%s,%s,'t','recibida','2026-01-10') RETURNING id_solicitud", (f"R{libro['clave'][1:]}", u["id_usuario"]))[0]["id_solicitud"]
    sol2 = sql("INSERT INTO solicitud_compra(folio,id_usuario,justificacion,estado,fecha_recepcion) "
               "VALUES (%s,%s,'t','recibida','2026-03-10') RETURNING id_solicitud", (f"S{libro['clave'][1:]}", u["id_usuario"]))[0]["id_solicitud"]
    for s, precio in ((sol, 30), (sol2, 33.33)):
        sql("INSERT INTO detalle_solicitud(id_solicitud,id_libro,descripcion,cantidad,precio_unitario) VALUES (%s,%s,'x',1,%s)",
            (s, libro["id_libro"], precio))
    with app.app_context():
        r = c.valor_reposicion(libro["id_libro"])
        assert r["fuente"] == "ultima_compra" and r["valor_usd"] == Decimal("33.33") and r["monto_mxn"] == Decimal("599.94")
        with pytest.raises(ApiError):
            c.valor_reposicion(0)
