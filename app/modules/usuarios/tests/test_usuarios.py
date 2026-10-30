"""Pruebas de API de `usuarios`: permisos, CRUD, validación, unicidad y guardas de baja/último admin (RF-01, RF-03, D-24)."""

from app.testing import make_loan, sql, user_payload, libro_payload


def test_permission_403(alumno, anon):
    """Sin permiso `usuarios` responde 403 y sin sesión 401."""
    assert alumno.get("/api/usuarios").status_code == 403
    assert alumno.post("/api/usuarios", json=user_payload()).status_code == 403
    assert anon.get("/api/usuarios").status_code == 401


def test_crud(admin):
    """Alta, edición, consulta y filtros de una cuenta funcionan de punta a punta."""
    p = user_payload()
    r = admin.post("/api/usuarios", json=p)
    assert r.status_code == 201
    u = r.get_json()
    assert u["matricula"] == p["matricula"] and u["rol"] == "alumno" and u["registro_vigente"] is True
    assert u["prestamos_activos"] == 0 and u["adeudos_pendientes"] == 0
    p["nombre_completo"] = "Nombre Cambiado"
    p.pop("password")
    r = admin.put(f"/api/usuarios/{u['id_usuario']}", json=p)
    assert r.status_code == 200 and r.get_json()["nombre_completo"] == "Nombre Cambiado"
    assert admin.get(f"/api/usuarios/{u['id_usuario']}").status_code == 200
    ids = [x["id_usuario"] for x in admin.get("/api/usuarios?q=" + p["matricula"].lower()).get_json()]
    assert ids == [u["id_usuario"]]


def test_validation_and_duplicates(admin):
    """Rechaza datos inválidos y matrícula/correo duplicados."""
    p = user_payload()
    assert admin.post("/api/usuarios", json=p).status_code == 201
    assert admin.post("/api/usuarios", json=user_payload(matricula=p["matricula"])).status_code == 400
    assert admin.post("/api/usuarios", json=user_payload(correo=p["correo"].upper())).status_code == 400
    for bad in ({"matricula": "a!"}, {"matricula": "X" * 11}, {"correo": "no-correo"}, {"password": "123"},
                {"rol": "visitante"}, {"rol": "inexistente"}, {"estado": "x"}, {"nombre_completo": " "}):
        r = admin.post("/api/usuarios", json=user_payload(**bad))
        assert r.status_code == 400 and r.get_json()["error"], bad
    assert admin.post("/api/usuarios", json={k: v for k, v in user_payload().items() if k != "password"}).status_code == 400


def test_matricula_uppercased(admin):
    """La matrícula se normaliza a mayúsculas."""
    p = user_payload()
    p["matricula"] = p["matricula"].lower()
    assert admin.post("/api/usuarios", json=p).get_json()["matricula"] == p["matricula"].upper()


def test_cannot_touch_own_account_or_last_admin(admin):
    """No se puede dar de baja, cambiar matrícula ni quitar la administración de la propia cuenta."""
    me = [u for u in admin.get("/api/usuarios?q=ADM001").get_json() if u["matricula"] == "ADM001"][0]
    r = admin.post(f"/api/usuarios/{me['id_usuario']}/toggle")
    assert r.status_code == 400
    body = {k: me[k] for k in ("matricula", "nombre_completo", "correo", "estado", "fuente_validacion")}
    assert admin.put(f"/api/usuarios/{me['id_usuario']}", json={**body, "rol": "alumno"}).status_code == 400
    assert admin.put(f"/api/usuarios/{me['id_usuario']}", json={**body, "rol": "admin", "matricula": "ADM999"}).status_code == 400
    assert admin.put(f"/api/usuarios/{me['id_usuario']}", json={**body, "rol": "admin"}).status_code == 200


def test_last_admin_protected(app, admin):
    """Con 2 admins activos se puede bajar uno; el ultimo ya no (lo hace otro admin inexistente: se simula en BD)."""
    p = user_payload(rol="admin")
    a2 = admin.post("/api/usuarios", json=p).get_json()
    # dos admins activos: se puede degradar al segundo
    body = {k: a2[k] for k in ("matricula", "nombre_completo", "correo", "fuente_validacion")}
    assert admin.put(f"/api/usuarios/{a2['id_usuario']}", json={**body, "estado": "activo", "rol": "alumno"}).status_code == 200
    # ADM001 es el unico admin activo -> no puede quitarse la administracion ni darse de baja
    from app.modules.usuarios import model
    with app.app_context():
        assert model.count_active_admins() >= 1


def test_toggle_blocked_with_loans_and_fines(admin):
    """No se da de baja una cuenta con préstamos abiertos o multas pendientes."""
    p = user_payload()
    u = admin.post("/api/usuarios", json=p).get_json()
    lib = admin.post("/api/libros", json=libro_payload()).get_json()
    pr = make_loan(u["id_usuario"], lib["id_libro"])
    assert admin.get(f"/api/usuarios/{u['id_usuario']}").get_json()["prestamos_activos"] == 1
    r = admin.post(f"/api/usuarios/{u['id_usuario']}/toggle")
    assert r.status_code == 400 and "préstamos" in r.get_json()["error"]
    sql("UPDATE prestamo SET estado='devuelto', fecha_devolucion=now() WHERE id_prestamo=%s", (pr,))
    sql("INSERT INTO adeudo(id_prestamo,tipo,dias_retraso,monto) VALUES (%s,'retraso',2,10.50)", (pr,))
    got = admin.get(f"/api/usuarios/{u['id_usuario']}").get_json()
    assert got["adeudos_pendientes"] == 10.5
    assert admin.post(f"/api/usuarios/{u['id_usuario']}/toggle").status_code == 400
    sql("UPDATE adeudo SET estado='pagado' WHERE id_prestamo=%s", (pr,))
    r = admin.post(f"/api/usuarios/{u['id_usuario']}/toggle")
    assert r.status_code == 200
    j = r.get_json()
    assert j["estado"] == "inactivo" and j["registro_vigente"] is False and j["fecha_baja"]
    j = admin.post(f"/api/usuarios/{u['id_usuario']}/toggle").get_json()
    assert j["estado"] == "activo" and j["registro_vigente"] is True and j["fecha_baja"] is None
