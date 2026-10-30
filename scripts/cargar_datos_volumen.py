#!/usr/bin/env python3
"""Carga el dataset de volumen de D-15 (>= 5,000 usuarios, >= 10,000 ejemplares, >= 20,000 prestamos).

Uso:
  python3 scripts/cargar_datos_volumen.py [--db librigest_volumen] [--usuarios 5000] [--ejemplares 10000]
                                          [--prestamos 20000] [--yes]
  python3 scripts/cargar_datos_volumen.py --eliminar [--db librigest_volumen]

Por defecto crea (o recrea) la BD aparte `librigest_volumen` con db/*.sql y la semilla de usuarios, y le agrega
los datos sinteticos con SQL (generate_series) via psql en el contenedor `db`. Nunca toca la BD principal:
`--db librigest` solo se acepta con confirmacion escrita (o --yes) y solo AGREGA filas (usuarios V0000001..,
libros VL000001.., folios VS...), no borra nada. Solo biblioteca estandar; requiere el stack levantado (levantar.py).

Datos: libros de 4 ejemplares; ~15 % de los prestamos abiertos (activos y vencidos), el resto devueltos en los
ultimos 2 anios; adeudos de retraso (10 % pendientes), renovaciones, lista de espera (250 libros con todas sus copias prestadas), conversaciones del asistente
con mensajes (10 % con_bibliotecario), solicitudes de compra y bitacora (login y notificaciones). Todos los usuarios V0000001..
comparten la contrasena de ADM001 (para pruebas). Despues: ANALYZE y verificacion de conteos y consistencia.
Para medir: ver docs/operacion.md seccion 3 (contenedor web aparte en el puerto 8199).

Opciones: --db (BD destino, librigest_volumen), --usuarios / --ejemplares / --prestamos (cantidades minimas
objetivo; la carga es incremental y repetible), --eliminar (borra la BD de volumen y termina), -y/--yes.

Codigos de salida: 0 correcto; 1 error (nombre de BD invalido, docker/db caido, SQL fallido, cancelacion,
verificacion con conteos por debajo del minimo o discrepancias de inventario).

SEGURIDAD: con la BD por defecto (`librigest_volumen`) se DROPea y recrea sin confirmar. --eliminar hace DROP
DATABASE de la BD indicada (se niega con la principal). Cargar en la BD principal mezcla datos sinteticos con
los reales y exige escribir su nombre (o -y).
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _pg  # noqa: E402

# BD principal del proyecto: protegida contra --eliminar y contra cargas sin confirmacion.
PRINCIPAL = _pg.config()["db"]
# Nombres de BD aceptados (evita inyeccion en los DROP/CREATE DATABASE interpolados).
NOMBRE_VALIDO = re.compile(r"^[a-z_][a-z0-9_]{0,40}$")
COPIAS = 4  # ejemplares por libro sintetico


def preparar_bd(db, cfg):
    """Crea la BD `db` desde db/*.sql y la siembra (usuarios demo). Si existe, la recrea.

    La semilla (`python -m app.seed`) corre en un contenedor web temporal apuntando a `db`.

    Args:
        db: nombre de la BD a (re)crear (se elimina antes con DROP ... WITH (FORCE)).
        cfg: dict de `_pg.config()` (usuario y clave).

    Raises:
        SystemExit: si falla algun comando SQL o la semilla (via `_pg`).
    """
    usuario = cfg["usuario"]
    print(f"Creando BD {db} (se reemplaza si existe)...")
    _pg.psql(usuario, db, f'DROP DATABASE IF EXISTS "{db}" WITH (FORCE)')
    _pg.psql(usuario, db, f'CREATE DATABASE "{db}"')
    for archivo in sorted((_pg.RAIZ / "db").glob("*.sql")):
        _pg.psql_script(usuario, db, archivo.read_text(encoding="utf-8"))
        print(f"  aplicado db/{archivo.name}")
    url = f"postgresql://{usuario}:{cfg['clave']}@db:5432/{db}"
    print("Sembrando usuarios demo (python -m app.seed en un contenedor web temporal)...")
    r = _pg.compose("run", "--rm", "--no-deps", "-T", "-e", f"DATABASE_URL={url}", "web", "python", "-m", "app.seed",
                    capture_output=True, text=True)
    if r.returncode != 0:
        _pg.salir(f"La semilla fallo: {r.stderr.strip() or r.stdout.strip()}")


def script_carga(estado, usuarios, ejemplares, prestamos):
    """Genera el script SQL de la carga sintetica (una sola transaccion, con generate_series).

    Calcula cuantas filas faltan respecto a lo ya existente, de modo que repetir la carga no choque con claves.

    Args:
        estado: dict devuelto por `estado_previo` (conteos y maximos actuales).
        usuarios: total objetivo de usuarios.
        ejemplares: total objetivo de ejemplares (se redondea a multiplos de COPIAS).
        prestamos: total objetivo de prestamos (~15 % abiertos).

    Returns:
        Texto SQL con BEGIN ... COMMIT; ANALYZE.
    """
    n_usr = max(0, usuarios - estado["usuarios"])
    n_ej = max(0, ejemplares - estado["ejemplares"])
    n_lib = -(-n_ej // COPIAS)
    n_ej_nuevos = n_lib * COPIAS
    n_abiertos = min(n_ej_nuevos // 3, max(0, prestamos - estado["prestamos"]) * 15 // 100)
    n_hist = max(0, prestamos - estado["prestamos"] - n_abiertos)
    n_conv, n_comp, n_bit = 3000, 500, 20000
    n_libros_espera = min(250, n_lib)
    return f"""
BEGIN;
SELECT setseed(0.42);
-- Usuarios: 90 % alumnos, 10 % docentes; misma contrasena que ADM001.
INSERT INTO usuario(matricula, nombre_completo, correo, contrasena_hash, id_rol, estado, fuente_validacion)
SELECT 'V' || lpad(({estado['u_base']} + g)::text, 7, '0'), 'Usuario Volumen ' || ({estado['u_base']} + g),
       'vol' || ({estado['u_base']} + g) || '@volumen.ducky.edu.mx',
       (SELECT contrasena_hash FROM usuario WHERE matricula = 'ADM001'), r.id_rol, 'activo', 'servicios_escolares'
FROM generate_series(1, {n_usr}) g JOIN rol r ON r.nombre = CASE WHEN g % 10 = 0 THEN 'docente' ELSE 'alumno' END;

-- Libros (una ubicacion por libro) y ejemplares.
WITH ub AS (
  INSERT INTO ubicacion(planta, pasillo, librero, nivel)
  SELECT CASE WHEN g % 2 = 0 THEN 'Planta baja' ELSE 'Planta alta' END, chr(65 + (g / 2) % 6),
         lpad((1 + (g / 12) % 12)::text, 2, '0'), 1 + g % 5
  FROM generate_series(1, {n_lib}) g RETURNING id_ubicacion),
nu AS (SELECT id_ubicacion, row_number() OVER (ORDER BY id_ubicacion) AS rn FROM ub)
INSERT INTO libro(clave, titulo, autor, editorial, tema, anio_publicacion, tipo_uso, clasificacion, sinopsis,
                  precio_referencia, id_ubicacion, estado)
SELECT 'VL' || lpad(({estado['l_base']} + rn)::text, 6, '0'),
       'Libro de volumen ' || ({estado['l_base']} + rn) || ' ' || (ARRAY['Algoritmos','Calculo','Historia','Quimica',
         'Literatura','Fisica','Derecho','Economia'])[1 + rn % 8],
       'Autor ' || (rn % 800), 'Editorial ' || (rn % 40),
       (ARRAY['Programacion','Matematicas','Historia','Quimica','Literatura','Fisica','Derecho','Economia',
              'Biologia','Arte'])[1 + rn % 10],
       1980 + rn % 45, CASE WHEN rn % 25 = 0 THEN 'consulta_interna' ELSE 'prestamo_externo' END,
       '000 VOL', 'Sinopsis sintetica del libro ' || rn || ' para pruebas de volumen.', 100 + rn % 400, id_ubicacion, 'activo'
FROM nu;

INSERT INTO ejemplar(id_libro, numero_copia)
SELECT l.id_libro, c FROM libro l CROSS JOIN generate_series(1, {COPIAS}) c WHERE l.id_libro > {estado['libro_max']};

-- Prestamos abiertos (cada tercer ejemplar nuevo): vencidos si pasaron mas de 7 dias.
CREATE TEMP TABLE _ej AS
  SELECT id_ejemplar, row_number() OVER (ORDER BY id_ejemplar) AS rn FROM ejemplar WHERE id_ejemplar > {estado['ejemplar_max']};
CREATE TEMP TABLE _us AS
  SELECT id_usuario, id_rol, row_number() OVER (ORDER BY id_usuario) AS rn FROM usuario WHERE matricula ~ '^V[0-9]{{7}}$';
CREATE TEMP TABLE _pol AS SELECT DISTINCT ON (id_rol) id_rol, id_politica FROM politica_prestamo WHERE activa ORDER BY id_rol, vigente_desde DESC;

INSERT INTO prestamo(id_ejemplar, id_usuario, id_politica, fecha_prestamo, fecha_vencimiento, estado)
SELECT e.id_ejemplar, u.id_usuario, p.id_politica, t.fp, t.fp::date + 7,
       CASE WHEN t.fp::date + 7 < CURRENT_DATE THEN 'vencido' ELSE 'activo' END
FROM (SELECT k, now() - ((k * 13) % 20 + 1) * interval '1 day' AS fp FROM generate_series(1, {n_abiertos}) k) t
JOIN _ej e ON e.rn = (t.k - 1) * 3 + 1
JOIN _us u ON u.rn = (t.k * 7919) % (SELECT count(*) FROM _us) + 1
JOIN _pol p ON p.id_rol = u.id_rol;
UPDATE ejemplar SET estado = 'prestado'
 WHERE id_ejemplar IN (SELECT id_ejemplar FROM prestamo WHERE fecha_devolucion IS NULL AND id_prestamo > {estado['prestamo_max']});

-- Prestamos devueltos (historial de 2 anios); algunos con retraso.
INSERT INTO prestamo(id_ejemplar, id_usuario, id_politica, fecha_prestamo, fecha_vencimiento, fecha_devolucion, estado)
SELECT e.id_ejemplar, u.id_usuario, p.id_politica, t.fp, t.fp::date + 7, t.fp + ((t.k * 5) % 12 + 1) * interval '1 day', 'devuelto'
FROM (SELECT k, now() - ((k * 37) % 700 + 15) * interval '1 day' - ((k * 11) % 24) * interval '1 hour' AS fp
      FROM generate_series(1, {n_hist}) k) t
JOIN _ej e ON e.rn = (t.k * 104729) % (SELECT count(*) FROM _ej) + 1
JOIN _us u ON u.rn = (t.k * 31) % (SELECT count(*) FROM _us) + 1
JOIN _pol p ON p.id_rol = u.id_rol;

-- Renovaciones (cada 5.º prestamo abierto nuevo) y adeudos de retraso (10 % pendientes).
INSERT INTO renovacion(id_prestamo, fecha, nueva_fecha_vencimiento)
SELECT id_prestamo, fecha_prestamo + interval '3 day', fecha_vencimiento + 7 FROM prestamo
 WHERE id_prestamo > {estado['prestamo_max']} AND fecha_devolucion IS NULL AND id_prestamo % 5 = 0;
UPDATE prestamo SET fecha_vencimiento = fecha_vencimiento + 7, num_renovaciones = 1,
       estado = CASE WHEN fecha_vencimiento + 7 < CURRENT_DATE THEN 'vencido' ELSE 'activo' END
 WHERE id_prestamo > {estado['prestamo_max']} AND fecha_devolucion IS NULL AND id_prestamo % 5 = 0;
INSERT INTO adeudo(id_prestamo, tipo, dias_retraso, monto, estado, fecha_pago)
SELECT id_prestamo, 'retraso', fecha_devolucion::date - fecha_vencimiento, (fecha_devolucion::date - fecha_vencimiento) * 10,
       CASE WHEN id_prestamo % 10 = 0 THEN 'pendiente' ELSE 'pagado' END,
       CASE WHEN id_prestamo % 10 = 0 THEN NULL ELSE fecha_devolucion::date END
FROM prestamo WHERE id_prestamo > {estado['prestamo_max']} AND fecha_devolucion::date > fecha_vencimiento;

-- Lista de espera (D-19): en 250 libros se prestan todas las copias y esperan hasta 4 usuarios (FIFO).
CREATE TEMP TABLE _lw AS
  SELECT id_libro, row_number() OVER (ORDER BY id_libro) AS rn FROM libro WHERE id_libro > {estado['libro_max']} ORDER BY id_libro LIMIT {n_libros_espera};
INSERT INTO prestamo(id_ejemplar, id_usuario, id_politica, fecha_prestamo, fecha_vencimiento, estado)
SELECT e.id_ejemplar, u.id_usuario, p.id_politica, now() - interval '2 day', CURRENT_DATE + 5, 'activo'
FROM ejemplar e JOIN _lw w ON w.id_libro = e.id_libro
JOIN _us u ON u.rn = (e.id_ejemplar * 7) % (SELECT count(*) FROM _us) + 1
JOIN _pol p ON p.id_rol = u.id_rol
WHERE e.estado = 'disponible';
UPDATE ejemplar SET estado = 'prestado' WHERE estado = 'disponible' AND id_libro IN (SELECT id_libro FROM _lw);
INSERT INTO lista_espera(id_usuario, id_libro, fecha_solicitud, posicion, estado)
SELECT u.id_usuario, w.id_libro, now() - (w.rn % 30 + k) * interval '1 hour', k, 'en_espera'
FROM _lw w CROSS JOIN generate_series(1, 4) k
JOIN _us u ON u.rn = (w.rn * 4 + k + 2500) % (SELECT count(*) FROM _us) + 1
WHERE NOT EXISTS (SELECT 1 FROM prestamo p JOIN ejemplar x ON x.id_ejemplar = p.id_ejemplar
                  WHERE p.id_usuario = u.id_usuario AND x.id_libro = w.id_libro AND p.fecha_devolucion IS NULL);

-- Conversaciones del asistente: 2 mensajes c/u; 10 % con_bibliotecario (la mitad pendiente).
WITH c AS (
  INSERT INTO conversacion(id_usuario, canal, fecha_inicio, fecha_fin, resuelta, calificacion)
  SELECT u.id_usuario, CASE WHEN g % 4 = 0 THEN 'movil' ELSE 'web' END, now() - (g % 90) * interval '1 day',
         now() - (g % 90) * interval '1 day' + interval '3 minute', g % 3 <> 0 AND g % 10 <> 0, CASE WHEN g % 3 = 0 THEN 1 + g % 5 END
  FROM generate_series(1, {n_conv}) g JOIN _us u ON u.rn = (g * 17) % (SELECT count(*) FROM _us) + 1
  RETURNING id_conversacion, resuelta, fecha_inicio),
n AS (SELECT c.*, row_number() OVER (ORDER BY id_conversacion) AS rn FROM c)
INSERT INTO mensaje(id_conversacion, id_intencion, emisor, texto, fecha)
SELECT n.id_conversacion, CASE WHEN s.e = 'asistente' THEN i.id_intencion END, s.e,
       CASE WHEN s.e = 'usuario' THEN 'Pregunta de prueba ' || n.rn ELSE 'Respuesta de prueba ' || n.rn END, n.fecha_inicio
FROM n CROSS JOIN (VALUES ('usuario'), ('asistente')) s(e)
JOIN intencion i ON i.nombre = CASE WHEN n.rn % 10 = 0 THEN 'pasar_a_bibliotecario' ELSE 'horarios' END;

-- Solicitudes de compra con 2 lineas.
WITH s AS (
  INSERT INTO solicitud_compra(folio, id_usuario, justificacion, fecha, total_estimado, estado)
  SELECT 'VS' || lpad(({estado['s_base']} + g)::text, 7, '0'), (SELECT id_usuario FROM usuario WHERE matricula = 'COM001'),
         'Compra de volumen ' || g, CURRENT_DATE - g % 300, 150, (ARRAY['pendiente','enviada','recibida','cancelada'])[1 + g % 4]
  FROM generate_series(1, {n_comp}) g RETURNING id_solicitud)
INSERT INTO detalle_solicitud(id_solicitud, descripcion, cantidad, precio_unitario)
SELECT id_solicitud, 'Titulo solicitado ' || id_solicitud || '-' || l, 5, 15 FROM s CROSS JOIN generate_series(1, 2) l;

-- Bitacora: inicios de sesion y notificaciones simuladas.
INSERT INTO bitacora(id_usuario, accion, detalle, fecha)
SELECT u.id_usuario, CASE WHEN g % 3 = 0 THEN 'notif_email' ELSE 'login' END,
       CASE WHEN g % 3 = 0 THEN 'vol' || g || '@volumen.ducky.edu.mx|Aviso ' || g || ': texto de prueba' ELSE 'Inicio de sesion ' || g END,
       now() - (g % 120) * interval '1 hour'
FROM generate_series(1, {n_bit}) g JOIN _us u ON u.rn = (g * 13) % (SELECT count(*) FROM _us) + 1;
COMMIT;
ANALYZE;
"""


def estado_previo(db):
    """Consulta conteos y maximos actuales de la BD para cargar sin chocar con datos previos.

    Args:
        db: base de datos a consultar.

    Returns:
        dict con conteos (usuarios, ejemplares, prestamos) y maximos/bases de numeracion (u_base, l_base,
        s_base, libro_max, ejemplar_max, prestamo_max).
    """
    cfg = _pg.config()

    def uno(sql):
        return int(_pg.psql(cfg["usuario"], db, sql, base=db).strip() or 0)

    return {
        "usuarios": uno("SELECT count(*) FROM usuario"), "ejemplares": uno("SELECT count(*) FROM ejemplar"),
        "prestamos": uno("SELECT count(*) FROM prestamo"),
        "u_base": uno("SELECT COALESCE(max(substr(matricula, 2)::int), 0) FROM usuario WHERE matricula ~ '^V[0-9]{7}$'"),
        "l_base": uno("SELECT COALESCE(max(substr(clave, 3)::int), 0) FROM libro WHERE clave ~ '^VL[0-9]{6}$'"),
        "s_base": uno("SELECT COALESCE(max(substr(folio, 3)::int), 0) FROM solicitud_compra WHERE folio ~ '^VS[0-9]{7}$'"),
        "libro_max": uno("SELECT COALESCE(max(id_libro), 0) FROM libro"),
        "ejemplar_max": uno("SELECT COALESCE(max(id_ejemplar), 0) FROM ejemplar"),
        "prestamo_max": uno("SELECT COALESCE(max(id_prestamo), 0) FROM prestamo"),
    }


def verificar(db, minimos):
    """Imprime filas por tabla y comprueba minimos y consistencia del inventario.

    Consistencia: ningun ejemplar `prestado` sin prestamo abierto, ni `disponible` con prestamo abierto.

    Args:
        db: base de datos a verificar.
        minimos: dict {tabla: filas minimas esperadas}.

    Raises:
        SystemExit: si alguna tabla queda por debajo del minimo o hay discrepancias (via `_pg.salir`).
    """
    cfg = _pg.config()
    c = _pg.conteos(cfg["usuario"], db)
    print("\nFilas por tabla (BD %s):" % db)
    for tabla in ("usuario", "libro", "ejemplar", "prestamo", "adeudo", "renovacion", "lista_espera", "conversacion",
                  "mensaje", "solicitud_compra", "bitacora"):
        print(f"  {tabla:<20}{c.get(tabla, 0):>8}")
    huecos = [f"{t} {c[t]} < {m}" for t, m in minimos.items() if c[t] < m]
    incons = int(_pg.psql(cfg["usuario"], db, """SELECT
      (SELECT count(*) FROM ejemplar e WHERE e.estado='prestado' AND NOT EXISTS (SELECT 1 FROM prestamo p WHERE p.id_ejemplar=e.id_ejemplar AND p.fecha_devolucion IS NULL))
    + (SELECT count(*) FROM ejemplar e WHERE e.estado='disponible' AND EXISTS (SELECT 1 FROM prestamo p WHERE p.id_ejemplar=e.id_ejemplar AND p.fecha_devolucion IS NULL))""",
                          base=db).strip())
    print(f"  discrepancias de inventario: {incons}")
    if huecos or incons:
        _pg.salir("Verificacion fallida: " + "; ".join(huecos + ([f'{incons} discrepancias'] if incons else [])))
    print("Dataset de volumen listo.")


def main(argv=None):
    """Punto de entrada: valida opciones, prepara la BD (o la elimina) y carga el dataset de volumen.

    Args:
        argv: lista de argumentos (None usa sys.argv); util para pruebas.

    Returns:
        0 en exito.

    Raises:
        SystemExit: ante nombre de BD invalido, intento de eliminar la principal, falta de confirmacion o
            cualquier fallo de docker/SQL/verificacion.
    """
    global ARGS_DB
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="librigest_volumen", help="BD destino (librigest_volumen)")
    ap.add_argument("--usuarios", type=int, default=5000, help="usuarios totales objetivo (5000)")
    ap.add_argument("--ejemplares", type=int, default=10000, help="ejemplares totales objetivo (10000)")
    ap.add_argument("--prestamos", type=int, default=20000, help="prestamos totales objetivo (20000)")
    ap.add_argument("--eliminar", action="store_true", help="elimina la BD de volumen y termina")
    ap.add_argument("-y", "--yes", action="store_true", help="no pedir confirmacion (obligatorio sin terminal)")
    a = ap.parse_args(argv)
    ARGS_DB = a.db

    if not NOMBRE_VALIDO.match(a.db):
        _pg.salir("Nombre de BD no valido (minusculas, digitos y _).")
    cfg = _pg.config()
    _pg.verificar_docker()
    principal = a.db == PRINCIPAL
    if a.eliminar:
        if principal:
            _pg.salir(f"No se elimina la BD principal ({PRINCIPAL}).")
        _pg.psql(cfg["usuario"], a.db, f'DROP DATABASE IF EXISTS "{a.db}" WITH (FORCE)')
        print(f"BD {a.db} eliminada.")
        return 0
    if principal:
        print(f"ATENCION: {a.db} es la BD principal. Se AGREGARAN datos sinteticos (no se borra nada) y se mezclaran con los reales.")
        if not a.yes and (not sys.stdin.isatty() or input(f"Escribe el nombre de la BD ({a.db}) para confirmar: ").strip() != a.db):
            _pg.salir("Cancelado: sin confirmacion no se carga en la BD principal.")
    else:
        preparar_bd(a.db, cfg)
    estado = estado_previo(a.db)
    print(f"Cargando en {a.db} (usuarios {estado['usuarios']}, ejemplares {estado['ejemplares']}, prestamos {estado['prestamos']} previos)...")
    _pg.psql_script(cfg["usuario"], a.db, script_carga(estado, a.usuarios, a.ejemplares, a.prestamos))
    verificar(a.db, {"usuario": a.usuarios, "ejemplar": a.ejemplares, "prestamo": a.prestamos})
    return 0


ARGS_DB = None

if __name__ == "__main__":
    sys.exit(main())
