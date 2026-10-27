from datetime import date, datetime
from decimal import Decimal

import pytest
from flask import Flask

from app.core import auth, http
from app.core.bitacora import audit
from app.core.errors import ApiError
from app.core.estado import toggle_estado
from app.core.module import make_blueprint
from app.core.serializers import JSONProvider, nest, to_json
from app.testing import make_user, sql


# ---- serializers ----

def test_to_json_recursive():
    row = {"d": date(2026, 1, 2), "t": datetime(2026, 1, 2, 3, 4, 5), "m": Decimal("10.50"),
           "l": [{"x": Decimal(1)}, (date(2020, 2, 2),)], "s": "a", "n": None, "b": True}
    assert to_json(row) == {"d": "2026-01-02", "t": "2026-01-02T03:04:05", "m": 10.5,
                            "l": [{"x": 1.0}, ["2020-02-02"]], "s": "a", "n": None, "b": True}
    assert to_json([row])[0]["m"] == 10.5 and to_json(None) is None


def test_nest():
    assert nest({"a": 1, "x": 2, "y": 3}, "sub", ("x", "y")) == {"a": 1, "sub": {"x": 2, "y": 3}}
    assert nest(None, "sub", ("x",)) is None
    r = {"x": 1}
    nest(r, "s", ("x",))
    assert r == {"x": 1}


def _mini_app():
    app = Flask(__name__)
    app.json = JSONProvider(app)

    @app.get("/rows")
    def rows():
        return [{"d": date(2026, 1, 2), "m": Decimal("2.5"), "ñ": "á"}]

    @app.post("/echo")
    def echo():
        return http.created(http.body())

    @app.get("/q")
    def q():
        return http.query_args({"q": "", "flag": False, "n": 5, "x": None, "c": ("0", lambda s: s * 2)})

    @app.post("/strict")
    def strict():
        return http.ok(http.body(strict=True))

    @app.get("/ok")
    def okk():
        return http.ok()

    @app.get("/extra")
    def extra():
        return http.ok(user=1)

    @app.errorhandler(ApiError)
    def h(e):
        return {"error": e.message}, e.status

    return app


def test_json_provider_returns_rows_directly():
    r = _mini_app().test_client().get("/rows")
    assert r.get_json() == [{"d": "2026-01-02", "m": 2.5, "ñ": "á"}]
    assert "á" in r.get_data(as_text=True)  # ensure_ascii desactivado


def test_http_body_ok_created_query():
    c = _mini_app().test_client()
    r = c.post("/echo", json={"a": 1})
    assert (r.status_code, r.get_json()) == (201, {"a": 1})
    assert c.post("/echo", data="no json", content_type="application/json").get_json() == {}
    assert c.post("/echo", json=[1, 2]).get_json() == {}
    assert c.post("/strict", json=[1]).status_code == 400
    assert c.post("/strict", json={"z": 1}).get_json() == {"z": 1}
    assert c.get("/ok").get_json() == {"ok": True}
    assert c.get("/extra").get_json() == {"user": 1}
    assert c.get("/q").get_json() == {"q": "", "flag": False, "n": 5, "x": None, "c": "0"}
    assert c.get("/q?q=hola&flag=TRUE&n=7&x=raw&c=ab").get_json() == {"q": "hola", "flag": True, "n": 7, "x": "raw", "c": "abab"}
    assert c.get("/q?flag=0&n=zz").get_json()["flag"] is False
    assert c.get("/q?n=zz").get_json()["n"] == 5


def test_make_blueprint_name_and_static():
    bp = make_blueprint("app.modules.demo")
    assert bp.name == "demo" and bp.url_prefix is None and bp.static_url_path == "/m/demo"


# ---- auth helpers ----

def test_require_permission(app):
    with app.test_request_context():
        with pytest.raises(ApiError) as e:
            auth.require_permission("x", {"permisos": []})
        assert e.value.status == 403
        assert auth.require_permission("x", {"permisos": ["x"]}) == {"permisos": ["x"]}


# ---- toggle_estado ----

def test_toggle_estado_guard_extra_and_result(app):
    u = make_user()
    seen = []

    def load(i):
        from app.core.repo import get_or_404
        return get_or_404("usuario", "id_usuario", i, "No hay.")

    def guard(row, nuevo):
        seen.append((row["estado"], nuevo))
        if row["matricula"].endswith("BLOQUEO"):
            raise ApiError("Bloqueado.")

    extra = {"inactivo": {"registro_vigente": False}, "activo": {"registro_vigente": True}}
    with app.app_context():
        row, nuevo = toggle_estado("usuario", "id_usuario", u["id_usuario"], load=load, guard=guard, extra=extra)
        assert (row["estado"], nuevo) == ("activo", "inactivo")
        now = load(u["id_usuario"])
        assert now["estado"] == "inactivo" and now["registro_vigente"] is False
        _, nuevo = toggle_estado("usuario", "id_usuario", u["id_usuario"], load=load, guard=guard, extra=extra)
        assert nuevo == "activo" and load(u["id_usuario"])["registro_vigente"] is True
        assert seen == [("activo", "inactivo"), ("inactivo", "activo")]
        with pytest.raises(ApiError) as e:
            toggle_estado("usuario", "id_usuario", -9, load=load)
        assert e.value.status == 404

        def deny(row, nuevo):
            raise ApiError("Bloqueado.")

        with pytest.raises(ApiError):
            toggle_estado("usuario", "id_usuario", u["id_usuario"], load=load, guard=deny)
        assert load(u["id_usuario"])["estado"] == "activo"  # la guarda impide el cambio
        # no hay commit en este contexto: se revierte con el teardown de la app


# ---- audit ----

def test_audit_logs_only_on_success(app):
    admin_id = sql("SELECT id_usuario FROM usuario WHERE matricula='ADM001'")[0]["id_usuario"]
    actor = {"id_usuario": admin_id}

    @audit("t_audit", lambda r: f"res={r['v']}")
    def ok_fn(x, actor):
        return {"v": x}

    @audit(lambda r: "t_a_" + r["v"], lambda r, a: f"{r['v']}/{a['x']}")
    def dyn(x, actor=None):
        return {"v": x}

    @audit("t_audit_fail")
    def bad(actor):
        raise ApiError("no")

    @audit("t_audit_none")
    def nobody(actor):
        return 1

    with app.app_context():
        assert ok_fn(5, actor) == {"v": 5}
        dyn("zz", actor=actor)
        with pytest.raises(ApiError):
            bad(actor)
        nobody(None)
        nobody({"id_usuario": None})  # visitante: log() lo ignora
        from app.core import db
        rows = db.fetchall("SELECT accion, detalle FROM bitacora WHERE accion LIKE 't\\_a%%' ORDER BY id_bitacora")
        assert [(r["accion"], r["detalle"]) for r in rows] == [("t_audit", "res=5"), ("t_a_zz", "zz/zz")]
        db.get_conn().rollback()
