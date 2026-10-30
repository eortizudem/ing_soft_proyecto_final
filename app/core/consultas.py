"""Consultas y fragmentos SQL compartidos por varios modulos (una sola definicion de cada concepto).

Fragmentos: cadenas SQL para incrustar en un SELECT; reciben el alias de la tabla externa.
  * `disponibles(l)`            ejemplares 'disponible' del libro `l`.
  * `prestamos_abiertos(u)`     D-24: prestamos con `fecha_devolucion IS NULL` del usuario `u`.
  * `prestamos_vencidos(u)`     D-24: abiertos con `fecha_vencimiento < hoy`.
  * `adeudos_pendientes(u)` / `adeudos_monto(u)`  conteo / suma de adeudos 'pendiente' del usuario `u`.
  * `CON_BIBLIOTECARIO`                  conversacion `c` del asistente con algun mensaje de la intencion 'pasar_a_bibliotecario'.
`prestamo.estado` es solo cache; nunca se usa para decidir (ver core.circulacion).
Busquedas: `usuario_por_matricula`, `libro_por_clave` (sin distinguir mayusculas).
"""
from . import repo

# Predicados SQL de D-24 (se incrustan con alias `p` de prestamo).
ABIERTO = "fecha_devolucion IS NULL"
VENCIDO = f"{ABIERTO} AND fecha_vencimiento < CURRENT_DATE"
CON_BIBLIOTECARIO = ("EXISTS (SELECT 1 FROM mensaje m JOIN intencion i ON i.id_intencion = m.id_intencion "
            "WHERE m.id_conversacion = c.id_conversacion AND i.nombre = 'pasar_a_bibliotecario')")


def disponibles(l="l"):
    """Subconsulta: numero de ejemplares 'disponible' del libro con alias `l`."""
    return f"(SELECT count(*) FROM ejemplar e WHERE e.id_libro = {l}.id_libro AND e.estado = 'disponible')::int"


def prestamos_abiertos(u="u"):
    """Subconsulta: prestamos abiertos (sin devolucion) del usuario con alias `u` (D-24)."""
    return f"(SELECT count(*) FROM prestamo p WHERE p.id_usuario = {u}.id_usuario AND p.{ABIERTO})::int"


def prestamos_vencidos(u="u"):
    """Subconsulta: prestamos vencidos del usuario con alias `u` (D-24)."""
    return f"(SELECT count(*) FROM prestamo p WHERE p.id_usuario = {u}.id_usuario AND p.{VENCIDO})::int"


def adeudos_pendientes(u="u"):
    """Subconsulta: numero de adeudos 'pendiente' del usuario con alias `u`."""
    return (f"(SELECT count(*) FROM adeudo a JOIN prestamo p ON p.id_prestamo = a.id_prestamo "
            f"WHERE p.id_usuario = {u}.id_usuario AND a.estado = 'pendiente')::int")


def adeudos_monto(u="u"):
    """Subconsulta: suma de adeudos 'pendiente' del usuario con alias `u` (0 si no hay)."""
    return (f"(SELECT COALESCE(sum(a.monto), 0) FROM adeudo a JOIN prestamo p ON p.id_prestamo = a.id_prestamo "
            f"WHERE p.id_usuario = {u}.id_usuario AND a.estado = 'pendiente')")


def usuario_por_matricula(matricula):
    """`{id_usuario, matricula, nombre_completo, estado}` o None."""
    return repo.fetch_one("SELECT id_usuario, matricula, nombre_completo, estado FROM usuario "
                          "WHERE upper(matricula) = upper(%s)", (matricula,))


def libro_por_clave(clave):
    """`{id_libro, clave, titulo, estado}` o None."""
    return repo.fetch_one("SELECT id_libro, clave, titulo, estado FROM libro WHERE upper(clave) = upper(%s)", (clave,))
