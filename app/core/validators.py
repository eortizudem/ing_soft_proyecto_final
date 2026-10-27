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
    return v is None or (isinstance(v, str) and not v.strip())


class Field:
    """Base: `required` (falta -> error), `default` (si no es requerido y falta), `msg`, `status`."""

    def __init__(self, label=None, *, required=True, default=None, msg=None, status=400):
        self.label, self.required, self.default, self.msg, self.status = label, required, default, msg, status
        self.name = label

    def fail(self, message=None):
        raise ApiError(message or self.msg or "Dato no válido.", self.status)

    def is_blank(self, v):
        return _blank(v)

    def required_message(self):
        return self.msg

    def run(self, value, name):
        self.name = self.label or name
        if self.is_blank(value):
            if self.required:
                self.fail(self.required_message())
            return self.default
        return self.parse(value)

    def parse(self, value):  # pragma: no cover - lo implementan las subclases
        return value


class Str(Field):
    """Texto: strip, upper/lower, largo (min/max) y patron. Mensajes sobrescribibles."""

    def __init__(self, label=None, *, max=None, min=None, pattern=None, pattern_msg=None, upper=False,
                 lower=False, strip=True, strict=False, required_msg=None, max_msg=None, min_msg=None, **kw):
        super().__init__(label, **kw)
        self.max, self.min, self.upper, self.lower, self.strip, self.strict = max, min, upper, lower, strip, strict
        self.pattern = re.compile(pattern) if isinstance(pattern, str) else pattern
        self.pattern_msg, self.required_msg, self.max_msg, self.min_msg = pattern_msg, required_msg, max_msg, min_msg

    def is_blank(self, v):
        return v is None or (isinstance(v, str) and not (v.strip() if self.strip else v))

    def required_message(self):
        return self.required_msg or f"Completa el campo {self.name}."

    def parse(self, value):
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
        super().__init__(label, max=max, lower=True, pattern=EMAIL_RE, pattern_msg=msg, **kw)


class Int(Field):
    """Entero (acepta '12' y 12.0, rechaza bool) con rango opcional; un solo mensaje `msg`."""

    def __init__(self, min=None, max=None, label=None, **kw):
        super().__init__(label, **kw)
        self.min, self.max = min, max

    def parse(self, value):
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
        super().__init__(label, **kw)
        self.min, self.max, self.places = min, max, places

    def parse(self, value):
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
        super().__init__(label, msg=msg, **kw)
        self.values = values

    def required_message(self):
        return f"Completa el campo {self.label}." if self.label else self.msg

    def parse(self, value):
        allowed = self.values() if callable(self.values) else self.values
        value = value.strip() if isinstance(value, str) else value
        if value not in allowed:
            self.fail()
        return value


class Bool(Field):
    """Booleano estricto (true/false JSON)."""

    def is_blank(self, v):
        return v is None

    def parse(self, value):
        if not isinstance(value, bool):
            self.fail()
        return value


class Date(Field):
    """Fecha ISO (AAAA-MM-DD) o date/datetime; rango opcional con min/max (date)."""

    def __init__(self, min=None, max=None, label=None, **kw):
        super().__init__(label, **kw)
        self.min, self.max = min, max

    def parse(self, value):
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
        super().__init__(label, **kw)
        self.item, self.min, self.max = item, min, max

    def is_blank(self, v):
        return v is None

    def parse(self, value):
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
    """Aplica `schema` ({campo: Field}) a `data`; devuelve dict limpio o lanza ApiError (primer error)."""
    data = data if isinstance(data, dict) else {}
    return {name: f.run(data.get(name), name) for name, f in schema.items() if not (partial and name not in data)}
