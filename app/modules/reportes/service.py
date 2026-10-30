"""Capa servicio de reportes: reglas de negocio y armado de reportes tabulares.

Cada reporte devuelve `columnas` y `filas`; el formato (pantalla/pdf/impresión) solo se registra y lo renderiza
el cliente. Cada generación queda en `reporte_generado` y en bitácora.

Tipos de reporte (`TIPOS`), permisos y filtros:
  - catalogo_completo / catalogo_activo: Clave, Título, Autor, Tema, Ejemplares, Disponibles, Estado. Sin filtros. Permiso: `reportes`.
  - usuarios: Matrícula, Nombre, Correo, Perfil, Estado. Permisos: `reportes` + `usuarios`.
  - con_adeudos (RF-28): Matrícula, Nombre, Correo, Libros vencidos, Días de retraso, Adeudo pendiente (MXN), Suspendido.
    Filtro: incluir_docentes. Permisos: `reportes` + `prestamos`.
  - inventario_estante (RF-16): Clave, Título, Ubicación, Ejemplares, Disponibles, Prestados, Bajas, Conteo físico.
    Filtros: planta, pasillo, librero, tema. Permiso: `reportes`.
  - prestamos_vencidos: Matrícula, Usuario, Libro, Copia, Préstamo, Vencimiento, Días de retraso, Multa estimada (MXN).
    Sin filtros. Permisos: `reportes` + `prestamos`.
  - prestamos: Folio, Matrícula, Usuario, Libro, Copia, Préstamo, Vencimiento, Devolución, Renovaciones, Estado.
    Filtros: desde, hasta (fecha de préstamo). Permisos: `reportes` + `prestamos`.
  - indicadores (PS-MET-02/03, CTX-03): Área, Indicador, Valor, Detalle. Filtros: desde, hasta. Permiso: `reportes`.
  - errores (PS-S3-06): Fecha, Origen, Usuario, Detalle. Filtros: desde, hasta. Permiso: `reportes`.
"""

from datetime import date

from app.core import circulacion, notificaciones
from app.core import errores as errores_log
from app.core.auth import require_permission
from app.core.bitacora import log
from app.core.errors import ApiError
from app.core.serializers import texto_ubicacion
from app.core.validators import Date, Enum, Str, validate

from . import model

TIPOS = ("catalogo_completo", "catalogo_activo", "usuarios", "con_adeudos", "inventario_estante",
         "prestamos_vencidos", "prestamos", "indicadores", "errores")
# Permiso adicional a `reportes` por tipo: datos personales / de circulacion (privacidad).
PERMISO_EXTRA = {"usuarios": "usuarios", "con_adeudos": "prestamos", "prestamos_vencidos": "prestamos",
                 "prestamos": "prestamos"}
FORMATOS = ("pantalla", "pdf", "impresion")
SCHEMA = {"tipo": Enum(TIPOS, "Tipo de reporte no válido.", status=404),
          "formato": Enum(FORMATOS, "Formato de reporte no válido.")}
FILTROS = {"planta": Str("planta", max=20, required=False), "pasillo": Str("pasillo", max=1, upper=True, required=False),
           "librero": Str("librero", max=2, required=False), "tema": Str("tema", max=60, required=False),
           "desde": Date(msg="La fecha inicial no es válida (AAAA-MM-DD).", required=False),
           "hasta": Date(msg="La fecha final no es válida (AAAA-MM-DD).", required=False)}
ROLES_CON_ADEUDOS = ("alumno",)


def _dia(v):
    """Formatea una fecha como ISO (AAAA-MM-DD) o cadena vacía.

    Args:
        v (date | None): Fecha.

    Returns:
        str: Fecha ISO o ''.
    """
    return v.isoformat() if v else ""


def con_adeudos(incluir_docentes=False):
    """RF-28/D-09: usuarios con préstamo vencido (D-24) o adeudo pendiente. Días de retraso = hábiles (D-03).

    Args:
        incluir_docentes (bool): Si es True, incluye también docentes (por defecto solo alumnos).

    Returns:
        list[dict]: Usuarios con vencidos, adeudos, monto y `dias` de retraso acumulados.
    """
    dias = {}
    for p in model.prestamos_vencidos():
        dias[p["id_usuario"]] = dias.get(p["id_usuario"], 0) + circulacion.dias_retraso(p["fecha_vencimiento"], date.today())
    roles = ROLES_CON_ADEUDOS + (("docente",) if incluir_docentes else ())
    return [{**r, "dias": dias.get(r["id_usuario"], 0)} for r in model.con_adeudos(roles)]


def _pct(parte, total):
    """Porcentaje con un decimal ('12.5 %') o '—' si el total es cero.

    Args:
        parte (int | float): Numerador.
        total (int | float): Denominador.

    Returns:
        str: Porcentaje formateado.
    """
    return f"{round(100 * parte / total, 1)} %" if total else "—"


def indicadores(desde=None, hasta=None):
    """PS-MET-02/03 y CTX-03: indicadores operativos como filas [indicador, valor, detalle].

    Args:
        desde (date | None): Inicio del periodo para duración de préstamos y préstamos por mes.
        hasta (date | None): Fin del periodo.

    Returns:
        tuple[list[str], list[list]]: Columnas (Área, Indicador, Valor, Detalle) y filas.
    """
    a, inv = model.indicadores_asistente(), model.indicadores_inventario()
    dur = model.duracion_prestamos(desde, hasta)
    discrepancias = inv["prestados_sin_prestamo"] + inv["disponibles_con_prestamo"]
    filas = [
        ["Asistente", "Conversaciones totales", a["total"], "Todas las conversaciones registradas (PS-MET-03)"],
        ["Asistente", "Resueltas sin pasar a bibliotecario", _pct(a["resueltas_sin_bibliotecario"], a["total"]),
         f"{a['resueltas_sin_bibliotecario']} conversación(es) marcadas como resueltas que no pidieron un bibliotecario"],
        ["Asistente", "Atendidas sin pasar a bibliotecario", _pct(a["total"] - a["con_bibliotecario"], a["total"]),
         f"{a['total'] - a['con_bibliotecario']} de {a['total']}; las demás pidieron un bibliotecario"],
        ["Asistente", "Consultas para el bibliotecario pendientes", a["consultas_pendientes"], "Esperan respuesta del bibliotecario"],
        ["Circulación", "Duración promedio del préstamo (días)", dur["dias"] if dur["dias"] is not None else "—",
         f"Sobre {dur['devueltos']} préstamo(s) devuelto(s) del periodo"],
        ["Circulación", "Tiempo de atención de préstamo/devolución", "No disponible",
         "El sistema no registra el inicio de la atención en mostrador, solo su registro; requiere cronometraje (PS-MET-01, CTX-03)"],
        ["Inventario", "Ejemplares en circulación (sin bajas)", inv["ejemplares"], "Base del porcentaje de discrepancias"],
        ["Inventario", "Ejemplares «prestado» sin préstamo abierto", inv["prestados_sin_prestamo"], "Discrepancia"],
        ["Inventario", "Ejemplares «disponible» con préstamo abierto", inv["disponibles_con_prestamo"], "Discrepancia"],
        ["Inventario", "Libros activos sin ejemplares", inv["libros_sin_ejemplares"], "Inconsistencia de catálogo"],
        ["Inventario", "Discrepancias de inventario (%)", _pct(discrepancias, inv["ejemplares"]),
         f"{discrepancias} ejemplar(es); meta PS-MET-02: menos de 1 %"],
    ]
    for p in model.prestamos_por_mes(desde, hasta):
        filas.append(["Préstamos por periodo", p["periodo"], p["prestamos"], f"{p['devueltos']} devuelto(s)"])
    return ["Área", "Indicador", "Valor", "Detalle"], filas


def errores(desde=None, hasta=None):
    """PS-S3-06: errores del servidor (500) y del navegador registrados en la bitácora.

    Args:
        desde (date | None): Fecha inicial inclusiva.
        hasta (date | None): Fecha final inclusiva.

    Returns:
        tuple[list[str], list[list]]: Columnas (Fecha, Origen, Usuario, Detalle) y filas.
    """
    filas = []
    for r in model.errores(desde, hasta):
        origen, resumen = errores_log.parsear(r["detalle"])
        filas.append([r["fecha"].strftime("%Y-%m-%d %H:%M"), origen, r["matricula"] or "Sin sesión", resumen])
    return ["Fecha", "Origen", "Usuario", "Detalle"], filas


def _tabla(tipo, f):
    """-> (columnas, filas) de cada tipo de reporte.

    Args:
        tipo (str): Uno de `TIPOS` (el valor desconocido final cae en catalogo_completo/activo).
        f (dict): Filtros validados (planta, pasillo, librero, tema, desde, hasta, incluir_docentes).

    Returns:
        tuple[list[str], list[list]]: Columnas y filas.
    """
    if tipo == "indicadores":
        return indicadores(f["desde"], f["hasta"])
    if tipo == "errores":
        return errores(f["desde"], f["hasta"])
    if tipo == "usuarios":
        return (["Matrícula", "Nombre", "Correo", "Perfil", "Estado"],
                [[r["matricula"], r["nombre_completo"], r["correo"], r["perfil"], r["estado"]] for r in model.usuarios()])
    if tipo == "con_adeudos":
        return (["Matrícula", "Nombre", "Correo", "Libros vencidos", "Días de retraso", "Adeudo pendiente (MXN)",
                 "Suspendido"],
                [[r["matricula"], r["nombre_completo"], r["correo"], r["vencidos"], r["dias"], r["monto"], "Sí"]
                 for r in con_adeudos(f["incluir_docentes"])])
    if tipo == "inventario_estante":
        librero = f["librero"].zfill(2) if f["librero"] else None
        return (["Clave", "Título", "Ubicación", "Ejemplares", "Disponibles", "Prestados", "Bajas", "Conteo físico"],
                [[r["clave"], r["titulo"], texto_ubicacion(r), r["existencia"], r["disponibles"], r["prestados"], r["bajas"], ""]
                 for r in model.existencia(f["planta"], f["pasillo"], librero, f["tema"])])
    if tipo == "prestamos_vencidos":
        hoy = date.today()
        filas = []
        for p in model.prestamos_vencidos():
            d = circulacion.dias_retraso(p["fecha_vencimiento"], hoy)
            filas.append([p["matricula"], p["nombre_completo"], f"{p['clave']} · {p['titulo']}", p["numero_copia"],
                          _dia(p["fecha_prestamo"]), _dia(p["fecha_vencimiento"]), d,
                          circulacion.multa_retraso(d, p["multa_diaria"])])
        return (["Matrícula", "Usuario", "Libro", "Copia", "Préstamo", "Vencimiento", "Días de retraso",
                 "Multa estimada (MXN)"], filas)
    if tipo == "prestamos":
        hoy = date.today()
        filas = []
        for p in model.prestamos(f["desde"], f["hasta"]):
            estado = ("devuelto" if p["fecha_devolucion"] else
                      "vencido" if circulacion.esta_vencido(p["fecha_vencimiento"], None, hoy) else "activo")
            filas.append([p["id_prestamo"], p["matricula"], p["nombre_completo"], f"{p['clave']} · {p['titulo']}",
                          p["numero_copia"], _dia(p["fecha_prestamo"]), _dia(p["fecha_vencimiento"]),
                          _dia(p["fecha_devolucion"]), p["num_renovaciones"], estado])
        return (["Folio", "Matrícula", "Usuario", "Libro", "Copia", "Préstamo", "Vencimiento", "Devolución",
                 "Renovaciones", "Estado"], filas)
    columnas = ["Clave", "Título", "Autor", "Tema", "Ejemplares", "Disponibles", "Estado"]
    return columnas, [[r["clave"], r["titulo"], r["autor"], r["tema"], r["ejemplares"], r["disponibles"], r["estado"]]
                      for r in model.catalogo(tipo == "catalogo_activo")]


def generar(tipo, formato, actor, filtros=None):
    """Genera un reporte, lo registra en `reporte_generado` y en bitácora (acción `reporte`).

    Args:
        tipo (str): Uno de `TIPOS`.
        formato (str): 'pantalla' | 'pdf' | 'impresion'.
        actor (dict): Usuario que genera el reporte.
        filtros (dict | None): planta, pasillo, librero, tema, desde, hasta, incluir_docentes.

    Returns:
        dict: {tipo, generado, generado_por, columnas, filas, total}.

    Raises:
        ApiError: 404 si el tipo no es válido; 400 por formato o filtros inválidos o desde > hasta;
            403 si falta el permiso extra del tipo (`PERMISO_EXTRA`).
    """
    tipo, formato = validate({"tipo": tipo, "formato": formato}, SCHEMA).values()
    if tipo in PERMISO_EXTRA:
        require_permission(PERMISO_EXTRA[tipo], actor)
    filtros = filtros or {}
    f = {**validate(filtros, FILTROS), "incluir_docentes": bool(filtros.get("incluir_docentes"))}
    if f["desde"] and f["hasta"] and f["desde"] > f["hasta"]:
        raise ApiError("La fecha inicial no puede ser posterior a la final.")
    columnas, filas = _tabla(tipo, f)
    fecha = model.registrar(actor["id_usuario"], tipo, formato, len(filas))
    log(actor["id_usuario"], "reporte", f"Reporte {tipo} ({formato}), {len(filas)} filas")
    return {"tipo": tipo, "generado": fecha, "generado_por": actor["nombre_completo"],
            "columnas": columnas, "filas": filas, "total": len(filas)}


def aviso_con_adeudos(actor, incluir_docentes=False):
    """RF-28: un aviso `servicios_escolares` con las matrículas de los alumnos con adeudos (lista de avisos simulada, D-11).

    Bitácora: `reporte_con_adeudos_aviso`.

    Args:
        actor (dict): Usuario que envía el aviso (requiere permiso `prestamos`).
        incluir_docentes (bool): Incluir docentes en la lista.

    Returns:
        dict: {enviados, matriculas}.

    Raises:
        ApiError: 403 sin permiso `prestamos`; 422 si no hay usuarios con adeudos.
    """
    require_permission("prestamos", actor)
    lista = con_adeudos(incluir_docentes)
    if not lista:
        raise ApiError("No hay alumnos con adeudos a quienes avisar.", 422)
    matriculas = [r["matricula"] for r in lista]
    notificaciones.enviar("servicios_escolares", f"Alumnos con adeudos en la biblioteca ({len(matriculas)})",
                          ", ".join(matriculas), actor["id_usuario"], "Servicios Escolares")
    log(actor["id_usuario"], "reporte_con_adeudos_aviso", f"{len(matriculas)} con_adeudos: {', '.join(matriculas)}")
    return {"enviados": len(matriculas), "matriculas": matriculas}
