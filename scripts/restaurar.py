#!/usr/bin/env python3
"""Restauracion de un respaldo de LibriGest (RNF-02, D-14).

Uso:
  python3 scripts/restaurar.py backups/librigest_AAAAmmdd_HHMMSS.dump              # pide confirmacion [s/N]
  python3 scripts/restaurar.py <archivo.dump> -y                                   # sin confirmacion (--yes)
  python3 scripts/restaurar.py <archivo.dump> --db otra_bd                         # BD destino / de referencia
  python3 scripts/restaurar.py <archivo.dump> --usuario postgres                   # rol de PostgreSQL
  python3 scripts/restaurar.py <archivo.dump> --verificar                          # prueba no destructiva

Sin --verificar: pide confirmacion [s/N] (omitir con -y) y restaura SOBRE --db con
pg_restore --clean --if-exists (reemplaza los datos actuales).
Con --verificar: restaura en una BD temporal, compara filas por tabla contra el .conteos del respaldo
(o contra --db si no existe), elimina la BD temporal y devuelve 0 solo si todo coincide. No toca --db.

Codigos de salida: 0 restauracion o verificacion correcta; 1 cancelado, conteos distintos, archivo inexistente,
servicio db caido o error de psql/pg_restore.

SEGURIDAD: restaurar sin --verificar REEMPLAZA los datos actuales de --db (pg_restore --clean --if-exists);
hacer antes un respaldo con respaldo.py. Sin -y exige responder s/si/y/yes.
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path

import _pg


def _restaurar(archivo, usuario, db):
    """Ejecuta `pg_restore --clean --if-exists --no-owner` en el contenedor db leyendo el .dump por stdin.

    Args:
        archivo: Path del .dump (formato custom de pg_dump -Fc).
        usuario: rol de PostgreSQL.
        db: base destino (se reemplazan sus objetos).

    Returns:
        Codigo de salida de pg_restore (puede ser != 0 solo por advertencias; su stderr se imprime).
    """
    with open(archivo, "rb") as f:
        r = _pg.compose("exec", "-T", "db", "pg_restore", "-U", usuario, "-d", db, "--clean", "--if-exists",
                        "--no-owner", stdin=f, capture_output=True)
    # pg_restore devuelve != 0 con advertencias; solo importa si quedaron tablas.
    if r.returncode != 0:
        print(r.stderr.decode(errors="replace").strip(), file=sys.stderr)
    return r.returncode


def _esperados(archivo, usuario, db):
    """Obtiene los conteos de referencia para la verificacion.

    Args:
        archivo: Path del .dump; se busca `<archivo>.conteos` junto a el.
        usuario: rol de PostgreSQL.
        db: base de referencia si no existe el archivo .conteos.

    Returns:
        Tupla (dict {tabla: filas}, descripcion del origen para el reporte).
    """
    conteos = archivo.with_suffix(".conteos")
    if conteos.exists():
        pares = (l.partition("=") for l in conteos.read_text(encoding="utf-8").splitlines() if l)
        return {k: int(v) for k, _, v in pares}, f"respaldo ({conteos.name})"
    return _pg.conteos(usuario, db), f"BD actual '{db}'"


def verificar(archivo, usuario, db):
    """Restaura el respaldo en una BD temporal `verif_<fecha>` y compara filas por tabla.

    La BD temporal siempre se elimina (bloque finally); `db` no se modifica.

    Args:
        archivo: Path del .dump.
        usuario: rol de PostgreSQL.
        db: base de referencia (si no hay .conteos).

    Returns:
        0 si todos los conteos coinciden; 1 si hay diferencias o no se restauro ninguna tabla.
    """
    temporal = "verif_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    esperados, origen = _esperados(archivo, usuario, db)
    _pg.psql(usuario, temporal, f'CREATE DATABASE "{temporal}"')
    try:
        _restaurar(archivo, usuario, temporal)
        obtenidos = _pg.conteos(usuario, temporal)
    finally:
        _pg.psql(usuario, temporal, f'DROP DATABASE IF EXISTS "{temporal}"')
    malas = [t for t in sorted(set(esperados) | set(obtenidos)) if esperados.get(t) != obtenidos.get(t)]
    print(f"Verificacion contra {origen}: {len(obtenidos)} tablas restauradas en BD temporal (eliminada).")
    for t in sorted(obtenidos):
        marca = "  " if t not in malas else "!!"
        print(f"{marca} {t:<24} esperado={esperados.get(t, '-'):<6} restaurado={obtenidos[t]}")
    if not obtenidos or malas:
        print(f"VERIFICACION FALLIDA ({len(malas)} tabla(s) con diferencias).", file=sys.stderr)
        return 1
    print("VERIFICACION CORRECTA: los conteos coinciden.")
    return 0


def main(argv=None):
    """Restaura un respaldo sobre `--db` o lo verifica con `--verificar`.

    Args:
        argv: lista de argumentos (None usa sys.argv); util para pruebas.

    Returns:
        0 en exito; 1 si el usuario cancela o la verificacion falla.

    Raises:
        SystemExit: si el archivo no existe, el servicio db no esta activo o la restauracion no deja tablas.
    """
    cfg = _pg.config()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("archivo", help="archivo .dump generado por respaldo.py")
    ap.add_argument("--db", default=cfg["db"], help=f"BD destino / de referencia (por defecto {cfg['db']})")
    ap.add_argument("--usuario", default=cfg["usuario"], help=f"rol de PostgreSQL (por defecto {cfg['usuario']})")
    ap.add_argument("-y", "--yes", action="store_true", help="no pedir confirmacion")
    ap.add_argument("--verificar", action="store_true", help="restaurar en una BD temporal y comparar conteos")
    args = ap.parse_args(argv)

    archivo = Path(args.archivo)
    if not archivo.is_file():
        _pg.salir(f"No existe el archivo: {archivo}")
    _pg.verificar_docker()
    if args.verificar:
        return verificar(archivo, args.usuario, args.db)
    if not args.yes:
        resp = input(f"Esto REEMPLAZARA los datos de la base '{args.db}' con {archivo.name}. ¿Continuar? [s/N] ")
        if resp.strip().lower() not in ("s", "si", "sí", "y", "yes"):
            print("Cancelado.")
            return 1
    codigo = _restaurar(archivo, args.usuario, args.db)
    if not _pg.conteos(args.usuario, args.db):
        _pg.salir("La restauracion no dejo tablas en la base.")
    print(f"Restauracion completada en '{args.db}'" + (" (con advertencias de pg_restore)." if codigo else "."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
