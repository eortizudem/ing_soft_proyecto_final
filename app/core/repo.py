"""Acceso a datos generico y seguro: SQL dinamico con psycopg.sql (identificadores validados, valores siempre
como parametros). Los nombres de tablas/columnas vienen del codigo, jamas de la peticion.

    row = repo.insert("libro", {"clave": "X1", ...}, returning="id_libro")
    rows = repo.select(BASE_SQL, {"estado": "activo"}, search=(q, ["v.titulo", "v.autor"]), order="v.clave")
"""
import re

from psycopg import sql

from . import db
from .errors import ApiError

fetch_one = db.fetchone
fetch_all = db.fetchall
execute = db.execute

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_ORDER = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?)(?:\s+(ASC|DESC))?$", re.I)
_OPS = {"gt": ">", "gte": ">=", "lt": "<", "lte": "<=", "ne": "<>"}
_columns_cache = {}


def ident(name):
    """Identifier seguro ('tabla' o 'alias.columna'); lanza ValueError si el nombre no es valido."""
    parts = str(name).split(".")
    if len(parts) > 2 or not all(_IDENT.match(p) for p in parts):
        raise ValueError(f"Identificador no permitido: {name!r}")
    return sql.Identifier(*parts)


def table_columns(table):
    """Columnas reales de `table` (information_schema, en cache): es la lista blanca de insert/update."""
    cols = _columns_cache.get(table)
    if cols is None:
        ident(table)
        rows = fetch_all("SELECT column_name FROM information_schema.columns "
                         "WHERE table_schema = current_schema() AND table_name = %s", (table,))
        cols = frozenset(r["column_name"] for r in rows)
        if not cols:
            raise ValueError(f"Tabla desconocida: {table!r}")
        _columns_cache[table] = cols
    return cols


def _check_columns(table, names):
    """Lanza ValueError si alguna de `names` no es columna real de `table` (lista blanca)."""
    unknown = set(names) - table_columns(table)
    if unknown:
        raise ValueError(f"Columnas desconocidas en {table}: {sorted(unknown)}")


def _returning(returning):
    """Fragmento ` RETURNING ...` a partir de None/'*'/columna/lista de columnas (vacio si falsy)."""
    if not returning:
        return sql.SQL("")
    cols = sql.SQL("*") if returning == "*" else sql.SQL(", ").join(
        ident(c) for c in ([returning] if isinstance(returning, str) else returning))
    return sql.SQL(" RETURNING ") + cols


def or_404(row, message="No se encontró el registro."):
    """Devuelve `row` o lanza ApiError 404 si es None."""
    if row is None:
        raise ApiError(message, 404)
    return row


def get_or_404(table, pk_col, id_, message="No se encontró el registro."):
    """Fila de `table` por clave primaria o ApiError 404."""
    _check_columns(table, [pk_col])
    q = sql.SQL("SELECT * FROM {} WHERE {} = %s").format(ident(table), ident(pk_col))
    return or_404(fetch_one(q, (id_,)), message)


def insert(table, data, returning="*"):
    """INSERT dinamico; `data` = {columna: valor}. Devuelve la fila RETURNING (dict) o None."""
    _check_columns(table, data)
    if data:
        q = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
            ident(table), sql.SQL(", ").join(map(ident, data)), sql.SQL(", ").join(sql.Placeholder() * len(data)))
    else:
        q = sql.SQL("INSERT INTO {} DEFAULT VALUES").format(ident(table))
    return _run(q + _returning(returning), list(data.values()), returning)


def update(table, pk_col, id_, data, returning="*"):
    """UPDATE dinamico por clave primaria; solo toca las columnas de `data` (None -> NULL)."""
    if not data:
        raise ValueError("update() requiere al menos una columna.")
    _check_columns(table, [pk_col, *data])
    sets = sql.SQL(", ").join(sql.SQL("{} = %s").format(ident(c)) for c in data)
    q = sql.SQL("UPDATE {} SET {} WHERE {} = %s").format(ident(table), sets, ident(pk_col))
    return _run(q + _returning(returning), [*data.values(), id_], returning)


def _run(query, params, returning):
    """Ejecuta `query`: con `returning` devuelve la fila; si no, solo ejecuta y devuelve None."""
    if returning:
        return fetch_one(query, params)
    execute(query, params)
    return None


def like_pattern(q):
    """Patron LIKE seguro (escapa \\ % _); se compara con unaccent(lower(..)) en SQL."""
    q = str(q or "").strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{q}%"


def build_where(filters=None, search=None):
    """Condiciones AND -> (Composed, params). Ignora filtros None/''.

    filters: {col: valor} igualdad; lista -> ANY; sufijos __gt __gte __lt __lte __ne ("v.disponibles__gt": 0).
    search: (texto, [columnas]) busqueda sin acentos ni mayusculas (unaccent ILIKE) sobre varias columnas.
    """
    parts, params = [], []
    for key, value in (filters or {}).items():
        if value is None or value == "":
            continue
        col, _, op = key.partition("__")
        if op and op not in _OPS:
            raise ValueError(f"Operador no permitido: {op!r}")
        if isinstance(value, (list, tuple, set)):
            if op:
                raise ValueError("Una lista solo admite igualdad.")
            if not value:
                parts.append(sql.SQL("FALSE"))
                continue
            parts.append(sql.SQL("{} = ANY(%s)").format(ident(col)))
            params.append(list(value))
        else:
            parts.append(sql.SQL("{} {} %s").format(ident(col), sql.SQL(_OPS.get(op, "="))))
            params.append(value)
    if search:
        text, cols = search
        if str(text or "").strip():
            pat = like_pattern(text)
            parts.append(sql.SQL("({})").format(sql.SQL(" OR ").join(
                sql.SQL("unaccent(lower({}::text)) LIKE unaccent(lower(%s))").format(ident(c)) for c in cols)))
            params += [pat] * len(cols)
    return (sql.SQL(" AND ").join(parts) if parts else sql.SQL("TRUE")), params


def _order_by(order):
    """Fragmento ` ORDER BY` validado con `_ORDER` (columna [ASC|DESC]); ValueError si algun item no es valido."""
    if not order:
        return sql.SQL("")
    items = []
    for item in [order] if isinstance(order, str) else order:
        m = _ORDER.match(item.strip())
        if not m:
            raise ValueError(f"ORDER BY no permitido: {item!r}")
        items.append(ident(m.group(1)) + sql.SQL(" " + m.group(2).upper() if m.group(2) else ""))
    return sql.SQL(" ORDER BY ") + sql.SQL(", ").join(items)


LIMITE_LISTADO = 500   # filas por defecto de los listados administrativos grandes (D-15, p95 <= 3 s con volumen)
MAX_LISTADO = 2000


def tope(limite):
    """`limite` pedido por el cliente acotado a 1..MAX_LISTADO (valor invalido o vacio -> LIMITE_LISTADO)."""
    return min(max(limite, 1), MAX_LISTADO) if isinstance(limite, int) and limite else LIMITE_LISTADO


def select(base, filters=None, search=None, order=None, limit=None):
    """Lista filas: `base` (SELECT estatico del modelo) + WHERE de build_where + ORDER BY validado (+ LIMIT)."""
    where, params = build_where(filters, search)
    q = sql.SQL("{} WHERE {}").format(sql.SQL(base), where) + _order_by(order)
    if limit:
        q += sql.SQL(" LIMIT {}").format(sql.Literal(int(limit)))
    return fetch_all(q, params)


def exists(table, where, exclude=None, ci=(), any_of=False):
    """¿Hay filas con `where` ({col: valor}, AND; OR con any_of)? `ci`: columnas sin distinguir mayusculas.

    exclude=(pk_col, id) ignora esa fila (util al editar).
    """
    _check_columns(table, [*where, *ci, *([exclude[0]] if exclude else [])])
    conds = [sql.SQL("lower({}) = lower(%s)" if c in ci else "{} = %s").format(ident(c)) for c in where]
    q = sql.SQL("SELECT 1 FROM {} WHERE ({})").format(
        ident(table), sql.SQL(" OR " if any_of else " AND ").join(conds))
    params = list(where.values())
    if exclude and exclude[1] is not None:
        q += sql.SQL(" AND {} <> %s").format(ident(exclude[0]))
        params.append(exclude[1])
    return fetch_one(q + sql.SQL(" LIMIT 1"), params) is not None


def count(table, where=None):
    """Numero de filas de `table` que cumplen `where` ({col: valor}; None/'' se ignoran)."""
    _check_columns(table, [k.partition("__")[0] for k in (where or {})])
    cond, params = build_where(where)
    q = sql.SQL("SELECT count(*)::int AS n FROM {} WHERE {}").format(ident(table), cond)
    return fetch_one(q, params)["n"]


def get_or_create(table, where, pk_col, extra=None):
    """Id de la fila con `where`; si no existe la inserta (con `extra`) y devuelve su id."""
    _check_columns(table, [pk_col, *where])
    cond, params = build_where(where)
    row = fetch_one(sql.SQL("SELECT {} FROM {} WHERE {} LIMIT 1").format(ident(pk_col), ident(table), cond), params)
    return (row or insert(table, {**where, **(extra or {})}, returning=pk_col))[pk_col]
