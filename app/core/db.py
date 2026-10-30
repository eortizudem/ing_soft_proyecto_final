"""Acceso a PostgreSQL con psycopg 3: una conexion por peticion (dict_row)."""
import psycopg
from flask import current_app, g
from psycopg.rows import dict_row


def connect(url=None):
    """Abre una conexion psycopg con filas `dict`; sin `url` usa `DATABASE_URL` de la app actual."""
    return psycopg.connect(url or current_app.config["DATABASE_URL"], row_factory=dict_row)


def get_conn():
    """Conexion de la peticion actual (se crea perezosamente y se guarda en `g`)."""
    if "db" not in g:
        g.db = connect()
    return g.db


def fetchall(sql, params=()):
    """Ejecuta `sql` y devuelve todas las filas (lista de dict)."""
    with get_conn().cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def fetchone(sql, params=()):
    """Ejecuta `sql` y devuelve la primera fila (dict) o None."""
    with get_conn().cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def execute(sql, params=()):
    """Ejecuta `sql` sin leer resultados; devuelve las filas afectadas."""
    with get_conn().cursor() as cur:
        cur.execute(sql, params)
        return cur.rowcount


def init_app(app):
    """Registra el ciclo transaccional por peticion.

    `after_request` hace commit si el status es < 400 y rollback en caso contrario; `teardown_appcontext` cierra la conexion.
    """
    @app.after_request
    def finish(response):
        """Confirma o revierte la transaccion segun el status de la respuesta."""
        conn = g.get("db")
        if conn is not None:
            if response.status_code < 400:
                conn.commit()
            else:
                conn.rollback()
        return response

    @app.teardown_appcontext
    def close(_exc):
        """Cierra la conexion de la peticion, si se abrio."""
        conn = g.pop("db", None)
        if conn is not None:
            conn.close()
