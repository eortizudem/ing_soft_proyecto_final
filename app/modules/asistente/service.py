"""Capa SERVICE del asistente: asistente basado en reglas (D-13; RF-29..RF-33, RNF-12..RNF-14).

Intenciones por palabras clave + similitud con `pregunta_frecuente`. Sin LLM ni llamadas externas, por lo que
responde en milisegundos (RNF-13, <= 3 s). Las reglas de negocio se explican con `politica_prestamo` (via
core.circulacion); el estatus propio usa `circulacion.contexto_usuario` y `circulacion.dias_retraso/multa_retraso`.

Algoritmo de deteccion de intencion (`detectar`):
  1. `normalizar(texto)`: minusculas, sin acentos, solo letras/digitos/espacios.
  2. Puntaje por palabras clave: para cada intencion de `PALABRAS` se suma el peso de cada raiz o frase que aparece
     (una sola vez por entrada). Pesos: 2.0 por defecto (una palabra generica basta para alcanzar `UMBRAL`); 3.0 para
     terminos de `pasar_a_bibliotecario` y `recuperar_contrasena`; 4.0 para quejas ("no me sirve"); 6.0 para frases
     explicitas ("mis prestamos", "hablar con un"), que deben ganar a las intenciones genericas. Las entradas de
     4 caracteres o menos exigen coincidencia de palabra completa (`\\b...\\b`); las mas largas funcionan como raiz.
  3. Puntaje por FAQ: tokens = primeros 5 caracteres de cada palabra (>= 3 letras, fuera de `STOP`); a la intencion de
     cada FAQ se le suma 4 x Dice(tokens del texto, tokens de la pregunta), con Dice = 2|A n B| / (|A| + |B|).
  4. Gana el mayor puntaje total; el empate lo gana la intencion que aparece primero en `PALABRAS` (prioridad).
  5. Si el mejor puntaje es menor que `UMBRAL` (2.0) o no hay puntaje, la intencion es `no_entendido`. Dos
     `no_entendido` consecutivos en una conversacion escalan a `pasar_a_bibliotecario` (RF-33, ver `_responder`).
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

UMBRAL = 2.0          # puntaje minimo para aceptar una intencion (un termino generico de peso 2.0 basta)
MAX_LIBROS = 5        # maximo de libros por respuesta de busqueda (RF-30)
SESION_CLAVE = "asistente_convs"   # clave de sesion con las conversaciones del visitante (ultimas 20)

# Esquemas de validacion (app.core.validators) de los payloads de entrada.
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
    """Minusculas, sin acentos (la n con tilde pasa a n), solo letras/digitos/espacios.

    Args:
        texto (str | None): texto libre; `None` se trata como cadena vacia.

    Returns:
        str: texto normalizado con espacios colapsados.
    """
    t = unicodedata.normalize("NFD", str(texto or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", t)).strip()


def _w(*palabras, peso=2.0):
    """Construye entradas `(raiz o frase, peso)` del diccionario `PALABRAS`.

    Args:
        *palabras (str): raices o frases ya normalizadas.
        peso (float): puntaje que aporta cada una al coincidir.

    Returns:
        list[tuple[str, float]]: pares `(palabra, peso)`.
    """
    return [(p, peso) for p in palabras]


# Diccionario de intenciones: intencion -> [(raiz o frase normalizada, peso)]. Una palabra suma `peso` una sola vez.
# El orden de las claves es la prioridad de desempate en `detectar` (primero = mayor prioridad).
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
    """Compila la expresion de una palabra clave: palabra completa si mide <= 4 caracteres, raiz (prefijo) si es mas larga.

    Args:
        p (str): raiz o frase normalizada.

    Returns:
        re.Pattern: patron listo para `search` sobre texto normalizado.
    """
    p = p.strip()
    return re.compile(r"\b" + re.escape(p) + (r"\b" if len(p) <= 4 else ""))


# Patrones precompilados de `PALABRAS` (se calculan una sola vez al importar el modulo).
_PATRONES = {i: [(_patron(p), w) for p, w in pal] for i, pal in PALABRAS.items()}

# Palabras de relleno que no aportan a la similitud con FAQ ni a la busqueda de libros.
STOP = set(normalizar(
    "el la los las un una unos unas de del al y o u en a por para con sin sobre que cual cuales como cuando donde "
    "es esta estan son hay tiene tienen tengo quiero quisiera necesito busco buscar busca buscame encuentro encontrar "
    "me mi mis se lo le les muy mas menos favor puedes puede podria pueden dime dame ver saber hola gracias "
    "libro libros disponible disponibles disponibilidad ejemplar ejemplares catalogo autor tema titulo editorial clave "
    "ubicacion ubicar localizar biblioteca algun alguno alguna algunos algunas existe existen").split())

# Respuestas por defecto por intencion cuando no hay FAQ aplicable (o la intencion no consulta datos).
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
    """Conjunto de tokens para la similitud: primeros 5 caracteres de cada palabra de 3+ letras que no sea de relleno.

    Args:
        texto (str): texto libre.

    Returns:
        set[str]: tokens truncados a 5 caracteres.
    """
    return {t[:5] for t in normalizar(texto).split() if len(t) >= 3 and t not in STOP}


def _dice(a, b):
    """Coeficiente de Dice entre dos conjuntos: 2|A n B| / (|A| + |B|).

    Args:
        a (set): primer conjunto de tokens.
        b (set): segundo conjunto de tokens.

    Returns:
        float: similitud entre 0.0 y 1.0 (0.0 si alguno esta vacio).
    """
    return 2 * len(a & b) / (len(a) + len(b)) if a and b else 0.0


def detectar(texto, faqs):
    """Detecta la intencion del mensaje (D-13): puntaje de palabras clave + similitud con las FAQ.

    Algoritmo (detalle en el docstring del modulo): puntaje[intencion] = suma de pesos de las palabras clave
    encontradas (`PALABRAS`) + 4 x Dice(tokens del texto, tokens de la pregunta) por cada FAQ de esa intencion con
    similitud mayor que 0. Gana el mayor puntaje; el empate lo resuelve el orden de `PALABRAS`. Si el mejor puntaje
    es menor que `UMBRAL` (2.0), o no hay ninguno, la intencion es `no_entendido`.

    Args:
        texto (str): mensaje del usuario (sin normalizar).
        faqs (list[dict]): preguntas frecuentes activas (`model.faqs()`) con `pregunta` e `intencion`.

    Returns:
        tuple[str, float]: `(intencion, puntaje)`; `("no_entendido", 0.0)` si nada coincide y
        `("no_entendido", puntaje)` si el mejor no alcanza el umbral.
    """
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
    """Terminos de busqueda de libros (RF-30): lo citado entre comillas o las palabras que no son de relleno (max. 4).

    Args:
        texto (str): mensaje del usuario.

    Returns:
        list[str]: terminos normalizados (una sola frase si hubo comillas); vacia si no hay titulo/autor/tema.
    """
    m = re.search(r"[\"“«'‘](.{2,}?)[\"”»'’]", str(texto))
    if m:
        return [normalizar(m.group(1))]
    return [t for t in normalizar(texto).split() if len(t) >= 3 and t not in STOP and t not in _NO_TERMINO][:4]


# Palabras de otras intenciones que no deben usarse como termino de busqueda de libro.
_NO_TERMINO = set(normalizar(
    "horario horarios hora multa multas prestamo prestamos renovar renovacion reglas politica quiero busco dias").split())


# ---------------------------------------------------------------- redaccion de respuestas
def _plural(n, uno, varios):
    """Formatea una cantidad con su sustantivo en singular o plural.

    Args:
        n (int): cantidad.
        uno (str): forma singular.
        varios (str): forma plural.

    Returns:
        str: p. ej. `"1 libro"` o `"3 libros"`.
    """
    return f"{n} {uno if n == 1 else varios}"


def _dinero(x):
    """Formatea un monto como pesos mexicanos.

    Args:
        x (Decimal | float | int): monto.

    Returns:
        str: p. ej. `"$12.50 MXN"`.
    """
    return f"${float(x):,.2f} MXN"


def _fecha(d):
    """Formatea una fecha como dd/mm/aaaa.

    Args:
        d (date): fecha.

    Returns:
        str: fecha formateada.
    """
    return d.strftime("%d/%m/%Y")


def _faq(intencion, texto, faqs):
    """Respuesta de la FAQ de la intencion que mas se parece al texto (Dice); sin FAQ usa `FALLBACK`.

    Args:
        intencion (str): intencion detectada.
        texto (str): mensaje del usuario.
        faqs (list[dict]): preguntas frecuentes activas.

    Returns:
        str: texto de respuesta.
    """
    cand = [f for f in faqs if f["intencion"] == intencion]
    if not cand:
        return FALLBACK.get(intencion, FALLBACK["no_entendido"])
    tk = _tokens(texto)
    return max(cand, key=lambda f: _dice(tk, _tokens(f["pregunta"])))["respuesta"]


def _politicas(user):
    """[(descripcion del rol, politica)] del usuario o, sin politica propia (visitante), de todos los roles (RF-32).

    Args:
        user (dict): usuario actual (`current_user()`); un visitante tiene `id_usuario` nulo.

    Returns:
        list[tuple[str, dict]]: pares `(rol, politica_prestamo vigente)`; vacia si no hay politicas vigentes.
    """
    if user.get("id_usuario"):
        cu = circulacion.contexto_usuario(user["id_usuario"])
        if cu["politica"]:
            return [(cu["usuario"]["rol"], cu["politica"])]
    pares = [(r["descripcion"], circulacion.politica_vigente(r["id_rol"])) for r in model.roles()]
    return [(d, p) for d, p in pares if p]


def _linea_politica(rol, p):
    """Redacta una linea con los limites de la politica de prestamo de un rol (dias habiles, libros, renovaciones, multa).

    Args:
        rol (str): descripcion del rol.
        p (dict): politica vigente (`dias_prestamo`, `max_libros`, `max_renovaciones`, `multa_diaria`).

    Returns:
        str: linea de texto.
    """
    return (f"{rol}: {_plural(p['dias_prestamo'], 'día hábil', 'días hábiles')} de préstamo por libro, hasta "
            f"{_plural(p['max_libros'], 'libro', 'libros')} a la vez, {_plural(p['max_renovaciones'], 'renovación', 'renovaciones')} "
            f"y multa de {_dinero(p['multa_diaria'])} por día hábil de retraso y por libro.")


def _explicar(intencion, texto, user):
    """Explica las reglas de prestamo, renovacion, multas o todas (`reglas`), leyendo `politica_prestamo` (RF-32; RN de
    circulacion en core.circulacion). En `multas` agrega la regla de reposicion si el texto menciona perdida o dano.

    Args:
        intencion (str): `prestamo`, `renovacion`, `multas` o `reglas`.
        texto (str): mensaje del usuario.
        user (dict): usuario actual (define de que politica se habla).

    Returns:
        str: explicacion; si no hay politica vigente, indica consultar a un bibliotecario.
    """
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
    """Estatus propio de prestamos: titulo, vencimiento o retraso con multa estimada y renovaciones usadas (RF-31).

    Args:
        user (dict): usuario autenticado (requiere `id_usuario`).

    Returns:
        str: resumen multilinea; indica si la cuenta esta suspendida para nuevos prestamos.
    """
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
    """Estatus propio de multas: adeudos pendientes con monto y prestamos vencidos cuya multa sigue creciendo (RF-31).

    Args:
        user (dict): usuario autenticado (requiere `id_usuario`).

    Returns:
        str: resumen multilinea o aviso de que no hay adeudos.
    """
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
    """Busca libros para la respuesta del asistente (RF-30).

    Args:
        texto (str): mensaje del usuario.

    Returns:
        tuple[str | None, list[dict]]: `(consulta, libros)`; `consulta` es `None` si no hay terminos y cada libro
        trae `id_libro`, `clave`, `titulo`, `disponibles` y `ubicacion` (texto). Maximo `MAX_LIBROS`.
    """
    terminos = terminos_libro(texto)
    if not terminos:
        return None, []
    filas = model.buscar_libros(terminos, MAX_LIBROS)
    libros = [{"id_libro": f["id_libro"], "clave": f["clave"], "titulo": f["titulo"], "disponibles": f["disponibles"],
               "ubicacion": texto_ubicacion(f)}
              for f in filas]
    return " ".join(terminos), libros


def _responder(intencion, texto, user, faqs, previa):
    """Construye la respuesta segun la intencion (sin persistir).

    Reglas: dos `no_entendido` seguidos escalan a `pasar_a_bibliotecario` (RF-33); `buscar_libro`/`ubicacion`
    consultan el catalogo (RF-30); `prestamo`/`renovacion`/`multas`/`reglas` explican la politica (RF-32);
    `estatus_*` requieren sesion (los visitantes no tienen datos propios, D-26; RF-31); el resto usa la FAQ.

    Args:
        intencion (str): intencion detectada.
        texto (str): mensaje del usuario.
        user (dict): usuario actual.
        faqs (list[dict]): preguntas frecuentes activas.
        previa (str | None): ultima intencion del asistente en la conversacion.

    Returns:
        dict: `texto`, `intencion` (posiblemente escalada), `con_bibliotecario` y, segun el caso, `libros` y `enlaces`.
    """
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
    """Indica si el usuario atiende consultas (tiene el permiso `prestamos`, es decir, es bibliotecario).

    Args:
        user (dict): usuario actual.

    Returns:
        bool: `True` si tiene el permiso.
    """
    return has_permission(user, "prestamos")


def _recordadas():
    """Conversaciones de visitante guardadas en la sesion de Flask.

    Returns:
        list[int]: ids de conversacion recordados.
    """
    return list(session.get(SESION_CLAVE, []))


def _es_dueno(conv, user):
    """Indica si el usuario es dueno de la conversacion: por `id_usuario`, o (visitante) por estar en su sesion.

    Args:
        conv (dict): fila `conversacion`.
        user (dict): usuario actual.

    Returns:
        bool: `True` si es el dueno.
    """
    if user.get("id_usuario"):
        return conv["id_usuario"] == user["id_usuario"]
    return conv["id_usuario"] is None and conv["id_conversacion"] in _recordadas()


def _cargar(id_conversacion, user, staff_ok=False):
    """Carga una conversacion verificando propiedad; el bibliotecario puede leer las escaladas si `staff_ok`.

    Args:
        id_conversacion (int): conversacion solicitada.
        user (dict): usuario actual.
        staff_ok (bool): permite acceso a personal con permiso `prestamos` si la conversacion fue escalada.

    Returns:
        dict: fila `conversacion`.

    Raises:
        ApiError: 404 si no existe o el usuario no tiene acceso (no revela existencia ajena).
    """
    conv = model.conversacion(id_conversacion)
    if not conv or not (_es_dueno(conv, user) or (staff_ok and _es_staff(user) and model.va_con_bibliotecario(id_conversacion))):
        raise ApiError("No se encontró la conversación.", 404)
    return conv


def _forma(conv, user):
    """Serializa una conversacion con sus mensajes; el personal ademas recibe los datos del usuario.

    Args:
        conv (dict): fila `conversacion`.
        user (dict): usuario actual.

    Returns:
        dict: `id_conversacion`, `resuelta`, `calificacion`, `con_bibliotecario`, `fecha_inicio`, `mensajes` y, para
        personal, `usuario` (`matricula`, `nombre_completo`) o `None` si es visitante.
    """
    out = {"id_conversacion": conv["id_conversacion"], "resuelta": conv["resuelta"], "calificacion": conv["calificacion"],
           "con_bibliotecario": model.va_con_bibliotecario(conv["id_conversacion"]), "fecha_inicio": conv["fecha_inicio"],
           "mensajes": model.mensajes(conv["id_conversacion"])}
    if _es_staff(user):
        u = conv["id_usuario"] and get_or_404("usuario", "id_usuario", conv["id_usuario"])
        out["usuario"] = {"matricula": u["matricula"], "nombre_completo": u["nombre_completo"]} if u else None
    return out


def enviar_mensaje(data, user):
    """Procesa un mensaje del usuario: valida, abre o continua la conversacion, detecta la intencion, responde y
    persiste ambos mensajes (RF-29..RF-33). Los visitantes tambien pueden conversar (D-26); sus conversaciones se
    recuerdan en sesion (ultimas 20).

    Args:
        data (dict): payload `{texto (1-500), id_conversacion?, canal? ("web" | "movil", por defecto "web")}`.
        user (dict): usuario actual (autenticado o visitante).

    Returns:
        dict: `{id_conversacion, respuesta}` con `respuesta` = `{texto, intencion, con_bibliotecario, libros?, enlaces?}`.

    Raises:
        ApiError: 400 si el payload es invalido; 404 si la conversacion no existe o no es del usuario.
    """
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
    """Devuelve una conversacion con sus mensajes (dueno, o bibliotecario si fue escalada; RF-33).

    Args:
        id_conversacion (int): conversacion solicitada.
        user (dict): usuario actual.

    Returns:
        dict: ver `_forma`.

    Raises:
        ApiError: 404 si no existe o no hay acceso.
    """
    return _forma(_cargar(id_conversacion, user, staff_ok=True), user)


def valorar(id_conversacion, data, user):
    """Registra la opinion del dueno: calificacion 1-5 y, opcionalmente, si su duda quedo resuelta. Una consulta
    escalada y pendiente solo la cierra el bibliotecario (`resolver`), por lo que `resuelta=True` se ignora en ese caso.

    Args:
        id_conversacion (int): conversacion a calificar.
        data (dict): payload `{calificacion (1-5), resuelta?}`.
        user (dict): usuario actual (debe ser el dueno).

    Returns:
        dict: conversacion actualizada (ver `_forma`).

    Raises:
        ApiError: 404 si no existe o no es del usuario; 400 si el payload es invalido.
    """
    conv = _cargar(id_conversacion, user)
    d = validate(data, CALIFICACION)
    valores = {"calificacion": d["calificacion"]}
    # una consulta pendiente solo la cierra el bibliotecario
    if d["resuelta"] is not None and not (d["resuelta"] and model.va_con_bibliotecario(conv["id_conversacion"]) and not conv["resuelta"]):
        valores["resuelta"] = d["resuelta"]
        valores["fecha_fin"] = None
    return _forma(model.valorar(id_conversacion, valores), user)


def consultas_bibliotecario(user, estado=""):
    """Lista las conversaciones escaladas a bibliotecario (permiso `prestamos`; RF-33).

    Args:
        user (dict): usuario actual (el permiso lo valida el controller).
        estado (str): `""` (todas), `pendiente` o `resuelta`.

    Returns:
        list[dict]: `id_conversacion`, `fecha_inicio`, `resuelta`, `ultimo_mensaje` y `usuario` (o `None` si visitante).

    Raises:
        ApiError: 400 si `estado` no es valido.
    """
    if estado not in ("", "pendiente", "resuelta"):
        raise ApiError("Estado inválido.", 400)
    return [{"id_conversacion": r["id_conversacion"], "fecha_inicio": r["fecha_inicio"], "resuelta": r["resuelta"],
             "ultimo_mensaje": r["ultimo_mensaje"],
             "usuario": {"matricula": r["matricula"], "nombre_completo": r["nombre_completo"]} if r["matricula"] else None}
            for r in model.consultas_bibliotecario(estado)]


@audit("asistente_resolver", lambda r: f"Consulta {r['id_conversacion']} resuelta")
def resolver(id_conversacion, data, actor):
    """El bibliotecario responde una consulta escalada y la marca como resuelta (RF-33). Se audita como
    `asistente_resolver`. La respuesta se guarda con el prefijo `[Bibliotecario]`.

    Args:
        id_conversacion (int): consulta a resolver.
        data (dict): payload `{respuesta (1-500)}`.
        actor (dict): bibliotecario que responde.

    Returns:
        dict: conversacion actualizada (ver `_forma`).

    Raises:
        ApiError: 400 si la respuesta es invalida; 404 si la consulta no existe o no fue escalada; 409 si ya estaba resuelta.
    """
    d = validate(data, RESPUESTA)
    conv = model.conversacion(id_conversacion)
    if not conv or not model.va_con_bibliotecario(id_conversacion):
        raise ApiError("No se encontró la consulta.", 404)
    if conv["resuelta"]:
        raise ApiError("La consulta ya fue resuelta.", 409)
    model.agregar_mensaje(id_conversacion, "asistente", "[Bibliotecario] " + d["respuesta"], None)
    return _forma(model.resolver(id_conversacion), actor)
