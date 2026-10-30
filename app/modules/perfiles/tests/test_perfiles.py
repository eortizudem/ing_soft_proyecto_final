"""Pruebas de API de `perfiles`: matriz de permisos y su edición (RF-02)."""

def test_matriz(alumno):
    """La matriz expone roles, permisos y valores esperados."""
    j = alumno.get("/api/roles").get_json()
    assert [r["nombre"] for r in j["roles"]][:2] == ["admin", "catalogo"]
    assert len(j["permisos"]) == 15
    assert j["matriz"]["admin"]["perfiles"] is True
    assert j["matriz"]["comprador"]["reportes"] is False
    assert j["matriz"]["alumno"]["compras"] is False


def test_change_requires_permission(alumno):
    """Cambiar un permiso sin el permiso `perfiles` responde 403."""
    assert alumno.put("/api/roles/comprador/permisos/reportes", json={"habilitado": True}).status_code == 403


def test_toggle_permission_and_effect(admin, app):
    """Habilitar un permiso surte efecto en la sesión del rol y queda en bitácora."""
    from app.testing import client_as, sql
    r = admin.put("/api/roles/comprador/permisos/reportes", json={"habilitado": True})
    try:
        assert r.status_code == 200 and r.get_json()["matriz"]["comprador"]["reportes"] is True
        c = client_as(app, "COM001", "Compras123")
        assert "reportes" in c.get("/api/me").get_json()["user"]["permisos"]
        assert c.get("/api/reportes/catalogo_activo").status_code == 200
        assert sql("SELECT 1 FROM bitacora WHERE accion='permiso_cambio' AND detalle LIKE 'comprador/reportes%%'")
    finally:
        admin.put("/api/roles/comprador/permisos/reportes", json={"habilitado": False})
    assert admin.get("/api/roles").get_json()["matriz"]["comprador"]["reportes"] is False


def test_admin_protected_and_not_found(admin):
    """El admin conserva `usuarios`/`perfiles`; rol o permiso inexistente da 404 y valor no booleano 400."""
    for p in ("usuarios", "perfiles"):
        assert admin.put(f"/api/roles/admin/permisos/{p}", json={"habilitado": False}).status_code == 400
    assert admin.put("/api/roles/nada/permisos/usuarios", json={"habilitado": True}).status_code == 404
    assert admin.put("/api/roles/admin/permisos/nada", json={"habilitado": True}).status_code == 404
    assert admin.put("/api/roles/alumno/permisos/buscar", json={"habilitado": "si"}).status_code == 400
