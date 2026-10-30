"""Pruebas de `core.repo`: construccion segura de SQL (whitelists, parametros) y operaciones CRUD contra la BD."""
import psycopg
import pytest

from app.core import repo
from app.core.errors import ApiError
from app.testing import make_book, make_user, sql, uniq, url


@pytest.fixture
def conn():
    """Conexion psycopg auxiliar para renderizar fragmentos SQL."""
    with psycopg.connect(url()) as c:
        yield c


def render(where, conn):
    """Renderiza el fragmento SQL de `build_where` a texto y devuelve (texto, parametros)."""
    return where[0].as_string(conn), where[1]


# ---- build_where (sin tocar datos) ----

def test_where_empty_is_true(conn):
    """Sin filtros el WHERE es TRUE."""
    assert render(repo.build_where({}), conn) == ("TRUE", [])
    assert render(repo.build_where({"a": None, "b": ""}, search=("  ", ["x"])), conn) == ("TRUE", [])


def test_where_equality_ops_and_lists(conn):
    """Igualdad, operadores con sufijo y listas (ANY) generan el SQL esperado."""
    q, p = render(repo.build_where({"u.estado": "activo", "v.disponibles__gt": 0, "id": [1, 2], "x__ne": "k"}), conn)
    assert q == '"u"."estado" = %s AND "v"."disponibles" > %s AND "id" = ANY(%s) AND "x" <> %s'
    assert p == ["activo", 0, [1, 2], "k"]
    assert render(repo.build_where({"id": []}), conn) == ("FALSE", [])


def test_where_values_never_interpolated(conn):
    """Los valores viajan como parametros; nunca se interpolan en el SQL."""
    evil = "x'; DROP TABLE usuario; --"
    q, p = render(repo.build_where({"estado": evil}, search=(evil, ["u.nombre"])), conn)
    assert evil not in q and "DROP" not in q
    assert p == [evil, repo.like_pattern(evil)]


def test_where_search_unaccent(conn):
    """La busqueda es sin acentos/mayusculas y escapa los comodines LIKE."""
    q, p = render(repo.build_where(search=("Cálc_ulo%", ["a.x", "b"])), conn)
    assert q == ('(unaccent(lower("a"."x"::text)) LIKE unaccent(lower(%s)) OR '
                 'unaccent(lower("b"::text)) LIKE unaccent(lower(%s)))')
    assert p == ["%Cálc\\_ulo\\%%"] * 2


@pytest.mark.parametrize("bad", ["a; DROP TABLE x", "a b", "a.b.c", "1a", "", 'a"b', "a-b", "x) OR (1=1"])
def test_identifier_whitelist_rejects(bad):
    """Identificadores con sintaxis no permitida se rechazan con ValueError."""
    with pytest.raises(ValueError):
        repo.ident(bad)
    with pytest.raises(ValueError):
        repo.build_where({bad: 1})
    with pytest.raises(ValueError):
        repo.build_where(search=("q", [bad]))


def test_where_bad_operator_and_order():
    """Operadores y ORDER BY fuera de la lista blanca lanzan ValueError."""
    with pytest.raises(ValueError):
        repo.build_where({"a__like": 1})
    with pytest.raises(ValueError):
        repo.build_where({"a__gt": [1]})
    for bad in ("a; DROP", "a DESC; x", "a ASCX", "1"):
        with pytest.raises(ValueError):
            repo._order_by(bad)


def test_order_by_render(conn):
    """ORDER BY se renderiza con identificadores entrecomillados y direccion en mayusculas."""
    assert repo._order_by(["u.a desc", "b"]).as_string(conn) == ' ORDER BY "u"."a" DESC, "b"'


# ---- operaciones con BD ----

def test_unknown_table_or_column_rejected(app):
    """Tablas o columnas inexistentes se rechazan antes de ejecutar el SQL."""
    with app.app_context():
        with pytest.raises(ValueError):
            repo.insert("no_existe", {"a": 1})
        with pytest.raises(ValueError):
            repo.insert("usuario", {"columna_falsa": 1})
        with pytest.raises(ValueError):
            repo.update("usuario", "id_usuario", 1, {"matricula; --": "x"})
        with pytest.raises(ValueError):
            repo.exists("usuario", {"x": 1})
        with pytest.raises(ValueError):
            repo.update("usuario", "id_usuario", 1, {})


def test_get_or_404_insert_update_exists_count(app):
    """Ciclo insert/get_or_404/update/exists/count sobre una tabla real."""
    u = make_user()
    with app.app_context():
        assert repo.get_or_404("usuario", "id_usuario", u["id_usuario"])["matricula"] == u["matricula"]
        with pytest.raises(ApiError) as e:
            repo.get_or_404("usuario", "id_usuario", -5, "No hay.")
        assert (e.value.status, e.value.message) == (404, "No hay.")
        n = repo.count("usuario", {"matricula": u["matricula"]})
        assert n == 1 and repo.count("usuario", {"matricula": None}) >= 1
        assert repo.exists("usuario", {"matricula": u["matricula"]})
        assert not repo.exists("usuario", {"matricula": u["matricula"]}, exclude=("id_usuario", u["id_usuario"]))
        assert repo.exists("usuario", {"matricula": "NOPE", "correo": u["correo"].upper()}, ci=("correo",), any_of=True)
        assert not repo.exists("usuario", {"matricula": "NOPE", "correo": u["correo"].upper()}, ci=("correo",))
        row = repo.update("usuario", "id_usuario", u["id_usuario"], {"nombre_completo": "Nuevo"})
        assert row["nombre_completo"] == "Nuevo"
        assert repo.update("usuario", "id_usuario", u["id_usuario"], {"fecha_baja": None}, returning=None) is None
        assert repo.update("usuario", "id_usuario", -5, {"nombre_completo": "x"}) is None
        s = uniq()
        r = repo.insert("rol", {"nombre": f"r{s}", "descripcion": "d"}, returning=["id_rol", "nombre"])
        assert set(r) == {"id_rol", "nombre"}
        repo.execute("DELETE FROM rol WHERE id_rol = %s", (r["id_rol"],))


def test_get_or_create_and_select(app):
    """`get_or_create` reutiliza la fila existente y `select` filtra, ordena y limita."""
    b = make_book(tema="Tema" + uniq(), estado="inactivo")
    with app.app_context():
        base = "SELECT * FROM libro l"
        rows = repo.select(base, {"l.tema": b["tema"], "l.estado": "inactivo"}, search=("PRUEBA", ["l.titulo"]),
                           order="l.clave DESC")
        assert [r["clave"] for r in rows] == [b["clave"]]
        assert repo.select(base, {"l.tema": b["tema"], "l.estado": "activo"}) == []
        ub = {"planta": "Planta " + uniq(), "pasillo": "Z", "librero": "01", "nivel": 1}
        i1 = repo.get_or_create("ubicacion", ub, "id_ubicacion")
        assert repo.get_or_create("ubicacion", ub, "id_ubicacion") == i1
    sql("DELETE FROM ubicacion WHERE id_ubicacion=%s", (i1,))


def test_tope_de_listados():
    """`tope` acota el limite a 1..MAX_LISTADO y usa LIMITE_LISTADO si es invalido."""
    from app.core import repo
    assert repo.tope(None) == repo.tope(0) == repo.LIMITE_LISTADO
    assert repo.tope(5) == 5 and repo.tope(-3) == 1
    assert repo.tope(10 ** 9) == repo.MAX_LISTADO
