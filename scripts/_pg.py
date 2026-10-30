"""Ayudas compartidas por los scripts que hablan con PostgreSQL en Docker (solo biblioteca estandar).

Modulo interno (no se ejecuta directamente): lo importan respaldo.py, restaurar.py, medir_rendimiento.py y
cargar_datos_volumen.py. Ejecuta `docker compose exec` contra el servicio `db`, por lo que requiere el stack
levantado (python3 scripts/levantar.py).

Configuracion: lee POSTGRES_USER, POSTGRES_DB y POSTGRES_PASSWORD de .env (si existe); las variables del
entorno del proceso tienen prioridad. Por defecto todas valen `librigest`.

Constantes:
    RAIZ: directorio raiz del proyecto (cwd de todos los comandos docker compose).
    CONTEO_SQL: consulta que devuelve `tabla=filas` para cada tabla base del esquema public.
"""
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CONTEO_SQL = """SELECT table_name || '=' || (xpath('/row/c/text()', query_to_xml(
  format('SELECT count(*) AS c FROM %I.%I', table_schema, table_name), false, true, '')))[1]::text
FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY 1"""


def salir(msg, codigo=1):
    """Imprime `ERROR: msg` en stderr y termina el proceso.

    Args:
        msg: mensaje de error para el usuario.
        codigo: codigo de salida del proceso (1 por defecto).

    Raises:
        SystemExit: siempre.
    """
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(codigo)


def _env_archivo():
    """Lee las variables de `.env` en la raiz del proyecto (ignora lineas vacias y comentarios).

    Returns:
        dict clave -> valor (sin comillas); vacio si no existe el archivo. El llamador decide la
        precedencia frente a `os.environ`.
    """
    valores = {}
    archivo = RAIZ / ".env"
    if archivo.exists():
        for linea in archivo.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                clave, _, valor = linea.partition("=")
                valores[clave.strip()] = valor.strip().strip("\"'")
    return valores


def config():
    """Credenciales de PostgreSQL: `.env` combinado con el entorno (el entorno gana).

    Returns:
        dict con las claves `usuario`, `db` y `clave` (por defecto `librigest` las tres).
    """
    env = {**_env_archivo(), **os.environ}
    return {"usuario": env.get("POSTGRES_USER", "librigest"), "db": env.get("POSTGRES_DB", "librigest"),
            "clave": env.get("POSTGRES_PASSWORD", "librigest")}


def compose(*args, **kw):
    """Ejecuta `docker compose <args>` con cwd en la raiz del proyecto.

    Args:
        *args: argumentos de docker compose (p. ej. "exec", "-T", "db", ...).
        **kw: opciones de `subprocess.run` (capture_output, input, stdout, ...). Si no se indica `stdin`,
            se usa DEVNULL para que docker no consuma el stdin del usuario.

    Returns:
        subprocess.CompletedProcess del comando (no lanza si el codigo de salida es != 0).
    """
    kw.setdefault("stdin", subprocess.DEVNULL)  # que docker no consuma el stdin del usuario
    return subprocess.run(["docker", "compose", *args], cwd=RAIZ, **kw)


def psql(usuario, db, sentencia, base="postgres"):
    """Ejecuta una sentencia SQL con psql (`-At`, ON_ERROR_STOP) en el contenedor db.

    Args:
        usuario: rol de PostgreSQL.
        db: base de datos a la que se conecta si `base` es falsy.
        sentencia: SQL a ejecutar (`psql -c`).
        base: base de conexion; por defecto `postgres` (necesario para CREATE/DROP DATABASE). Pasar
            `base=db` para ejecutar dentro de `db`.

    Returns:
        Salida estandar de psql (texto, sin alinear y sin encabezados).

    Raises:
        SystemExit: si psql falla (via `salir`).
    """
    r = compose("exec", "-T", "db", "psql", "-U", usuario, "-d", base or db, "-v", "ON_ERROR_STOP=1", "-At",
                "-c", sentencia, capture_output=True, text=True)
    if r.returncode != 0:
        salir(f"psql fallo: {r.stderr.strip()}")
    return r.stdout


def verificar_docker():
    """Comprueba que el servicio `db` este en ejecucion.

    Raises:
        SystemExit: si `docker compose exec db true` falla (via `salir`).
    """
    r = compose("exec", "-T", "db", "true", capture_output=True)
    if r.returncode != 0:
        salir("El servicio 'db' no esta en ejecucion. Levanta el stack con: python3 scripts/levantar.py")


def conteos(usuario, db):
    """Cuenta las filas de cada tabla base del esquema public.

    Args:
        usuario: rol de PostgreSQL.
        db: base de datos a consultar.

    Returns:
        dict {tabla: filas}.

    Raises:
        SystemExit: si psql falla (via `psql`).
    """
    salida = psql(usuario, db, CONTEO_SQL, base=db)
    return {k: int(v) for k, _, v in (l.partition("=") for l in salida.splitlines() if l)}


def psql_script(usuario, db, texto):
    """Ejecuta un script SQL completo en `db` (psql `-f -`, ON_ERROR_STOP).

    Args:
        usuario: rol de PostgreSQL.
        db: base de datos destino.
        texto: contenido del script, enviado por stdin.

    Returns:
        Salida estandar de psql.

    Raises:
        SystemExit: ante el primer error de SQL (via `salir`).
    """
    r = compose("exec", "-T", "db", "psql", "-U", usuario, "-d", db, "-v", "ON_ERROR_STOP=1", "-q", "-f", "-",
                input=texto, capture_output=True, text=True, stdin=None)
    if r.returncode != 0:
        salir(f"psql fallo: {r.stderr.strip()}")
    return r.stdout
