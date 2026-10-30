#!/usr/bin/env python3
"""Levanta LibriGest (Biblioteca Ducky) con Docker Compose.

Uso:
  python scripts/levantar.py              # build + up -d, espera /api/health y muestra las cuentas demo
  python scripts/levantar.py --no-build   # igual, sin reconstruir la imagen
  python scripts/levantar.py --logs       # tras levantar, sigue los logs del servicio web (Ctrl+C sale)
  python scripts/levantar.py --down       # detiene y elimina los contenedores (el volumen pgdata se conserva)

Pasos: verifica docker / compose v2 / demonio; crea .env desde .env.example si no existe; ejecuta
`docker compose up -d [--build]`; sondea http://localhost:8000/api/health hasta 90 s; imprime URL y credenciales.

Codigos de salida: 0 correcto; 1 error (docker ausente, demonio caido, falta .env.example, fallo de compose o
la API no respondio a tiempo); con --down o `up` fallido se propaga el codigo de docker compose.

Seguridad: no pide confirmacion y no borra datos (--down no usa -v). Las credenciales impresas son
solo de demostracion; cambiar SECRET_KEY en .env fuera de desarrollo.
"""
import argparse
import json
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
URL = "http://localhost:8000"
CREDENCIALES = [
    ("Administrador", "ADM001", "Admin123"),
    ("Alumno (María)", "A0512345", "Alumno123"),
    ("Alumno (Carlos)", "A0512980", "Alumno123"),
    ("Alumno (Laura)", "A0513001", "Alumno123"),
    ("Docente", "DOC001", "Docente123"),
    ("Catálogo", "CAT001", "Catalogo123"),
    ("Compras", "COM001", "Compras123"),
    ("Bibliotecario", "BIB001", "Biblioteca123"),
    ("Colaborador", "COL001", "Colabora123"),
]


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


def correr(args, **kw):
    """Ejecuta un comando con cwd en la raiz del proyecto.

    Args:
        args: lista de argumentos del comando.
        **kw: opciones de `subprocess.run`.

    Returns:
        subprocess.CompletedProcess.
    """
    return subprocess.run(args, cwd=RAIZ, **kw)


def verificar_docker():
    """Comprueba que docker, el plugin compose v2 y el demonio esten disponibles.

    Raises:
        SystemExit: con un mensaje orientado al usuario si falta alguno (via `salir`).
    """
    if not shutil.which("docker"):
        salir("No se encontró 'docker'. Instala Docker Desktop o Docker Engine: https://docs.docker.com/get-docker/")
    if correr(["docker", "compose", "version"], capture_output=True).returncode != 0:
        salir("No está disponible 'docker compose' (plugin Compose v2). Actualiza Docker.")
    if correr(["docker", "info"], capture_output=True).returncode != 0:
        salir("El demonio de Docker no responde. Abre Docker Desktop (o inicia el servicio) e inténtalo de nuevo.")


def preparar_env():
    """Crea `.env` copiando `.env.example` si aun no existe.

    Raises:
        SystemExit: si no existen ni `.env` ni `.env.example`.
    """
    env, ejemplo = RAIZ / ".env", RAIZ / ".env.example"
    if not env.exists():
        if not ejemplo.exists():
            salir("No existe .env ni .env.example.")
        shutil.copyfile(ejemplo, env)
        print("Se creó .env a partir de .env.example (cambia SECRET_KEY para producción).")


def salud_ok():
    """Consulta GET /api/health.

    Returns:
        True si responde JSON con `ok: true`; False ante cualquier error de red o respuesta distinta.
    """
    try:
        with urllib.request.urlopen(f"{URL}/api/health", timeout=3) as r:
            return json.load(r).get("ok") is True
    except Exception:
        return False


def esperar_salud(timeout=90):
    """Sondea /api/health cada 2 s hasta que responda o venza el plazo.

    Args:
        timeout: segundos maximos de espera.

    Raises:
        SystemExit: si la API no responde dentro de `timeout`.
    """
    print(f"Esperando a que la API responda en {URL}/api/health ", end="", flush=True)
    fin = time.time() + timeout
    while time.time() < fin:
        if salud_ok():
            print(" listo.")
            return
        print(".", end="", flush=True)
        time.sleep(2)
    print()
    salir(f"La API no respondió en {timeout} s. Revisa: docker compose logs web")


def main():
    """Punto de entrada: interpreta las opciones y levanta (o detiene con --down) el stack.

    Returns:
        None. Termina con `sys.exit` ante errores (ver codigos de salida en el docstring del modulo).
    """
    ap = argparse.ArgumentParser(description="Levanta LibriGest con Docker Compose.")
    ap.add_argument("--no-build", action="store_true", help="no reconstruir la imagen")
    ap.add_argument("--logs", action="store_true", help="seguir los logs después de levantar")
    ap.add_argument("--down", action="store_true", help="detener y eliminar los contenedores")
    a = ap.parse_args()

    verificar_docker()
    if a.down:
        r = correr(["docker", "compose", "down"])
        if r.returncode:
            salir("No se pudieron detener los contenedores.", r.returncode)
        print("Contenedores detenidos (los datos siguen en el volumen pgdata).")
        return
    preparar_env()
    cmd = ["docker", "compose", "up", "-d"] + ([] if a.no_build else ["--build"])
    print("Ejecutando:", " ".join(cmd))
    r = correr(cmd)
    if r.returncode:
        salir("Falló 'docker compose up'.", r.returncode)
    esperar_salud()
    print(f"\nLibriGest está en: {URL}\n\nCuentas de demostración:")
    for rol, mat, pw in CREDENCIALES:
        print(f"  {rol:<16} matrícula {mat:<9} contraseña {pw}")
    print("\nOtros scripts:\n"
          "  python scripts/recrear_db.py -y        reinicia la base con el esquema y los datos demo\n"
          "  python scripts/respaldo.py             respaldo de la base en backups/ (RNF-02)\n"
          "  python scripts/restaurar.py <archivo>  restaura un respaldo\n"
          "  python scripts/medir_rendimiento.py    mide el tiempo de respuesta (p95 <= 3 s)")
    if a.logs:
        print("\nSiguiendo logs (Ctrl+C para salir)...")
        try:
            correr(["docker", "compose", "logs", "-f", "web"])
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
