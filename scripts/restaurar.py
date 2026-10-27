#!/usr/bin/env python3
"""Restauracion de un respaldo de LibriGest (RNF-02, D-14).

Uso: python3 scripts/restaurar.py <archivo.dump> [--db librigest] [-y] [--verificar]

Sin --verificar: pide confirmacion [s/N] (omitir con -y) y restaura SOBRE --db con
pg_restore --clean --if-exists (reemplaza los datos actuales).
Con --verificar: restaura en una BD temporal, compara filas por tabla contra el .conteos del respaldo
(o contra --db si no existe), elimina la BD temporal y devuelve 0 solo si todo coincide. No toca --db.
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path

import _pg


def _restaurar(archivo, usuario, db):
    with open(archivo, "rb") as f:
        r = _pg.compose("exec", "-T", "db", "pg_restore", "-U", usuario, "-d", db, "--clean", "--if-exists",
                        "--no-owner", stdin=f, capture_output=True)
    # pg_restore devuelve != 0 con advertencias; solo importa si quedaron tablas.
    if r.returncode != 0:
        print(r.stderr.decode(errors="replace").strip(), file=sys.stderr)
    return r.returncode


def _esperados(archivo, usuario, db):
    conteos = archivo.with_suffix(".conteos")
    if conteos.exists():
        pares = (l.partition("=") for l in conteos.read_text(encoding="utf-8").splitlines() if l)
        return {k: int(v) for k, _, v in pares}, f"respaldo ({conteos.name})"
    return _pg.conteos(usuario, db), f"BD actual '{db}'"


def verificar(archivo, usuario, db):
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
    cfg = _pg.config()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("archivo", help="archivo .dump generado por respaldo.py")
    ap.add_argument("--db", default=cfg["db"], help=f"BD destino / de referencia (por defecto {cfg['db']})")
    ap.add_argument("--usuario", default=cfg["usuario"])
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
