"""Lista de espera: avance de la fila (D-19). Prestamos (devolucion), adeudos (dano que libera el ejemplar) y el
barrido de espera llaman a ESTA funcion; ningun modulo reimplementa el reservado ni el aviso."""
from datetime import datetime

from . import circulacion, notificaciones, repo
from .bitacora import log

# Estados de lista_espera que aun ocupan lugar en la fila.
ACTIVOS = ("en_espera", "notificado")


def siguiente(id_libro):
    """Primer usuario `en_espera` del libro (FIFO), bloqueado para actualizarlo."""
    return repo.fetch_one(
        """SELECT id_espera, id_usuario FROM lista_espera WHERE id_libro = %s AND estado = 'en_espera'
           ORDER BY posicion, fecha_solicitud, id_espera LIMIT 1 FOR UPDATE""", (id_libro,))


def notificar_espera(id_libro):
    """D-19: mientras sobren ejemplares disponibles sin apartar, el siguiente en espera pasa a 'notificado' con
    plazo (`limite_reserva`) y recibe un correo. Devuelve la lista `[{id_espera, id_usuario}]` notificada
    (vacia si el libro no es prestable, no sobra ejemplar o nadie espera)."""
    ctx = circulacion.contexto_libro(id_libro)
    libro = ctx["libro"]
    if libro["estado"] != "activo" or libro["tipo_uso"] != "prestamo_externo":
        return []
    notificados = []
    for _ in range(max(ctx["disponibles"] - ctx["reservados"], 0)):
        entrada = siguiente(id_libro)
        if not entrada:
            break
        limite = circulacion.limite_reserva()
        repo.update("lista_espera", "id_espera", entrada["id_espera"],
                    {"estado": "notificado", "fecha_notificacion": datetime.now(), "fecha_limite_recoger": limite},
                    returning=None)
        notificaciones.enviar_a_usuario(
            "email", f"Libro disponible: {libro['clave']}",
            f"Ya hay un ejemplar de «{libro['titulo']}» reservado para ti hasta el {limite:%d/%m/%Y}.",
            entrada["id_usuario"])
        log(entrada["id_usuario"], "espera_notificar", f"{libro['clave']}: reservado hasta {limite:%Y-%m-%d}")
        notificados.append({"id_espera": entrada["id_espera"], "id_usuario": entrada["id_usuario"]})
    return notificados
