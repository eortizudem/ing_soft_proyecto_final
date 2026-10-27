from app.testing import login, sql, user_payload


def test_login_ok(anon):
    r = login(anon, "adm001", "Admin123")
    assert r.status_code == 200
    u = r.get_json()["user"]
    assert u["matricula"] == "ADM001" and u["rol"] == "admin" and "usuarios" in u["permisos"]
    assert set(u) == {"id_usuario", "matricula", "nombre_completo", "correo", "rol", "rol_descripcion", "permisos"}
    assert anon.get("/api/me").get_json()["user"]["matricula"] == "ADM001"


def test_login_fail(anon):
    r = login(anon, "ADM001", "mala")
    assert r.status_code == 401 and r.get_json()["error"] == "Clave o contraseña incorrecta"
    assert login(anon, "NOEXISTE", "x").status_code == 401


def test_login_inactive(anon, admin):
    p = user_payload(estado="inactivo")
    assert admin.post("/api/usuarios", json=p).status_code == 201
    r = login(anon, p["matricula"], p["password"])
    assert r.status_code == 403 and r.get_json()["error"] == "La cuenta está inactiva"


def test_me_requires_login(anon):
    assert anon.get("/api/me").status_code == 401


def test_logout_and_bitacora(app):
    from app.testing import client_as
    c = client_as(app, "A0512345", "Alumno123")
    assert c.post("/api/logout").get_json() == {"ok": True}
    assert c.get("/api/me").status_code == 401
    acc = {r["accion"] for r in sql("SELECT accion FROM bitacora b JOIN usuario u USING(id_usuario) "
                                    "WHERE u.matricula='A0512345'")}
    assert {"login", "logout"} <= acc


def test_visitante(anon):
    u = anon.post("/api/visitante").get_json()["user"]
    assert u["rol"] == "visitante" and u["id_usuario"] is None and u["matricula"] == "VISITANTE"
    assert "buscar" in u["permisos"] and "usuarios" not in u["permisos"]
    assert anon.get("/api/libros").status_code == 200
    assert anon.get("/api/usuarios").status_code == 403


def test_recuperar_password(anon, admin):
    p = user_payload()
    admin.post("/api/usuarios", json=p)
    assert anon.post("/api/recuperar", json={"correo": "nadie@x.com"}).get_json() == {"ok": True, "token": None}
    tok = anon.post("/api/recuperar", json={"correo": p["correo"]}).get_json()["token"]
    assert tok
    assert anon.post("/api/recuperar/confirmar", json={"token": tok, "password": "123"}).status_code == 400
    assert anon.post("/api/recuperar/confirmar", json={"token": tok, "password": "NuevaClave1"}).status_code == 200
    assert anon.post("/api/recuperar/confirmar", json={"token": tok, "password": "NuevaClave1"}).status_code == 400
    assert login(anon, p["matricula"], "NuevaClave1").status_code == 200
    assert login(anon, p["matricula"], p["password"]).status_code == 401


# ---- Seguridad (PS-S4-03 / PS-NFR-05): DEMO_MOSTRAR_TOKEN y cookie de sesion ----
def test_demo_mostrar_token_apagado_no_revela_codigo(anon, admin, app):
    p = user_payload()
    assert admin.post("/api/usuarios", json=p).status_code == 201
    app.config["DEMO_MOSTRAR_TOKEN"] = False
    try:
        assert anon.post("/api/recuperar", json={"correo": p["correo"]}).get_json() == {"ok": True}
        assert anon.post("/api/recuperar", json={"correo": "nadie@x.com"}).get_json() == {"ok": True}
    finally:
        app.config["DEMO_MOSTRAR_TOKEN"] = True
    # el codigo queda como correo simulado en la bandeja
    correo = sql("SELECT detalle FROM bitacora WHERE accion='notif_email' AND detalle LIKE %s ORDER BY id_bitacora DESC LIMIT 1",
                 (f"{p['correo']}|Recuperación de contraseña:%",))[0]["detalle"]
    token = correo.split("código de recuperación es ")[1].split(" ")[0]
    assert anon.post("/api/recuperar/confirmar", json={"token": token, "password": "NuevaClave1"}).status_code == 200


def test_bandera_https_y_cookie(monkeypatch):
    from app import config
    assert config.Config.SESSION_COOKIE_HTTPONLY is True and config.Config.SESSION_COOKIE_SAMESITE == "Lax"
    monkeypatch.setenv("X_BANDERA", "true")
    assert config._bandera("X_BANDERA", False) is True
    monkeypatch.setenv("X_BANDERA", "No")
    assert config._bandera("X_BANDERA", True) is False
    assert config._bandera("X_NO_EXISTE", True) is True
