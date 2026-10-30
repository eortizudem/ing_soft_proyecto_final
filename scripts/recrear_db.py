#!/usr/bin/env python3
"""Recrea por completo la base de datos de LibriGest y la siembra.

Uso:
  python scripts/recrear_db.py              # pide confirmacion [s/N], recrea y siembra
  python scripts/recrear_db.py -y           # igual, sin confirmacion (--yes)
  python scripts/recrear_db.py --sin-semilla  # solo esquema: omite db/*seed*.sql y la semilla de usuarios

Pasos: levanta el contenedor db y espera pg_isready; DROP SCHEMA public CASCADE + CREATE SCHEMA + extension
unaccent; aplica todos los db/*.sql en orden alfabetico; (salvo --sin-semilla) arranca web y ejecuta la semilla
de usuarios y compras (python -m app.seed); imprime las filas por tabla.

Codigos de salida: 0 correcto; 1 cancelado por el usuario o error de docker/PostgreSQL/SQL (o el codigo del
paso que fallo).

SEGURIDAD: DESTRUCTIVO. Borra TODOS los datos de la base configurada (POSTGRES_DB). Sin -y exige responder
s/si/y; usar -y solo en automatizaciones. Para conservar datos, haga antes `python scripts/respaldo.py`.
"""
import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
# Tablas cuyo conteo se imprime al final (las 21 de db/01_schema.sql).
TABLAS = ["permiso", "rol", "rol_permiso", "usuario", "bitacora", "recuperacion_contrasena", "reporte_generado",
          "solicitud_compra", "detalle_solicitud", "ubicacion", "libro", "ejemplar", "politica_prestamo",
          "prestamo", "adeudo", "renovacion", "lista_espera", "intencion", "conversacion", "mensaje",
          "pregunta_frecuente"]
# Comando psql ejecutado dentro del contenedor (las variables POSTGRES_* las define el servicio db).
PSQL = 'psql -v ON_ERROR_STOP=1 -q -U "$POSTGRES_USER" -d "$POSTGRES_DB"'


def salir(msg, codigo=1):
    """Imprime `ERROR: msg` en stderr y termina el proceso.

    Args:
        msg: mensaje de error.
        codigo: codigo de salida (1 por defecto).

    Raises:
        SystemExit: siempre.
    """
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(codigo)


def dc(args, **kw):
    """Ejecuta `docker compose <args>` en la raiz del proyecto.

    Args:
        args: lista de argumentos de compose.
        **kw: opciones de `subprocess.run`.

    Returns:
        subprocess.CompletedProcess.
    """
    return subprocess.run(["docker", "compose"] + args, cwd=RAIZ, **kw)


def psql(stdin_bytes=None, stdin_file=None, extra=""):
    """Ejecuta psql (ON_ERROR_STOP, silencioso) dentro del contenedor db leyendo el SQL por stdin.

    Args:
        stdin_bytes: SQL en bytes (se usa si no hay `stdin_file`).
        stdin_file: ruta de un archivo .sql que se envia por stdin.
        extra: opciones adicionales de psql (p. ej. "-t -A -F '|'").

    Returns:
        subprocess.CompletedProcess con stdout/stderr capturados (en bytes).
    """
    cmd = ["exec", "-T", "db", "sh", "-c", f"{PSQL} {extra}"]
    if stdin_file:
        with open(stdin_file, "rb") as f:
            return dc(cmd, stdin=f, capture_output=True)
    return dc(cmd, input=stdin_bytes, capture_output=True)


def chequear(res, paso):
    """Verifica el resultado de un paso e imprime `OK`.

    Args:
        res: CompletedProcess devuelto por `psql`/`dc`.
        paso: descripcion del paso, para los mensajes.

    Raises:
        SystemExit: con el codigo del proceso si fallo (tras volcar su stderr).
    """
    if res.returncode:
        sys.stderr.write(res.stderr.decode("utf-8", "replace"))
        salir(f"Falló el paso: {paso}", res.returncode)
    print(f"  OK  {paso}")


def main():
    """Punto de entrada: confirma, recrea el esquema, aplica db/*.sql, siembra y cuenta filas.

    Returns:
        None. Termina con `sys.exit` ante cancelacion o error (ver codigos en el docstring del modulo).
    """
    ap = argparse.ArgumentParser(description="Recrea y siembra la base de datos.")
    ap.add_argument("-y", "--yes", action="store_true", help="no pedir confirmación")
    ap.add_argument("--sin-semilla", action="store_true", help="solo esquema, sin datos")
    a = ap.parse_args()

    if not shutil.which("docker"):
        salir("No se encontró 'docker'. Instálalo y vuelve a intentar.")
    if dc(["version"], capture_output=True).returncode or subprocess.run(
            ["docker", "info"], capture_output=True).returncode:
        salir("Docker/Compose no disponible o el demonio no responde.")
    if not a.yes:
        if input("Esto borrará TODOS los datos. ¿Continuar? [s/N] ").strip().lower() not in ("s", "si", "sí", "y"):
            print("Cancelado.")
            sys.exit(1)

    print("Asegurando que el contenedor db esté activo...")
    if dc(["up", "-d", "db"]).returncode:
        salir("No se pudo iniciar el contenedor db.")
    for _ in range(40):
        if dc(["exec", "-T", "db", "sh", "-c", 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'],
              capture_output=True).returncode == 0:
            break
        time.sleep(2)
    else:
        salir("PostgreSQL no quedó listo a tiempo.")

    print("Recreando esquema:")
    chequear(psql(b"DROP SCHEMA public CASCADE; CREATE SCHEMA public; "
                  b"CREATE EXTENSION IF NOT EXISTS unaccent;"), "borrar esquema public")
    # Todos los db/*.sql en orden alfabetico (01_schema, 02_seed, ...); --sin-semilla omite los que contienen "seed".
    for archivo in sorted((RAIZ / "db").glob("*.sql")):
        if a.sin_semilla and "seed" in archivo.stem:
            continue
        chequear(psql(stdin_file=archivo), f"aplicar db/{archivo.name}")
    if not a.sin_semilla:
        if dc(["up", "-d", "web"], capture_output=True).returncode:
            salir("No se pudo iniciar el contenedor web.")
        r = None
        for _ in range(20):  # web puede estar arrancando
            r = dc(["exec", "-T", "web", "python", "-m", "app.seed"], capture_output=True)
            if r.returncode == 0:
                break
            time.sleep(2)
        chequear(r, "semilla de usuarios y compras (python -m app.seed)")
        print("  " + r.stdout.decode("utf-8", "replace").strip().splitlines()[-1])

    consulta = " UNION ALL ".join(f"SELECT '{t}' AS tabla, count(*) AS filas FROM {t}" for t in TABLAS)
    r = psql(consulta.encode(), extra="-t -A -F '|'")
    chequear(r, "contar filas")
    print("\nFilas por tabla:")
    for linea in r.stdout.decode().splitlines():
        if "|" in linea:
            t, n = linea.split("|")
            print(f"  {t:<26}{n:>6}")
    print("\nBase de datos lista.")


if __name__ == "__main__":
    main()
