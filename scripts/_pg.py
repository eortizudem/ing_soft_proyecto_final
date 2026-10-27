"""Ayudas compartidas por los scripts que hablan con PostgreSQL en Docker (solo biblioteca estandar)."""
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CONTEO_SQL = """SELECT table_name || '=' || (xpath('/row/c/text()', query_to_xml(
  format('SELECT count(*) AS c FROM %I.%I', table_schema, table_name), false, true, '')))[1]::text
FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY 1"""


def salir(msg, codigo=1):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(codigo)


def _env_archivo():
    """Variables de .env (si existe); el entorno del proceso tiene prioridad."""
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
    env = {**_env_archivo(), **os.environ}
    return {"usuario": env.get("POSTGRES_USER", "librigest"), "db": env.get("POSTGRES_DB", "librigest"),
            "clave": env.get("POSTGRES_PASSWORD", "librigest")}


def compose(*args, **kw):
    """docker compose <args> en la raiz del proyecto (servicio db, sin TTY)."""
    kw.setdefault("stdin", subprocess.DEVNULL)  # que docker no consuma el stdin del usuario
    return subprocess.run(["docker", "compose", *args], cwd=RAIZ, **kw)


def psql(usuario, db, sentencia, base="postgres"):
    """Ejecuta SQL con psql en el contenedor db; devuelve la salida (texto) o aborta."""
    r = compose("exec", "-T", "db", "psql", "-U", usuario, "-d", base or db, "-v", "ON_ERROR_STOP=1", "-At",
                "-c", sentencia, capture_output=True, text=True)
    if r.returncode != 0:
        salir(f"psql fallo: {r.stderr.strip()}")
    return r.stdout


def verificar_docker():
    r = compose("exec", "-T", "db", "true", capture_output=True)
    if r.returncode != 0:
        salir("El servicio 'db' no esta en ejecucion. Levanta el stack con: python3 scripts/levantar.py")


def conteos(usuario, db):
    """{tabla: filas} de la BD `db` (esquema public)."""
    salida = psql(usuario, db, CONTEO_SQL, base=db)
    return {k: int(v) for k, _, v in (l.partition("=") for l in salida.splitlines() if l)}


def psql_script(usuario, db, texto):
    """Ejecuta un script SQL (texto) completo en `db` con psql; aborta ante el primer error."""
    r = compose("exec", "-T", "db", "psql", "-U", usuario, "-d", db, "-v", "ON_ERROR_STOP=1", "-q", "-f", "-",
                input=texto, capture_output=True, text=True, stdin=None)
    if r.returncode != 0:
        salir(f"psql fallo: {r.stderr.strip()}")
    return r.stdout
