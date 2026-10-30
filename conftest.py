"""Fixtures globales de pytest: app, limpieza de datos de la sesion y clientes autenticados por rol semilla."""
import pytest

from app import create_app
from app.testing import client_as, sql

# Orden de borrado respetando FKs; solo se eliminan filas creadas durante la sesion de pruebas.
_TABLAS = [("mensaje", "id_mensaje"), ("conversacion", "id_conversacion"), ("lista_espera", "id_espera"),
           ("adeudo", "id_adeudo"), ("renovacion", "id_renovacion"), ("prestamo", "id_prestamo"),
           ("detalle_solicitud", "id_detalle"), ("solicitud_compra", "id_solicitud"), ("ejemplar", "id_ejemplar"),
           ("libro", "id_libro"), ("ubicacion", "id_ubicacion"), ("recuperacion_contrasena", "id_token"),
           ("reporte_generado", "id_reporte"), ("bitacora", "id_bitacora"), ("usuario", "id_usuario")]


@pytest.fixture(scope="session")
def app():
    """Aplicacion Flask unica para toda la sesion de pruebas."""
    return create_app()


@pytest.fixture(scope="session", autouse=True)
def limpiar_datos(app):
    """Al terminar la sesion borra las filas creadas por las pruebas (id mayor al maximo previo en cada tabla)."""
    snap = {t: sql(f"SELECT COALESCE(max({pk}),0) AS m FROM {t}")[0]["m"] for t, pk in _TABLAS}
    yield
    for t, pk in _TABLAS:
        sql(f"DELETE FROM {t} WHERE {pk} > %s", (snap[t],))


@pytest.fixture
def anon(app):
    """Cliente sin sesion iniciada."""
    return app.test_client()


@pytest.fixture
def login_as(app):
    """Fabrica de clientes autenticados: login_as("ADM001", "Admin123")."""
    return lambda matricula, password: client_as(app, matricula, password)


def _cliente(nombre, matricula, password):
    """Declara el fixture `nombre` (cliente ya autenticado con esas credenciales semilla)."""
    @pytest.fixture(name=nombre)
    def fixture(login_as):
        """Cliente autenticado con las credenciales semilla del rol."""
        return login_as(matricula, password)
    return fixture


admin = _cliente("admin", "ADM001", "Admin123")
as_admin = _cliente("as_admin", "ADM001", "Admin123")
alumno = _cliente("alumno", "A0512345", "Alumno123")
catalogo = _cliente("catalogo", "CAT001", "Catalogo123")
comprador = _cliente("comprador", "COM001", "Compras123")
bibliotecario = _cliente("bibliotecario", "BIB001", "Biblioteca123")
docente = _cliente("docente", "DOC001", "Docente123")
colaborador = _cliente("colaborador", "COL001", "Colabora123")
alumno2 = _cliente("alumno2", "A0512980", "Alumno123")
