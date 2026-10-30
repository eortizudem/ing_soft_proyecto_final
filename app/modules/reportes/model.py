"""Capa modelo de reportes: consultas SQL de solo lectura para cada tipo de reporte y registro en `reporte_generado`.

Sin reglas de negocio ni formato de salida (eso es `service.py`).
"""

from app.core import consultas, repo


def catalogo(solo_activos):
    """Reporte `catalogo_completo` / `catalogo_activo`: libros con existencia y disponibilidad.

    Args:
        solo_activos (bool): Si es True, solo libros activos.

    Returns:
        list[dict]: clave, titulo, autor, tema, estado, ejemplares (sin bajas), disponibles.
    """
    return repo.fetch_all(
        f"""SELECT l.clave, l.titulo, l.autor, l.tema, l.estado,
             (SELECT count(*) FROM ejemplar e WHERE e.id_libro=l.id_libro AND e.estado<>'baja')::int AS ejemplares,
             CASE WHEN l.estado='activo' THEN
               {consultas.disponibles('l')}
               ELSE 0 END AS disponibles
           FROM libro l WHERE (NOT %s OR l.estado='activo') ORDER BY l.clave""", (solo_activos,))


def usuarios():
    """Reporte `usuarios`: todos los usuarios con su perfil.

    Returns:
        list[dict]: matricula, nombre_completo, correo, perfil, estado.
    """
    return repo.fetch_all(
        """SELECT u.matricula, u.nombre_completo, u.correo, r.descripcion AS perfil, u.estado
           FROM usuario u JOIN rol r ON r.id_rol=u.id_rol ORDER BY u.matricula""")


def registrar(id_usuario, tipo, formato, total):
    """Registra la generación de un reporte en `reporte_generado`.

    Args:
        id_usuario (int): Quien lo generó.
        tipo (str): Tipo de reporte.
        formato (str): 'pantalla' | 'pdf' | 'impresion'.
        total (int): Número de filas (se limita a 32767).

    Returns:
        datetime: Fecha de generación.
    """
    return repo.insert("reporte_generado", {"id_usuario": id_usuario, "tipo": tipo, "formato": formato,
                                            "total_titulos": min(total, 32767)}, returning="fecha")["fecha"]


def con_adeudos(roles):
    """Usuarios de los `roles` con préstamo vencido (D-24) o adeudo pendiente (misma definición que
    `core.circulacion.contexto_usuario`).

    Args:
        roles (Iterable[str]): Nombres de rol a incluir (p. ej. 'alumno', 'docente').

    Returns:
        list[dict]: id_usuario, matricula, nombre_completo, correo, rol, vencidos, adeudos, monto.
    """
    return repo.fetch_all(
        f"""SELECT * FROM (
             SELECT u.id_usuario, u.matricula, u.nombre_completo, u.correo, r.nombre AS rol,
               {consultas.prestamos_vencidos('u')} AS vencidos,
               {consultas.adeudos_pendientes('u')} AS adeudos,
               {consultas.adeudos_monto('u')} AS monto
             FROM usuario u JOIN rol r ON r.id_rol=u.id_rol) d
           WHERE d.rol = ANY(%s) AND (d.vencidos > 0 OR d.adeudos > 0)
           ORDER BY d.matricula""", (list(roles),))


def prestamos_vencidos():
    """Préstamos vencidos (D-24) con usuario, libro y tarifa diaria de la política con que se crearon (D-05).

    Returns:
        list[dict]: Préstamos vencidos ordenados por fecha de vencimiento, con `multa_diaria`.
    """
    return repo.fetch_all(
        f"""SELECT p.id_prestamo, p.id_usuario, u.matricula, u.nombre_completo, l.clave, l.titulo, e.numero_copia,
                  p.fecha_prestamo::date AS fecha_prestamo, p.fecha_vencimiento, pol.multa_diaria
           FROM prestamo p JOIN usuario u ON u.id_usuario=p.id_usuario
             JOIN ejemplar e ON e.id_ejemplar=p.id_ejemplar JOIN libro l ON l.id_libro=e.id_libro
             JOIN politica_prestamo pol ON pol.id_politica=p.id_politica
           WHERE p.{consultas.VENCIDO}
           ORDER BY p.fecha_vencimiento, p.id_prestamo""")


def prestamos(desde, hasta):
    """Reporte `prestamos`: préstamos cuya fecha de préstamo cae en el rango.

    Args:
        desde (date | None): Fecha inicial inclusiva; None = sin límite.
        hasta (date | None): Fecha final inclusiva; None = sin límite.

    Returns:
        list[dict]: Préstamos con usuario, libro, copia, fechas y renovaciones.
    """
    return repo.fetch_all(
        """SELECT p.id_prestamo, u.matricula, u.nombre_completo, l.clave, l.titulo, e.numero_copia,
                  p.fecha_prestamo::date AS fecha_prestamo, p.fecha_vencimiento,
                  p.fecha_devolucion::date AS fecha_devolucion, p.num_renovaciones
           FROM prestamo p JOIN usuario u ON u.id_usuario=p.id_usuario
             JOIN ejemplar e ON e.id_ejemplar=p.id_ejemplar JOIN libro l ON l.id_libro=e.id_libro
           WHERE (%(d)s::date IS NULL OR p.fecha_prestamo::date >= %(d)s)
             AND (%(h)s::date IS NULL OR p.fecha_prestamo::date <= %(h)s)
           ORDER BY p.fecha_prestamo, p.id_prestamo""", {"d": desde, "h": hasta})


def existencia(planta, pasillo, librero, tema):
    """Reporte `inventario_estante` (RF-16): existencias por libro y ubicación.

    Args:
        planta (str | None): Planta (sin distinguir mayúsculas); None = todas.
        pasillo (str | None): Letra de pasillo.
        librero (str | None): Librero a dos dígitos.
        tema (str | None): Texto contenido en el tema (sin acentos).

    Returns:
        list[dict]: clave, titulo, estado, ubicación, existencia (sin bajas), disponibles, prestados, bajas.
    """
    return repo.fetch_all(
        """SELECT l.clave, l.titulo, l.estado, u.planta, u.pasillo, u.librero, u.nivel,
             count(e.id_ejemplar) FILTER (WHERE e.estado<>'baja')::int AS existencia,
             count(e.id_ejemplar) FILTER (WHERE e.estado='disponible')::int AS disponibles,
             count(e.id_ejemplar) FILTER (WHERE e.estado='prestado')::int AS prestados,
             count(e.id_ejemplar) FILTER (WHERE e.estado='baja')::int AS bajas
           FROM libro l JOIN ubicacion u ON u.id_ubicacion=l.id_ubicacion
             LEFT JOIN ejemplar e ON e.id_libro=l.id_libro
           WHERE (%(pl)s::text IS NULL OR u.planta ILIKE %(pl)s::text) AND (%(pa)s::text IS NULL OR u.pasillo = %(pa)s::text)
             AND (%(li)s::text IS NULL OR u.librero = %(li)s::text)
             AND (%(t)s::text IS NULL OR unaccent(l.tema) ILIKE unaccent(%(t)s::text))
           GROUP BY l.id_libro, u.id_ubicacion ORDER BY u.planta, u.pasillo, u.librero, u.nivel, l.clave""",
        {"pl": planta, "pa": pasillo, "li": librero, "t": f"%{tema}%" if tema else None})


# ---- Indicadores (PS-MET-02/03, CTX-03) e errores (PS-S3-06) ----
def indicadores_asistente():
    """Conversaciones del asistente: total, con_bibliotecario, resueltas sin pasar a bibliotecario y consultas pendientes."""
    return repo.fetch_one(
        f"""SELECT count(*)::int AS total,
             count(*) FILTER (WHERE {consultas.CON_BIBLIOTECARIO})::int AS con_bibliotecario,
             count(*) FILTER (WHERE c.resuelta AND NOT {consultas.CON_BIBLIOTECARIO})::int AS resueltas_sin_bibliotecario,
             count(*) FILTER (WHERE NOT c.resuelta AND {consultas.CON_BIBLIOTECARIO})::int AS consultas_pendientes
           FROM conversacion c""")


def indicadores_inventario():
    """Discrepancias de inventario: estado del ejemplar inconsistente con sus prestamos abiertos (D-24)."""
    return repo.fetch_one(
        f"""SELECT count(*) FILTER (WHERE e.estado <> 'baja')::int AS ejemplares,
             count(*) FILTER (WHERE e.estado = 'prestado' AND NOT EXISTS (
               SELECT 1 FROM prestamo p WHERE p.id_ejemplar = e.id_ejemplar AND p.{consultas.ABIERTO}))::int AS prestados_sin_prestamo,
             count(*) FILTER (WHERE e.estado = 'disponible' AND EXISTS (
               SELECT 1 FROM prestamo p WHERE p.id_ejemplar = e.id_ejemplar AND p.{consultas.ABIERTO}))::int AS disponibles_con_prestamo,
             (SELECT count(*) FROM libro l WHERE l.estado = 'activo' AND NOT EXISTS (
               SELECT 1 FROM ejemplar x WHERE x.id_libro = l.id_libro AND x.estado <> 'baja'))::int AS libros_sin_ejemplares
           FROM ejemplar e""")


def duracion_prestamos(desde, hasta):
    """Promedio de días entre el préstamo y la devolución (préstamos devueltos del periodo).

    Args:
        desde (date | None): Fecha inicial inclusiva.
        hasta (date | None): Fecha final inclusiva.

    Returns:
        dict: {devueltos, dias} (`dias` es None si no hay devueltos).
    """
    return repo.fetch_one(
        """SELECT count(*)::int AS devueltos,
             round(avg(extract(epoch FROM (p.fecha_devolucion - p.fecha_prestamo)) / 86400)::numeric, 1) AS dias
           FROM prestamo p WHERE p.fecha_devolucion IS NOT NULL
             AND (%(d)s::date IS NULL OR p.fecha_prestamo::date >= %(d)s)
             AND (%(h)s::date IS NULL OR p.fecha_prestamo::date <= %(h)s)""", {"d": desde, "h": hasta})


def prestamos_por_mes(desde, hasta):
    """Préstamos y devueltos por mes (AAAA-MM) según fecha de préstamo.

    Args:
        desde (date | None): Fecha inicial inclusiva.
        hasta (date | None): Fecha final inclusiva.

    Returns:
        list[dict]: periodo, prestamos, devueltos.
    """
    return repo.fetch_all(
        """SELECT to_char(p.fecha_prestamo, 'YYYY-MM') AS periodo, count(*)::int AS prestamos,
             count(*) FILTER (WHERE p.fecha_devolucion IS NOT NULL)::int AS devueltos
           FROM prestamo p
           WHERE (%(d)s::date IS NULL OR p.fecha_prestamo::date >= %(d)s)
             AND (%(h)s::date IS NULL OR p.fecha_prestamo::date <= %(h)s)
           GROUP BY 1 ORDER BY 1""", {"d": desde, "h": hasta})


def errores(desde, hasta, limite=200):
    """Errores de la bitácora (más recientes primero); `matricula` es NULL si no había sesión (PS-S3-06).

    Args:
        desde (date | None): Fecha inicial inclusiva.
        hasta (date | None): Fecha final inclusiva.
        limite (int): Máximo de renglones.

    Returns:
        list[dict]: fecha, detalle, matricula.
    """
    return repo.fetch_all(
        """SELECT b.fecha, b.detalle, u.matricula FROM bitacora b LEFT JOIN usuario u ON u.id_usuario = b.id_usuario
           WHERE b.accion = 'error_sistema'
             AND (%(d)s::date IS NULL OR b.fecha::date >= %(d)s)
             AND (%(h)s::date IS NULL OR b.fecha::date <= %(h)s)
           ORDER BY b.fecha DESC, b.id_bitacora DESC LIMIT %(n)s""", {"d": desde, "h": hasta, "n": limite})
