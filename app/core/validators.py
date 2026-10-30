"""Validacion declarativa: esquemas de campos -> dict limpio o ApiError (mensajes en espanol).

    SCHEMA = {"nombre": Str("nombre completo", max=120), "edad": Int(0, 120, msg="Edad invalida.")}
    data = validate(body, SCHEMA)              # limpia y valida; solo devuelve claves del esquema
    data = validate(body, SCHEMA, partial=True)  # PATCH: omite las claves ausentes
"""
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from .errors import ApiError

CODE_RE = re.compile(r"^[A-Z0-9-]{3,10}$")
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _blank(v):
    """True si `v` es None o texto vacio/solo espacios."""
    return v is None or (isinstance(v, str) and not v.strip())


class Field:
    """Base: `required` (falta -> error), `default` (si no es requerido y falta), `msg`, `status`."""

    def __init__(self, label=None, *, required=True, default=None, msg=None, status=400):
        """Configura el campo base.

        Args:
            label: nombre legible del campo para los mensajes (por defecto, la clave del esquema).
            required: si falta o esta vacio, falla.
            default: valor devuelto cuando no es requerido y falta.
            msg: mensaje de error unico del campo.
            status: codigo HTTP del ApiError.
        """
        self.label, self.required, self.default, self.msg, self.status = label, required, default, msg, status
        self.name = label

    def fail(self, message=None):
        """Lanza ApiError con `message`, o `msg` del campo, o un mensaje generico."""
        raise ApiError(message or self.msg or "Dato no válido.", self.status)

    def is_blank(self, v):
        """True si el valor cuenta como ausente (None o texto vacio)."""
        return _blank(v)

    def required_message(self):
        """Mensaje cuando falta un campo requerido."""
        return self.msg

    def run(self, value, name):
        """Valida un valor: ausente -> error o `default`; presente -> `parse`.

        Args:
            value: valor recibido.
            name: clave del campo en el esquema (se usa si no hay `label`).

        Raises:
            ApiError: con `status` del campo si el valor no es valido.
        """
        self.name = self.label or name
        if self.is_blank(value):
            if self.required:
                self.fail(self.required_message())
            return self.default
        return self.parse(value)

    def parse(self, value):  # pragma: no cover - lo implementan las subclases
        """Convierte y valida `value`; las subclases lo sobrescriben."""
        return value


class Str(Field):
    """Texto: strip, upper/lower, largo (min/max) y patron. Mensajes sobrescribibles."""

    def __init__(self, label=None, *, max=None, min=None, pattern=None, pattern_msg=None, upper=False,
                 lower=False, strip=True, strict=False, required_msg=None, max_msg=None, min_msg=None, **kw):
        """Configura las restricciones del campo de texto.

        Args:
            label: nombre legible para los mensajes.
            max: largo maximo.
            min: largo minimo.
            pattern: regex (str o compilada) que debe cumplir el texto; `pattern_msg` es su mensaje.
            upper: convertir a mayusculas (o `lower` a minusculas).
            strip: quitar espacios laterales.
            strict: solo acepta `str` (rechaza numeros).
            required_msg: mensaje cuando falta; `max_msg`/`min_msg` para el largo.
        """
        super().__init__(label, **kw)
        self.max, self.min, self.upper, self.lower, self.strip, self.strict = max, min, upper, lower, strip, strict
        self.pattern = re.compile(pattern) if isinstance(pattern, str) else pattern
        self.pattern_msg, self.required_msg, self.max_msg, self.min_msg = pattern_msg, required_msg, max_msg, min_msg

    def is_blank(self, v):
        """Con `strip` (por defecto), el texto solo con espacios cuenta como vacio."""
        return v is None or (isinstance(v, str) and not (v.strip() if self.strip else v))

    def required_message(self):
        """Usa `required_msg` o `Completa el campo <nombre>.`."""
        return self.required_msg or f"Completa el campo {self.name}."

    def parse(self, value):
        """Normaliza (strip/upper/lower) y valida largo y patron; devuelve el texto limpio."""
        if self.strict and not isinstance(value, str):
            self.fail(self.min_msg or self.required_message())
        text = str(value)
        text = text.strip() if self.strip else text
        text = text.upper() if self.upper else text.lower() if self.lower else text
        if self.max and len(text) > self.max:
            self.fail(self.max_msg or f"El campo {self.name} admite máximo {self.max} caracteres.")
        if self.min and len(text) < self.min:
            self.fail(self.min_msg or f"El campo {self.name} necesita al menos {self.min} caracteres.")
        if self.pattern and not self.pattern.match(text):
            self.fail(self.pattern_msg or f"El campo {self.name} no tiene un formato válido.")
        return text


class Email(Str):
    """Correo en minusculas con formato basico usuario@dominio.ext."""

    def __init__(self, label="correo", *, max=120, msg="Introduce un correo válido.", **kw):
        """Fija minusculas y el patron `EMAIL_RE`; `msg` es el mensaje de formato invalido."""
        super().__init__(label, max=max, lower=True, pattern=EMAIL_RE, pattern_msg=msg, **kw)


class Int(Field):
    """Entero (acepta '12' y 12.0, rechaza bool) con rango opcional; un solo mensaje `msg`."""

    def __init__(self, min=None, max=None, label=None, **kw):
        """Configura el rango del entero.

        Args:
            min: valor minimo permitido (opcional).
            max: valor maximo permitido (opcional).
        """
        super().__init__(label, **kw)
        self.min, self.max = min, max

    def parse(self, value):
        """Convierte a int (rechaza bool y floats no enteros) y valida el rango."""
        if isinstance(value, bool):
            self.fail()
        try:
            if isinstance(value, float):
                if not value.is_integer():
                    raise ValueError
                n = int(value)
            else:
                n = int(str(value).strip())
        except (ValueError, TypeError):
            self.fail()
        if (self.min is not None and n < self.min) or (self.max is not None and n > self.max):
            self.fail()
        return n


class Dec(Field):
    """Decimal finito con rango y `places` (cuantiza a esos decimales)."""

    def __init__(self, min=None, max=None, places=None, label=None, **kw):
        """Configura el rango y los decimales.

        Args:
            min: valor minimo permitido (opcional).
            max: valor maximo permitido (opcional).
            places: decimales a los que se cuantiza el resultado (opcional).
        """
        super().__init__(label, **kw)
        self.min, self.max, self.places = min, max, places

    def parse(self, value):
        """Convierte a Decimal finito (rechaza bool), valida el rango y cuantiza a `places`."""
        if isinstance(value, bool):
            self.fail()
        try:
            d = Decimal(str(value).strip())
        except InvalidOperation:
            self.fail()
        if not d.is_finite() or (self.min is not None and d < self.min) or (self.max is not None and d > self.max):
            self.fail()
        return d.quantize(Decimal(1).scaleb(-self.places)) if self.places is not None else d


class Enum(Field):
    """Valor dentro de `values` (iterable o funcion que lo devuelve). Con `label`, vacio -> 'Completa...'."""

    def __init__(self, values, msg=None, label=None, **kw):
        """Configura los valores permitidos.

        Args:
            values: iterable de valores permitidos o funcion sin argumentos que lo devuelve (p. ej. consulta a BD).
        """
        super().__init__(label, msg=msg, **kw)
        self.values = values

    def required_message(self):
        """Con `label`: `Completa el campo <label>.`; si no, `msg`."""
        return f"Completa el campo {self.label}." if self.label else self.msg

    def parse(self, value):
        """Valida que el valor (sin espacios laterales si es texto) este en `values`."""
        allowed = self.values() if callable(self.values) else self.values
        value = value.strip() if isinstance(value, str) else value
        if value not in allowed:
            self.fail()
        return value


class Bool(Field):
    """Booleano estricto (true/false JSON)."""

    def is_blank(self, v):
        """Solo None cuenta como ausente (False es un valor valido)."""
        return v is None

    def parse(self, value):
        """Acepta unicamente booleanos JSON."""
        if not isinstance(value, bool):
            self.fail()
        return value


class Date(Field):
    """Fecha ISO (AAAA-MM-DD) o date/datetime; rango opcional con min/max (date)."""

    def __init__(self, min=None, max=None, label=None, **kw):
        """Configura el rango de fechas.

        Args:
            min: fecha minima permitida (date, opcional).
            max: fecha maxima permitida (date, opcional).
        """
        super().__init__(label, **kw)
        self.min, self.max = min, max

    def parse(self, value):
        """Convierte a `date` (ISO, date o datetime) y valida el rango."""
        try:
            if isinstance(value, datetime):
                d = value.date()
            elif isinstance(value, date):
                d = value
            else:
                d = date.fromisoformat(str(value).strip())
        except ValueError:
            self.fail()
        if (self.min and d < self.min) or (self.max and d > self.max):
            self.fail()
        return d


class List(Field):
    """Lista de objetos (item = esquema dict) o de valores (item = Field); min/max de elementos."""

    def __init__(self, item, min=0, max=None, label=None, **kw):
        """Configura el tipo y tamano de la lista.

        Args:
            item: esquema dict (lista de objetos) o `Field` (lista de valores).
            min: minimo de elementos.
            max: maximo de elementos (opcional).
        """
        super().__init__(label, **kw)
        self.item, self.min, self.max = item, min, max

    def is_blank(self, v):
        """Solo None cuenta como ausente (una lista vacia se valida contra `min`)."""
        return v is None

    def parse(self, value):
        """Valida tipo y cantidad de elementos y cada elemento con `item`."""
        if not isinstance(value, list) or len(value) < self.min or (self.max and len(value) > self.max):
            self.fail()
        out = []
        for x in value:
            if isinstance(self.item, dict):
                if not isinstance(x, dict):
                    self.fail()
                out.append(validate(x, self.item))
            else:
                out.append(self.item.run(x, self.name))
        return out


def validate(data, schema, partial=False):
    """Aplica `schema` ({campo: Field}) a `data`; devuelve dict limpio o lanza ApiError (primer error).

    Args:
        data: cuerpo recibido (si no es dict se trata como vacio).
        schema: mapa nombre -> `Field`; solo esas claves llegan al resultado.
        partial: si True (PATCH) omite los campos ausentes en lugar de exigirlos.

    Raises:
        ApiError: primer campo (en orden del esquema) que no valida.
    """
    data = data if isinstance(data, dict) else {}
    return {name: f.run(data.get(name), name) for name, f in schema.items() if not (partial and name not in data)}
