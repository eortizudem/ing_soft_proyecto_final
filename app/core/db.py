"""Acceso a PostgreSQL con psycopg 3: una conexion por peticion (dict_row)."""
import psycopg
from flask import current_app, g
from psycopg.rows import dict_row


def connect(url=None):
    return psycopg.connect(url or current_app.config["DATABASE_URL"], row_factory=dict_row)


def get_conn():
    if "db" not in g:
        g.db = connect()
    return g.db


def fetchall(sql, params=()):
    with get_conn().cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def fetchone(sql, params=()):
    with get_conn().cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def execute(sql, params=()):
    with get_conn().cursor() as cur:
        cur.execute(sql, params)
        return cur.rowcount


def init_app(app):
    @app.after_request
    def finish(response):
        conn = g.get("db")
        if conn is not None:
            if response.status_code < 400:
                conn.commit()
            else:
                conn.rollback()
        return response

    @app.teardown_appcontext
    def close(_exc):
        conn = g.pop("db", None)
        if conn is not None:
            conn.close()
