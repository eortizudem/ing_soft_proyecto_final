"""Asistente basado en reglas (D-13): intenciones por palabras clave + similitud con pregunta_frecuente.

Sin LLM ni llamadas externas. Las reglas de negocio se explican con `politica_prestamo` (via core.circulacion);
el estatus propio usa `circulacion.contexto_usuario` y `circulacion.dias_retraso/multa_retraso`.
"""
import re
import unicodedata
from datetime import date

from flask import session

from app.core import circulacion, parametros
from app.core.auth import has_permission
from app.core.bitacora import audit
from app.core.errors import ApiError
from app.core.repo import get_or_404
from app.core.serializers import texto_ubicacion
from app.core.validators import Bool, Enum, Int, Str, validate

from . import model

UMBRAL = 2.0          # puntaje minimo para aceptar una intencion
MAX_LIBROS = 5
SESION_CLAVE = "asistente_convs"

MENSAJE = {
    "texto": Str("mensaje", max=500, max_msg="El mensaje admite máximo 500 caracteres."),
    "id_conversacion": Int(1, None, msg="Conversación inválida.", required=False),
    "canal": Enum(("web", "movil"), "Selecciona un canal válido.", required=False, default="web"),
}
CALIFICACION = {
    "calificacion": Int(1, 5, msg="La respuesta debe ser un número del 1 al 5."),
    "resuelta": Bool(msg="El campo resuelta debe ser verdadero o falso.", required=False),
}
RESPUESTA = {"respuesta": Str("respuesta", max=500, max_msg="La respuesta admite máximo 500 caracteres.")}

# ---------------------------------------------------------------- normalizacion y diccionario
def normalizar(texto):
    """Minusculas, sin acentos (la n con tilde pasa a n), solo letras/digitos/espacios."""
    t = unicodedata.normalize("NFD", str(texto or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", t)).strip()


def _w(*palabras, peso=2.0):
    return [(p, peso) for p in palabras]


# intencion -> [(raiz o frase normalizada, peso)]. Una palabra suma `peso` una sola vez.
PALABRAS = {
    "pasar_a_bibliotecario": _w("bibliotecari", "agente", "contactar", peso=3.0) + _w(
        "hablar con un", "hablar con una", "hablar con el", "hablar con alguien", "hablar con otra persona",
        "una persona", "persona real", "humano", "atencion personal", "comunicarme con", peso=6.0)
    + _w("no me ayudaste", "no me sirve", "no resolviste", peso=4.0),
    "estatus_prestamos": _w("mis prestamos", "mi prestamo", "mis libros", "que libros tengo", "tengo prestado",
                            "tengo prestados", "cuando vence", "vence mi", "vencen mis", "mis renovaciones",
                            "cuantos libros tengo", "mi estatus", "mi estado", "estatus de mis", peso=6.0),
    "estatus_multas": _w("mis multas", "mi multa", "tengo multa", "tengo multas", "tengo adeudo", "tengo adeudos",
                         "mis adeudos", "cuanto debo", "debo algo", "tengo deuda", "mi deuda", "mis deudas", peso=6.0),
    "reglas": _w("reglas", "regla", "politica", "norma", "reglamento", "como funciona", "que necesito",
                 "requisito", "vigencia", "condiciones"),
    "renovacion": _w("renov", "renuev", "extender", "ampliar", "mas tiempo", "prorroga", "alargar"),
    "multas": _w("multa", "adeudo", "deuda", "retraso", "pagar", "perdi", "pierd", "perdida", "extravi", "dano", "danio",
                 "reposicion", "sancion", "penaliza"),
    "prestamo": _w("prestamo", "prestar", "prestan", "prestado", "llevar", "llevo", "cuantos libros", "plazo",
                   "dias de prestamo", "devolver", "devolucion"),
    "horarios": _w("horario", "a que hora", "abren", "abre", "cierran", "cierra", "abierta", "abierto",
                   "hasta que hora", "servicio"),
    "ubicacion": _w("donde", "ubicacion", "ubicar", "localizar", "pasillo", "librero", "planta", "encuentro",
                    "como llego"),
    "buscar_libro": _w("libro", "buscar", "busco", "busca", "autor", "tema", "titulo", "editorial", "disponible",
                       "disponibilidad", "tienen", "catalogo", "ejemplar", "novela", "clave", "hay"),
    "recuperar_contrasena": _w("contrasena", "password", "olvide", "recuperar", "clave de acceso", "no puedo entrar", peso=3.0),
    "solicitar_compra": _w("comprar", "compra", "adquisicion", "adquirir", "que compren", "solicitar libro"),
    "ayuda": _w("ayuda", "que puedes", "que sabes", "que haces", "como funcionas", "opciones", "menu", "para que sirves"),
    "saludo": _w("hola", "buenas", "buenos dias", "buen dia", "que tal", "hey", "saludos", "buenas tardes"),
    "despedida": _w("adios", "hasta luego", "gracias", "chao", "bye", "nos vemos", "eso es todo", "hasta pronto"),
}
def _patron(p):
    p = p.strip()
    return re.compile(r"\b" + re.escape(p) + (r"\b" if len(p) <= 4 else ""))


_PATRONES = {i: [(_patron(p), w) for p, w in pal] for i, pal in PALABRAS.items()}

STOP = set(normalizar(
    "el la los las un una unos unas de del al y o u en a por para con sin sobre que cual cuales como cuando donde "
    "es esta estan son hay tiene tienen tengo quiero quisiera necesito busco buscar busca buscame encuentro encontrar "
    "me mi mis se lo le les muy mas menos favor puedes puede podria pueden dime dame ver saber hola gracias "
    "libro libros disponible disponibles disponibilidad ejemplar ejemplares catalogo autor tema titulo editorial clave "
    "ubicacion ubicar localizar biblioteca algun alguno alguna algunos algunas existe existen").split())

FALLBACK = {
    "saludo": "¡Hola! Soy el asistente de LibriGest. Puedo buscar libros y explicarte préstamos, renovaciones y multas.",
    "despedida": "¡Hasta luego! Aquí estaré si necesitas algo más.",
    "ayuda": "Puedo buscar libros, explicar las reglas de préstamo, renovación y multas, y (con sesión iniciada) "
             "consultar tus préstamos y adeudos.",
    "horarios": "Consulta el horario de la biblioteca con el personal de mostrador.",
    "ubicacion": "Busca el libro en Buscar y localizar: la ficha indica planta, pasillo, librero y nivel.",
    "buscar_libro": "Escribe el título, autor o tema del libro que buscas.",
    "recuperar_contrasena": 'En la pantalla de inicio de sesión elige "Olvidé mi contraseña".',
    "solicitar_compra": "El personal de compras registra las solicitudes desde el módulo Compras.",
    "pasar_a_bibliotecario": "Registré tu solicitud; un bibliotecario revisará la conversación y te responderá.",
    "no_entendido": "No logré entender tu pregunta. ¿Quieres reformularla o hablar con un bibliotecario?",
}


def _tokens(texto):
    return {t[:5] for t in normalizar(texto).split() if len(t) >= 3 and t not in STOP}


def _dice(a, b):
    return 2 * len(a & b) / (len(a) + len(b)) if a and b else 0.0


def detectar(texto, faqs):
    """-> (intencion, puntaje, ranking). Puntaje = palabras clave + 4 x similitud (Dice) con la mejor FAQ."""
    n = normalizar(texto)
    puntos = {}
    for intencion, pats in _PATRONES.items():
        s = sum(w for p, w in pats if p.search(n))
        if s:
            puntos[intencion] = s
    tk = _tokens(texto)
    for f in faqs:
        d = _dice(tk, _tokens(f["pregunta"]))
        if d:
            puntos[f["intencion"]] = puntos.get(f["intencion"], 0) + 4 * d
    if not puntos:
        return "no_entendido", 0.0
    mejor = max(puntos, key=lambda i: (puntos[i], -list(PALABRAS).index(i) if i in PALABRAS else -99))
    if puntos[mejor] < UMBRAL:
        return "no_entendido", puntos[mejor]
    return mejor, puntos[mejor]


def terminos_libro(texto):
    """Terminos de busqueda: lo citado entre comillas o las palabras que no son de relleno (max. 4)."""
    m = re.search(r"[\"“«'‘](.{2,}?)[\"”»'’]", str(texto))
    if m:
        return [normalizar(m.group(1))]
    return [t for t in normalizar(texto).split() if len(t) >= 3 and t not in STOP and t not in _NO_TERMINO][:4]


_NO_TERMINO = set(normalizar(
    "horario horarios hora multa multas prestamo prestamos renovar renovacion reglas politica quiero busco dias").split())


# ---------------------------------------------------------------- redaccion de respuestas
def _plural(n, uno, varios):
    return f"{n} {uno if n == 1 else varios}"


def _dinero(x):
    return f"${float(x):,.2f} MXN"


def _fecha(d):
    return d.strftime("%d/%m/%Y")


def _faq(intencion, texto, faqs):
    cand = [f for f in faqs if f["intencion"] == intencion]
    if not cand:
        return FALLBACK.get(intencion, FALLBACK["no_entendido"])
    tk = _tokens(texto)
    return max(cand, key=lambda f: _dice(tk, _tokens(f["pregunta"])))["respuesta"]


def _politicas(user):
    """[(descripcion del rol, politica)] del usuario o, sin politica propia (visitante), de todos los roles."""
    if user.get("id_usuario"):
        cu = circulacion.contexto_usuario(user["id_usuario"])
        if cu["politica"]:
            return [(cu["usuario"]["rol"], cu["politica"])]
    pares = [(r["descripcion"], circulacion.politica_vigente(r["id_rol"])) for r in model.roles()]
    return [(d, p) for d, p in pares if p]


def _linea_politica(rol, p):
    return (f"{rol}: {_plural(p['dias_prestamo'], 'día hábil', 'días hábiles')} de préstamo por libro, hasta "
            f"{_plural(p['max_libros'], 'libro', 'libros')} a la vez, {_plural(p['max_renovaciones'], 'renovación', 'renovaciones')} "
            f"y multa de {_dinero(p['multa_diaria'])} por día hábil de retraso y por libro.")


def _explicar(intencion, texto, user):
    pols = _politicas(user)
    if not pols:
        return "Todavía no hay una política de préstamo vigente para tu perfil. Consulta con un bibliotecario."
    lineas = "\n".join(_linea_politica(r, p) for r, p in pols)
    prestamo = ("Préstamo: " + lineas + "\nLos sábados y domingos no cuentan. Para que te presten un libro no debes tener "
                "multas pendientes ni préstamos vencidos, no exceder tu límite y el libro debe estar disponible y ser de préstamo externo.")
    renov = ("Renovación: puedes renovar si el préstamo no está vencido, no tienes multas pendientes, nadie está en lista de "
             "espera del libro y no superas tus renovaciones (" + "; ".join(
                 f"{r}: {p['max_renovaciones']}" for r, p in pols) + "). Cada renovación suma otro periodo completo ("
             + "; ".join(f"{r}: {p['dias_prestamo']} días hábiles" for r, p in pols) + ").")
    multa = ("Multas: " + "; ".join(f"{r}: {_dinero(p['multa_diaria'])}" for r, p in pols) + " por día hábil de retraso y por libro. "
             "Se paga en Tesorería y el bibliotecario registra el pago.")
    perdida = (f"\nSi pierdes un libro se cobra su valor de reposición (precio de la última compra en dólares por el tipo de "
               f"cambio del día, hoy {float(parametros.tipo_cambio()):.2f} MXN/USD) más las multas acumuladas.")
    n = normalizar(texto)
    if intencion == "prestamo":
        return prestamo
    if intencion == "renovacion":
        return renov
    if intencion == "multas":
        return multa + (perdida if re.search(r"\b(perd|pierd|extravi|robo|dan|reposicion)", n) else "")
    return "\n".join((prestamo, renov, multa))


def _estatus_prestamos(user):
    cu = circulacion.contexto_usuario(user["id_usuario"])
    filas = model.prestamos_abiertos(user["id_usuario"])
    if not filas:
        return "No tienes préstamos activos." + (" Tienes multas pendientes." if cu["adeudos_pendientes"] else "")
    hoy, partes = date.today(), []
    for f in filas:
        dias = circulacion.dias_retraso(f["fecha_vencimiento"], hoy)
        estado = (f"VENCIDO ({_plural(dias, 'día hábil', 'días hábiles')} de retraso, multa estimada "
                  f"{_dinero(circulacion.multa_retraso(dias, f['multa_diaria']))})") if f["fecha_vencimiento"] < hoy \
            else f"vence el {_fecha(f['fecha_vencimiento'])}"
        partes.append(f"• {f['titulo']}: {estado}; renovaciones {f['num_renovaciones']}/{f['max_renovaciones']}.")
    cab = f"Tienes {_plural(len(filas), 'préstamo activo', 'préstamos activos')}"
    if cu["suspendido"]:
        cab += " y tu cuenta está suspendida para nuevos préstamos (por vencidos o multas)"
    return cab + ":\n" + "\n".join(partes)


def _estatus_multas(user):
    cu = circulacion.contexto_usuario(user["id_usuario"])
    filas = model.adeudos_pendientes(user["id_usuario"])
    vencidos = [f for f in model.prestamos_abiertos(user["id_usuario"]) if f["fecha_vencimiento"] < date.today()]
    if not filas and not vencidos:
        return "No tienes multas ni adeudos pendientes."
    partes = []
    if filas:
        partes.append(f"Tienes {_plural(cu['adeudos_pendientes'], 'adeudo pendiente', 'adeudos pendientes')} por "
                      f"{_dinero(cu['adeudos_monto'])}:")
        partes += [f"• {f['titulo']} ({f['tipo']}): {_dinero(f['monto'])}." for f in filas]
        partes.append("Págalos en Tesorería; el bibliotecario registra el pago.")
    if vencidos:
        partes.append(f"Además tienes {_plural(len(vencidos), 'préstamo vencido', 'préstamos vencidos')}: la multa sigue creciendo hasta devolver.")
    return "\n".join(partes)


def _libros(texto):
    terminos = terminos_libro(texto)
    if not terminos:
        return None, []
    filas = model.buscar_libros(terminos, MAX_LIBROS)
    libros = [{"id_libro": f["id_libro"], "clave": f["clave"], "titulo": f["titulo"], "disponibles": f["disponibles"],
               "ubicacion": texto_ubicacion(f)}
              for f in filas]
    return " ".join(terminos), libros


def _responder(intencion, texto, user, faqs, previa):
    """-> dict respuesta (sin persistir). `previa` = ultima intencion del asistente en la conversacion."""
    r = {"texto": "", "intencion": intencion, "con_bibliotecario": False}
    if intencion == "no_entendido" and previa == "no_entendido":
        intencion = r["intencion"] = "pasar_a_bibliotecario"
    if intencion == "pasar_a_bibliotecario":
        r.update(texto=_faq(intencion, texto, faqs), con_bibliotecario=True)
    elif intencion in ("buscar_libro", "ubicacion"):
        consulta, libros = _libros(texto)
        if consulta is None:  # sin título/autor/tema: pedirlo (no responder con una FAQ cualquiera)
            r["texto"] = FALLBACK[intencion]
        elif libros:
            r.update(texto=f"Encontré {_plural(len(libros), 'libro', 'libros')} para «{consulta}»:", libros=libros,
                     enlaces=[{"texto": "Buscar y localizar", "ruta": "buscar"}])
        else:
            r["texto"] = f"No encontré libros activos para «{consulta}». Prueba con otro título, autor, tema, clave o editorial."
    elif intencion in ("prestamo", "renovacion", "multas", "reglas"):
        r["texto"] = _explicar(intencion, texto, user)
    elif intencion in ("estatus_prestamos", "estatus_multas"):
        if not user.get("id_usuario"):
            r["texto"] = "Para consultar tus préstamos y adeudos debes iniciar sesión con tu cuenta (los visitantes no tienen datos propios)."
        else:
            r["texto"] = (_estatus_prestamos if intencion == "estatus_prestamos" else _estatus_multas)(user)
    elif intencion == "saludo":
        nombre = user["nombre_completo"].split()[0] if user.get("id_usuario") else ""
        r["texto"] = f"¡Hola{' ' + nombre if nombre else ''}! " + FALLBACK["saludo"].split("! ", 1)[1]
    else:
        r["texto"] = _faq(intencion, texto, faqs)
    return r


# ---------------------------------------------------------------- conversaciones y permisos
def _es_staff(user):
    return has_permission(user, "prestamos")


def _recordadas():
    return list(session.get(SESION_CLAVE, []))


def _es_dueno(conv, user):
    if user.get("id_usuario"):
        return conv["id_usuario"] == user["id_usuario"]
    return conv["id_usuario"] is None and conv["id_conversacion"] in _recordadas()


def _cargar(id_conversacion, user, staff_ok=False):
    conv = model.conversacion(id_conversacion)
    if not conv or not (_es_dueno(conv, user) or (staff_ok and _es_staff(user) and model.va_con_bibliotecario(id_conversacion))):
        raise ApiError("No se encontró la conversación.", 404)
    return conv


def _forma(conv, user):
    out = {"id_conversacion": conv["id_conversacion"], "resuelta": conv["resuelta"], "calificacion": conv["calificacion"],
           "con_bibliotecario": model.va_con_bibliotecario(conv["id_conversacion"]), "fecha_inicio": conv["fecha_inicio"],
           "mensajes": model.mensajes(conv["id_conversacion"])}
    if _es_staff(user):
        u = conv["id_usuario"] and get_or_404("usuario", "id_usuario", conv["id_usuario"])
        out["usuario"] = {"matricula": u["matricula"], "nombre_completo": u["nombre_completo"]} if u else None
    return out


def enviar_mensaje(data, user):
    d = validate(data, MENSAJE)
    ids = model.intenciones()
    faqs = model.faqs()
    if d["id_conversacion"]:
        conv = _cargar(d["id_conversacion"], user)
    else:
        conv = model.crear_conversacion(user.get("id_usuario"), d["canal"])
        if not user.get("id_usuario"):
            session[SESION_CLAVE] = _recordadas()[-19:] + [conv["id_conversacion"]]
    cid = conv["id_conversacion"]
    previa = model.ultima_intencion_asistente(cid)
    intencion, _ = detectar(d["texto"], faqs)
    if intencion not in ids:
        intencion = "no_entendido"
    resp = _responder(intencion, d["texto"], user, faqs, previa)
    model.agregar_mensaje(cid, "usuario", d["texto"], ids.get(intencion))
    model.agregar_mensaje(cid, "asistente", resp["texto"], ids.get(resp["intencion"]))
    return {"id_conversacion": cid, "respuesta": resp}


def obtener(id_conversacion, user):
    return _forma(_cargar(id_conversacion, user, staff_ok=True), user)


def valorar(id_conversacion, data, user):
    conv = _cargar(id_conversacion, user)
    d = validate(data, CALIFICACION)
    valores = {"calificacion": d["calificacion"]}
    # una consulta pendiente solo la cierra el bibliotecario
    if d["resuelta"] is not None and not (d["resuelta"] and model.va_con_bibliotecario(conv["id_conversacion"]) and not conv["resuelta"]):
        valores["resuelta"] = d["resuelta"]
        valores["fecha_fin"] = None
    return _forma(model.valorar(id_conversacion, valores), user)


def consultas_bibliotecario(user, estado=""):
    if estado not in ("", "pendiente", "resuelta"):
        raise ApiError("Estado inválido.", 400)
    return [{"id_conversacion": r["id_conversacion"], "fecha_inicio": r["fecha_inicio"], "resuelta": r["resuelta"],
             "ultimo_mensaje": r["ultimo_mensaje"],
             "usuario": {"matricula": r["matricula"], "nombre_completo": r["nombre_completo"]} if r["matricula"] else None}
            for r in model.consultas_bibliotecario(estado)]


@audit("asistente_resolver", lambda r: f"Consulta {r['id_conversacion']} resuelta")
def resolver(id_conversacion, data, actor):
    d = validate(data, RESPUESTA)
    conv = model.conversacion(id_conversacion)
    if not conv or not model.va_con_bibliotecario(id_conversacion):
        raise ApiError("No se encontró la consulta.", 404)
    if conv["resuelta"]:
        raise ApiError("La consulta ya fue resuelta.", 409)
    model.agregar_mensaje(id_conversacion, "asistente", "[Bibliotecario] " + d["respuesta"], None)
    return _forma(model.resolver(id_conversacion), actor)
