import pytest

from app.core import errores
from app.testing import sql, uniq


def _ultimos(patron):
    return sql("SELECT id_usuario, detalle FROM bitacora WHERE accion='error_sistema' AND detalle LIKE %s ORDER BY id_bitacora",
               (f"%{patron}%",))


@pytest.fixture(autouse=True)
def _sin_limites():
    errores.reiniciar_limites()
    yield
    errores.reiniciar_limites()


def test_cliente_anonimo_queda_en_bitacora_sin_usuario(anon):
    marca = uniq()
    r = anon.post("/api/errores", json={"mensaje": f"TypeError {marca}", "ruta": "/libros", "origen": "main.js:10"})
    assert r.status_code == 200 and r.get_json() == {"registrado": True}
    (fila,) = _ultimos(marca)
    assert fila["id_usuario"] is None and fila["detalle"].startswith("cliente|/libros: TypeError")


def test_cliente_con_sesion_guarda_usuario_y_trunca(admin):
    marca = uniq()
    admin.post("/api/errores", json={"mensaje": marca + "x" * 500})
    (fila,) = _ultimos(marca)
    assert fila["id_usuario"] and len(fila["detalle"]) <= 200


def test_mensaje_vacio_no_se_registra(anon):
    assert anon.post("/api/errores", json={"mensaje": "  "}).get_json() == {"registrado": False}
    assert anon.post("/api/errores", data="no json").get_json() == {"registrado": False}


def test_limite_por_cliente(anon):
    marca = uniq()
    estados = [anon.post("/api/errores", json={"mensaje": f"{marca} {n}"}).get_json()["registrado"] for n in range(8)]
    assert estados == [True] * 5 + [False] * 3
    assert len(_ultimos(marca)) == 5


def test_limite_ventana_y_global():
    assert all(errores.dentro_del_limite("1.1.1.1", ahora=0) for _ in range(5))
    assert not errores.dentro_del_limite("1.1.1.1", ahora=1)
    assert errores.dentro_del_limite("1.1.1.1", ahora=61)       # la ventana de 60 s expira
    errores.reiniciar_limites()
    ok = [errores.dentro_del_limite(f"ip{n}", ahora=0) for n in range(70)]
    assert ok.count(True) == 60                                      # tope global


def test_error_500_se_registra_con_su_usuario(admin, monkeypatch):
    marca = uniq()

    def falla():
        raise RuntimeError(f"explotó {marca}")

    monkeypatch.setattr("app.modules.info.service.faq", falla)
    r = admin.get("/api/faq")
    assert r.status_code == 500 and r.get_json() == {"error": "Error interno del servidor."}
    (fila,) = _ultimos(marca)
    assert fila["id_usuario"] and fila["detalle"].startswith("servidor|GET /api/faq: RuntimeError")


def test_error_500_anonimo_sin_usuario(anon, monkeypatch):
    monkeypatch.setattr("app.modules.info.service.faq", lambda: 1 / 0)
    assert anon.get("/api/faq").status_code == 500
    assert [f["id_usuario"] for f in _ultimos("ZeroDivisionError")][-1] is None


def test_registrar_nunca_lanza(app, monkeypatch):
    def malo(*a, **k):
        raise RuntimeError("sin base de datos")

    monkeypatch.setattr(errores.db, "connect", malo)
    with app.app_context():
        assert errores.registrar("servidor", "x") is False
