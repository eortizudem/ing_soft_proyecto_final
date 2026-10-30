"""Utilidades de prueba: acceso directo a la BD, clientes autenticados y fabricas de usuarios, libros y prestamos.
No se usa en produccion; requiere `DATABASE_URL` en el entorno."""
import os
import uuid

import psycopg
from psycopg.rows import dict_row
from werkzeug.security import generate_password_hash


def url():
    """URL de la BD de pruebas (variable de entorno obligatoria `DATABASE_URL`)."""
    return os.environ["DATABASE_URL"]


def sql(query, params=()):
    """Ejecuta `query` con conexion propia en autocommit; devuelve filas (dict) o None si no produce resultados.

    Al ser autocommit, lo escrito persiste (lo limpia el fixture `limpiar_datos` de conftest.py).
    """
    with psycopg.connect(url(), row_factory=dict_row, autocommit=True) as c:
        cur = c.execute(query, params)
        return cur.fetchall() if cur.description else None


def uniq(n=6):
    """Sufijo aleatorio en mayusculas de `n` caracteres hexadecimales, para datos de prueba unicos."""
    return uuid.uuid4().hex[:n].upper()


def login(client, matricula, password):
    """POST /api/login con las credenciales dadas; devuelve la respuesta sin validarla."""
    return client.post("/api/login", json={"matricula": matricula, "password": password})


def client_as(app, matricula, password):
    """Cliente de pruebas ya autenticado; falla con `assert` si el login no devuelve 200."""
    c = app.test_client()
    r = login(c, matricula, password)
    assert r.status_code == 200, r.get_json()
    return c


def user_payload(**over):
    """Cuerpo valido para crear un usuario (alumno activo con datos unicos); `over` sobrescribe campos."""
    s = uniq()
    d = {"matricula": f"T{uniq(9)}", "nombre_completo": f"Usuario Prueba {s}", "correo": f"t{s.lower()}@ducky.edu.mx",
         "rol": "alumno", "estado": "activo", "fuente_validacion": "manual", "password": "Prueba123"}
    d.update(over)
    return d


def libro_payload(**over):
    """Cuerpo valido para crear un libro prestable con 3 ejemplares y datos unicos; `over` sobrescribe campos."""
    s = uniq()
    d = {"clave": f"X{s}", "titulo": f"Libro de prueba {s}", "autor": "Autor Prueba", "editorial": "Editorial",
         "tema": "Pruebas", "anio_publicacion": 2020, "tipo_uso": "prestamo_externo", "clasificacion": "000 PRU",
         "sinopsis": "Sinopsis de prueba", "precio_referencia": 100, "ejemplares": 3, "planta": "Planta baja",
         "pasillo": "A", "librero": 3, "nivel": 2, "estado": "activo"}
    d.update(over)
    return d


def make_loan(id_usuario, id_libro):
    """Crea un prestamo activo directamente en BD y marca el ejemplar prestado."""
    ej = sql("SELECT id_ejemplar FROM ejemplar WHERE id_libro=%s AND estado='disponible' ORDER BY numero_copia LIMIT 1",
             (id_libro,))[0]["id_ejemplar"]
    pol = sql("SELECT id_politica FROM politica_prestamo WHERE id_rol=(SELECT id_rol FROM usuario WHERE id_usuario=%s) LIMIT 1",
              (id_usuario,))[0]["id_politica"]
    sql("UPDATE ejemplar SET estado='prestado' WHERE id_ejemplar=%s", (ej,))
    return sql("INSERT INTO prestamo(id_ejemplar,id_usuario,id_politica,fecha_vencimiento) "
               "VALUES (%s,%s,%s,CURRENT_DATE+7) RETURNING id_prestamo", (ej, id_usuario, pol))[0]["id_prestamo"]


def make_user(**over):
    """Inserta un usuario directo en BD (sin pasar por la API). Devuelve la fila + 'password' en claro."""
    p = user_payload(**over)
    row = sql("INSERT INTO usuario(matricula,nombre_completo,correo,contrasena_hash,id_rol,estado,fuente_validacion,"
              "registro_vigente) VALUES (%s,%s,%s,%s,(SELECT id_rol FROM rol WHERE nombre=%s),%s,%s,%s) RETURNING *",
              (p["matricula"], p["nombre_completo"], p["correo"], generate_password_hash(p["password"]), p["rol"],
               p["estado"], p["fuente_validacion"], p["estado"] == "activo"))[0]
    return {**row, "password": p["password"], "rol": p["rol"]}


def make_book(**over):
    """Inserta libro + ubicacion + ejemplares directo en BD. Devuelve la fila de libro."""
    p = libro_payload(**over)
    ub = sql("INSERT INTO ubicacion(planta,pasillo,librero,nivel) VALUES (%s,%s,%s,%s) RETURNING id_ubicacion",
             (p["planta"], p["pasillo"], f"{p['librero']:02d}", p["nivel"]))[0]["id_ubicacion"]
    cols = ("clave", "titulo", "autor", "editorial", "tema", "anio_publicacion", "tipo_uso", "clasificacion",
            "sinopsis", "precio_referencia", "estado")
    row = sql(f"INSERT INTO libro({', '.join(cols)}, id_ubicacion) VALUES ({', '.join(['%s'] * len(cols))}, %s) "
              "RETURNING *", [p[c] for c in cols] + [ub])[0]
    for n in range(1, p["ejemplares"] + 1):
        sql("INSERT INTO ejemplar(id_libro, numero_copia) VALUES (%s,%s)", (row["id_libro"], n))
    return row
