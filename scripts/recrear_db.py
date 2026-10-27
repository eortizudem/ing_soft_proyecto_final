#!/usr/bin/env python3
"""Recrea por completo la base de datos de LibriGest y la siembra.

Uso: python scripts/recrear_db.py [--yes] [--sin-semilla]
Aplica todos los db/*.sql en orden alfabetico y despues la semilla de usuarios (python -m app.seed).
"""
import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TABLAS = ["permiso", "rol", "rol_permiso", "usuario", "bitacora", "recuperacion_contrasena", "reporte_generado",
          "solicitud_compra", "detalle_solicitud", "ubicacion", "libro", "ejemplar", "politica_prestamo",
          "prestamo", "adeudo", "renovacion", "lista_espera", "intencion", "conversacion", "mensaje",
          "pregunta_frecuente"]
PSQL = 'psql -v ON_ERROR_STOP=1 -q -U "$POSTGRES_USER" -d "$POSTGRES_DB"'


def salir(msg, codigo=1):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(codigo)


def dc(args, **kw):
    return subprocess.run(["docker", "compose"] + args, cwd=RAIZ, **kw)


def psql(stdin_bytes=None, stdin_file=None, extra=""):
    cmd = ["exec", "-T", "db", "sh", "-c", f"{PSQL} {extra}"]
    if stdin_file:
        with open(stdin_file, "rb") as f:
            return dc(cmd, stdin=f, capture_output=True)
    return dc(cmd, input=stdin_bytes, capture_output=True)


def chequear(res, paso):
    if res.returncode:
        sys.stderr.write(res.stderr.decode("utf-8", "replace"))
        salir(f"Falló el paso: {paso}", res.returncode)
    print(f"  OK  {paso}")


def main():
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
