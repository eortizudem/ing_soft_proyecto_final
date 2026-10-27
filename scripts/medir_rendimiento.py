#!/usr/bin/env python3
"""Mide el tiempo de respuesta de los endpoints criticos (RNF-03/05/11/13, D-15). Solo biblioteca estandar.

Uso: python3 scripts/medir_rendimiento.py [--url http://localhost:8000] [-n 20] [-c 20] [--limite 3.0]
                                          [--usuario ADM001 --clave Admin123] [--escritura [--db librigest]]

Inicia sesion, llama N veces a cada endpoint (una a la vez y luego -c solicitudes simultaneas, D-15) y muestra p50 / p95 / max en segundos.
Sale con codigo 1 si el p95 de algun endpoint supera --limite (3 s por defecto) o si hay errores 5xx;
los endpoints que responden 404 (modulo no instalado) se omiten con aviso.

--url apunta a cualquier servidor (p. ej. un contenedor web sobre la BD de volumen, ver cargar_datos_volumen.py).
--escritura agrega los flujos de escritura: crear prestamo, renovar, devolver y registrar pago (N iteraciones,
en serie). Crea su propio usuario (ZPERF01) y libro (ZPERF01) por la API y, al terminar, borra todo lo que
generaron con SQL en la BD `--db` (por defecto la de POSTGRES_DB; requiere docker compose con el servicio db).
"""
import argparse
import http.cookiejar
import json
import math
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _pg  # noqa: E402

# (nombre, metodo, ruta, cuerpo JSON). Cubre catalogo, usuarios, circulacion, asistente y reportes.
ENDPOINTS = [
    ("libros", "GET", "/api/libros", None),
    ("libros?q=", "GET", "/api/libros?q=a", None),
    ("usuarios", "GET", "/api/usuarios", None),
    ("prestamos", "GET", "/api/prestamos", None),
    ("adeudos", "GET", "/api/adeudos", None),
    ("espera", "GET", "/api/espera", None),
    ("compras", "GET", "/api/compras", None),
    ("notificaciones", "GET", "/api/notificaciones", None),
    ("asistente/mensajes", "POST", "/api/asistente/mensajes", {"texto": "horarios de la biblioteca", "canal": "web"}),
    ("reportes/catalogo_activo", "GET", "/api/reportes/catalogo_activo", None),
    ("reportes/con_adeudos", "GET", "/api/reportes/con_adeudos", None),
    ("reportes/prestamos", "GET", "/api/reportes/prestamos", None),
    ("reportes/existencia", "GET", "/api/reportes/inventario_estante", None),
    ("reportes/vencidos", "GET", "/api/reportes/prestamos_vencidos", None),
    ("reportes/indicadores", "GET", "/api/reportes/indicadores", None),
    ("reportes/errores", "GET", "/api/reportes/errores", None),
    ("asistente/consultas", "GET", "/api/asistente/consultas", None),
]


def percentil(valores, p):
    """Percentil por rango mas cercano (valores no vacios)."""
    orden = sorted(valores)
    return orden[max(0, math.ceil(p / 100 * len(orden)) - 1)]


class Cliente:
    def __init__(self, base):
        self.base = base.rstrip("/")
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def pedir(self, metodo, ruta, cuerpo=None):
        """-> (status, segundos). Los errores HTTP no lanzan; los de red si."""
        status, seg, _ = self.pedir_json(metodo, ruta, cuerpo)
        return status, seg

    def pedir_json(self, metodo, ruta, cuerpo=None):
        """-> (status, segundos, cuerpo JSON o None)."""
        datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
        req = urllib.request.Request(self.base + ruta, data=datos, method=metodo,
                                     headers={"Content-Type": "application/json"} if datos else {})
        t0 = time.perf_counter()
        try:
            with self.opener.open(req, timeout=30) as r:
                crudo = r.read()
                status = r.status
        except urllib.error.HTTPError as e:
            crudo = e.read()
            status = e.code
        except (urllib.error.URLError, OSError):  # tiempo agotado / conexion rota: cuenta como fallo (HTTP 0)
            crudo, status = b"", 0
        seg = time.perf_counter() - t0
        try:
            return status, seg, json.loads(crudo)
        except ValueError:
            return status, seg, None


def _lote(cliente, metodo, ruta, cuerpo, n, concurrentes):
    """n peticiones: en serie (concurrentes=1) o en tandas simultaneas -> [(status, segundos)]."""
    if concurrentes <= 1:
        return [cliente.pedir(metodo, ruta, cuerpo) for _ in range(n)]
    with ThreadPoolExecutor(max_workers=concurrentes) as pool:
        return list(pool.map(lambda _: cliente.pedir(metodo, ruta, cuerpo), range(n)))


def _fila(nombre, tiempos, estados, limite):
    """Imprime p50/p95/max de un conjunto de tiempos; devuelve 1 si el p95 supera el limite o hubo errores."""
    p95 = percentil(tiempos, 95)
    malo = p95 > limite or any(s >= 400 for s in estados)
    extra = f" (HTTP {sorted(estados)})" if any(s >= 400 for s in estados) else ""
    print(f"{nombre:<28}{len(tiempos):>4}{percentil(tiempos, 50):>9.3f}{p95:>9.3f}{max(tiempos):>9.3f}  "
          f"{'FALLA' if malo else 'ok'}{extra}")
    return int(malo)


# ---- Flujos de escritura (--escritura) ----
MARCA = "ZPERF01"


def limpiar_escritura(db):
    """Borra el usuario y libro de medicion y todo lo que generaron (prestamos, adeudos, avisos, bitacora)."""
    cfg = _pg.config()
    _pg.psql(cfg["usuario"], db, f"""
      DELETE FROM adeudo WHERE id_prestamo IN (SELECT p.id_prestamo FROM prestamo p JOIN usuario u USING (id_usuario) WHERE u.matricula='{MARCA}');
      DELETE FROM renovacion WHERE id_prestamo IN (SELECT p.id_prestamo FROM prestamo p JOIN usuario u USING (id_usuario) WHERE u.matricula='{MARCA}');
      DELETE FROM prestamo WHERE id_usuario IN (SELECT id_usuario FROM usuario WHERE matricula='{MARCA}');
      DELETE FROM lista_espera WHERE id_usuario IN (SELECT id_usuario FROM usuario WHERE matricula='{MARCA}');
      DELETE FROM bitacora WHERE detalle LIKE '%{MARCA}%' OR id_usuario IN (SELECT id_usuario FROM usuario WHERE matricula='{MARCA}');
      DELETE FROM ejemplar WHERE id_libro IN (SELECT id_libro FROM libro WHERE clave='{MARCA}');
      DELETE FROM libro WHERE clave='{MARCA}';
      DELETE FROM ubicacion WHERE id_ubicacion NOT IN (SELECT id_ubicacion FROM libro) AND planta='Planta baja' AND pasillo='F' AND librero='12' AND nivel=9;
      DELETE FROM usuario WHERE matricula='{MARCA}';""", base=db)


def medir_escritura(cliente, n, limite, db):
    """Crear prestamo, renovar, devolver y registrar pago (en serie, n iteraciones). -> numero de fallos."""
    print(f"\n== Flujos de escritura: {n} iteraciones en serie ==")
    try:
        limpiar_escritura(db)
    except SystemExit:
        print("ERROR: no se pudo limpiar con docker compose; sin acceso a la BD no se miden escrituras.", file=sys.stderr)
        return 1
    st, _, r = cliente.pedir_json("POST", "/api/usuarios", {
        "matricula": MARCA, "nombre_completo": "Usuario de medicion", "correo": "zperf01@medicion.test", "rol": "alumno",
        "estado": "activo", "fuente_validacion": "manual", "password": "Prueba123"})
    st2, _, r2 = cliente.pedir_json("POST", "/api/libros", {
        "clave": MARCA, "titulo": "Libro de medicion", "autor": "Medicion", "editorial": "Medicion", "tema": "Pruebas",
        "anio_publicacion": 2020, "tipo_uso": "prestamo_externo", "clasificacion": "000 PRU", "sinopsis": "Medicion",
        "precio_referencia": 100, "ejemplares": 1, "planta": "Planta baja", "pasillo": "F", "librero": 12, "nivel": 9,
        "estado": "activo"})
    if st != 201 or st2 != 201:
        print(f"ERROR: no se pudo preparar la medicion (usuario HTTP {st}: {r}; libro HTTP {st2}: {r2})", file=sys.stderr)
        limpiar_escritura(db)
        return 1
    tiempos = {k: [] for k in ("prestamo crear", "prestamo renovar", "prestamo devolver", "adeudo pago")}
    estados = {k: set() for k in tiempos}
    def paso(nombre, metodo, ruta, cuerpo=None):
        status, seg, datos = cliente.pedir_json(metodo, ruta, cuerpo)
        tiempos[nombre].append(seg)
        estados[nombre].add(status)
        return status, datos
    try:
        for i in range(n):
            st, d = paso("prestamo crear", "POST", "/api/prestamos", {"matricula": MARCA, "clave": MARCA})
            if st != 201:
                break
            idp = d["prestamo"]["id_prestamo"]
            paso("prestamo renovar", "POST", f"/api/prestamos/{idp}/renovar")
            paso("prestamo devolver", "POST", f"/api/prestamos/{idp}/devolver")
            st, d = paso("prestamo crear", "POST", "/api/prestamos", {"matricula": MARCA, "clave": MARCA})
            if st != 201:
                break
            idp = d["prestamo"]["id_prestamo"]
            st, _, danio = cliente.pedir_json("POST", "/api/adeudos/danio", {"id_prestamo": idp, "porcentaje": 10})
            if st != 201:
                break
            paso("adeudo pago", "POST", f"/api/adeudos/{danio['adeudo']['id_adeudo']}/pago", {"referencia_tesoreria": f"PERF-{i}"})
    finally:
        limpiar_escritura(db)
    print(f"{'flujo':<28}{'n':>4}{'p50':>9}{'p95':>9}{'max':>9}  estado")
    return sum(_fila(k, v, estados[k], limite) for k, v in tiempos.items() if v)


def medir(cliente, n, limite, concurrentes=1):
    modo = f"{concurrentes} concurrentes" if concurrentes > 1 else "una a la vez"
    print(f"\n== {n} solicitudes por endpoint, {modo} ==")
    print(f"{'endpoint':<28}{'n':>4}{'p50':>9}{'p95':>9}{'max':>9}  estado")
    fallos = 0
    for nombre, metodo, ruta, cuerpo in ENDPOINTS:
        tiempos, estados = [], set()
        for status, seg in _lote(cliente, metodo, ruta, cuerpo, n, concurrentes):
            estados.add(status)
            tiempos.append(seg)
        if estados <= {404, 403}:
            print(f"{nombre:<28}{'-':>4}{'-':>9}{'-':>9}{'-':>9}  OMITIDO (HTTP {min(estados)})")
            continue
        fallos += _fila(nombre, tiempos, estados, limite)
    return fallos


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("-n", type=int, default=20, help="repeticiones por endpoint (20)")
    ap.add_argument("-c", "--concurrentes", type=int, default=20,
                    help="solicitudes simultaneas de la segunda pasada (20; 0 la omite)")
    ap.add_argument("--limite", type=float, default=3.0, help="p95 maximo en segundos (3.0)")
    ap.add_argument("--usuario", default="ADM001")
    ap.add_argument("--clave", default="Admin123")
    ap.add_argument("--escritura", action="store_true", help="mide tambien crear prestamo, renovar, devolver y pagar")
    ap.add_argument("--db", default=None, help="BD donde limpiar los datos de --escritura (por defecto POSTGRES_DB)")
    args = ap.parse_args(argv)

    cliente = Cliente(args.url)
    try:
        status, seg = cliente.pedir("POST", "/api/login", {"matricula": args.usuario, "password": args.clave})
    except (urllib.error.URLError, OSError) as e:
        print(f"ERROR: no se pudo conectar a {args.url}: {e}", file=sys.stderr)
        return 2
    print(f"login: HTTP {status} en {seg:.3f} s")
    if status != 200:
        print("ERROR: no se pudo iniciar sesion.", file=sys.stderr)
        return 2
    fallos = medir(cliente, max(1, args.n), args.limite)
    if args.concurrentes > 1:
        fallos += medir(cliente, args.concurrentes, args.limite, args.concurrentes)
    if args.escritura:
        fallos += medir_escritura(cliente, max(1, args.n), args.limite, args.db or _pg.config()["db"])
    print(f"\nResultado: {'FALLA' if fallos else 'CORRECTO'} (limite p95 = {args.limite} s, {fallos} endpoint(s) fuera).")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
