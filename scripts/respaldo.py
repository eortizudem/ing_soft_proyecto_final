#!/usr/bin/env python3
"""Respaldo de la base de datos de LibriGest (RNF-02, D-14).

Uso: python3 scripts/respaldo.py [--salida backups/] [--db librigest]

Genera <salida>/librigest_YYYYmmdd_HHMMSS.dump (pg_dump -Fc dentro del contenedor db) y un archivo
.conteos con las filas por tabla en ese momento (lo usa `restaurar.py --verificar`).
RPO 24 h: programar este script cada dia (ver docs/operacion.md).
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path

import _pg


def main(argv=None):
    cfg = _pg.config()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--salida", default="backups", help="directorio de destino (por defecto backups/)")
    ap.add_argument("--db", default=cfg["db"], help=f"base a respaldar (por defecto {cfg['db']})")
    ap.add_argument("--usuario", default=cfg["usuario"])
    args = ap.parse_args(argv)

    _pg.verificar_docker()
    destino = Path(args.salida)
    if not destino.is_absolute():
        destino = _pg.RAIZ / destino
    destino.mkdir(parents=True, exist_ok=True)
    sello = datetime.now().strftime("%Y%m%d_%H%M%S")
    archivo = destino / f"{args.db}_{sello}.dump"
    parcial = archivo.with_suffix(".dump.part")

    with open(parcial, "wb") as f:
        r = _pg.compose("exec", "-T", "db", "pg_dump", "-U", args.usuario, "-Fc", args.db,
                        stdout=f, stderr=_pg.subprocess.PIPE)
    if r.returncode != 0 or parcial.stat().st_size == 0:
        parcial.unlink(missing_ok=True)
        _pg.salir(f"pg_dump fallo: {r.stderr.decode(errors='replace').strip()}")
    parcial.replace(archivo)
    cuentas = _pg.conteos(args.usuario, args.db)
    archivo.with_suffix(".conteos").write_text("".join(f"{t}={n}\n" for t, n in cuentas.items()), encoding="utf-8")
    print(f"Respaldo creado: {archivo} ({archivo.stat().st_size / 1024:.1f} KiB, {len(cuentas)} tablas, "
          f"{sum(cuentas.values())} filas)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
