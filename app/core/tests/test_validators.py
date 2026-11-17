"""Pruebas de `core.validators`: cada tipo de campo, mensajes y comportamiento de `validate`."""
from datetime import date
from decimal import Decimal

import pytest

from app.core.excepciones import ApiError
from app.core.validators import Bool, CODE_RE, Date, Dec, Email, Enum, Int, List, Str, validate


def err(schema, data, partial=False):
    """Ejecuta `validate` esperando un ApiError y lo devuelve para inspeccionarlo."""
    with pytest.raises(ApiError) as e:
        validate(data, schema, partial)
    return e.value


def test_texto_obligatorio_etiqueta_y_recorte():
    """Str requerido: usa la etiqueta en el mensaje, quita espacios y respeta el maximo."""
    s = {"nombre": Str("nombre completo", max=5)}
    assert validate({"nombre": "  Ana "}, s) == {"nombre": "Ana"}
    for blank in (None, "", "   "):
        e = err(s, {"nombre": blank})
        assert e.message == "Completa el campo nombre completo." and e.status == 400
    assert err(s, {}).message == "Completa el campo nombre completo."
    assert err(s, {"nombre": "abcdef"}).message == "El campo nombre completo admite máximo 5 caracteres."


def test_texto_etiqueta_por_defecto_es_el_campo_y_convierte():
    """Sin etiqueta se usa el nombre del campo; los valores no texto se convierten a str."""
    assert err({"tema": Str()}, {}).message == "Completa el campo tema."
    assert validate({"n": 12}, {"n": Str()}) == {"n": "12"}


def test_texto_transformacion_patron_y_mensajes_propios():
    """Str aplica mayusculas, patron y mensajes personalizados."""
    s = {"c": Str("clave", upper=True, pattern=CODE_RE, pattern_msg="Mala clave.")}
    assert validate({"c": " ab-1 "}, s) == {"c": "AB-1"}
    assert err(s, {"c": "a!"}).message == "Mala clave."
    assert validate({"c": "AbC"}, {"c": Str(lower=True)}) == {"c": "abc"}
    s = {"p": Str("pwd", min=6, strict=True, min_msg="Corta.", strip=False, required_msg="Falta.")}
    assert err(s, {"p": ""}).message == "Falta."
    assert err(s, {"p": "123"}).message == "Corta."
    assert err(s, {"p": 1234567}).message == "Corta."
    assert validate({"p": " ab cd "}, s) == {"p": " ab cd "}
    assert err({"d": Str("d", max=1, max_msg="Largo.")}, {"d": "ab"}).message == "Largo."


def test_texto_opcional_valor_por_defecto_y_vacio_omite_reglas():
    """Un Str opcional vacio devuelve el defecto sin validar largo ni patron."""
    s = {"d": Str("destinatario", max=3, required=False, default="Tesorería")}
    assert validate({}, s) == {"d": "Tesorería"}
    assert validate({"d": "  "}, s) == {"d": "Tesorería"}


def test_correo():
    """Email se normaliza a minusculas y rechaza formatos invalidos."""
    s = {"correo": Email("correo institucional", msg="Correo mal.")}
    assert validate({"correo": " A@B.CO "}, s) == {"correo": "a@b.co"}
    for bad in ("x", "a@b", "a b@c.co", "@b.co"):
        assert err(s, {"correo": bad}).message == "Correo mal."
    assert err(s, {"correo": "a" * 121 + "@b.co"}).message.startswith("El campo correo institucional admite máximo")


def test_entero_casos_limite():
    """Int acepta '12' y 12.0, rechaza bool/decimales y valida el rango."""
    s = {"n": Int(1, 10, msg="Entero 1-10.")}
    assert validate({"n": "5"}, s) == {"n": 5}
    assert validate({"n": 5.0}, s) == {"n": 5}
    assert validate({"n": 10}, s) == {"n": 10}
    for bad in (None, "", True, False, 5.5, "x", "1.5", 0, 11, [], {}):
        assert err(s, {"n": bad}).message == "Entero 1-10.", bad
    assert validate({"n": 0}, {"n": Int(msg="m")}) == {"n": 0}
    assert validate({}, {"n": Int(required=False, default=7, msg="m")}) == {"n": 7}


def test_decimal_rango_decimales_y_finitud():
    """Dec valida rango, cuantiza a `places` y rechaza valores no finitos."""
    s = {"p": Dec(0, 100, places=2, msg="Precio.")}
    assert validate({"p": "10.555"}, s)["p"] == Decimal("10.56")
    assert validate({"p": 3}, s)["p"] == Decimal("3.00")
    assert validate({"p": 100}, s)["p"] == Decimal("100.00")
    for bad in (None, "", "abc", "NaN", "Infinity", -0.01, 101, True):
        assert err(s, {"p": bad}).message == "Precio.", bad
    assert validate({"p": "100.5"}, {"p": Dec(msg="x")})["p"] == Decimal("100.5")


def test_enum_estatico_funcion_y_etiqueta():
    """Enum acepta valores fijos o de una funcion y usa la etiqueta en el mensaje de requerido."""
    s = {"e": Enum(("a", "b"), "Elige.")}
    assert validate({"e": " a "}, s) == {"e": "a"}
    assert err(s, {"e": "z"}).message == "Elige."
    assert err(s, {}).message == "Elige."
    assert err({"e": Enum(("a",), "Elige.", label="estado")}, {}).message == "Completa el campo estado."
    assert validate({"e": "x"}, {"e": Enum(lambda: ["x"], "m")}) == {"e": "x"}
    assert err({"e": Enum(["a"], "m", status=404)}, {"e": "q"}).status == 404
    assert validate({}, {"e": Enum(["a"], "m", required=False)}) == {"e": None}


def test_booleano_estricto():
    """Bool solo acepta true/false JSON."""
    s = {"b": Bool(msg="Booleano.")}
    assert validate({"b": False}, s) == {"b": False}
    assert validate({"b": True}, s) == {"b": True}
    for bad in (None, "true", 1, 0, "", []):
        assert err(s, {"b": bad}).message == "Booleano.", bad


def test_fecha():
    """Date acepta ISO, date y datetime, y valida el rango."""
    s = {"d": Date(min=date(2020, 1, 1), msg="Fecha.")}
    assert validate({"d": "2021-05-04"}, s) == {"d": date(2021, 5, 4)}
    assert validate({"d": date(2021, 5, 4)}, s)["d"] == date(2021, 5, 4)
    for bad in ("2021-13-01", "hoy", 5, "2019-12-31", None):
        assert err(s, {"d": bad}).message == "Fecha.", bad


def test_lista_de_esquemas_y_valores():
    """List valida listas de objetos (esquema) y de valores, con minimo de elementos."""
    s = {"l": List({"n": Int(1, 5, msg="N.")}, min=1, msg="Lista.")}
    assert validate({"l": [{"n": "2"}]}, s) == {"l": [{"n": 2}]}
    for bad in (None, [], "x", [1], [{"n": 9}], {"n": 1}):
        assert err(s, {"l": bad}).message in ("Lista.", "N."), bad
    assert err(s, {"l": [{"n": 9}]}).message == "N."
    assert validate({"l": ["a", " b "]}, {"l": List(Str("x"), msg="m")}) == {"l": ["a", "b"]}
    assert err({"l": List(Str("x"), max=1, msg="Poco.")}, {"l": ["a", "b"]}).message == "Poco."


def test_validar_solo_claves_del_esquema_parcial_y_no_dict():
    """`validate` devuelve solo claves del esquema, omite ausentes con partial y trata un no-dict como vacio."""
    s = {"a": Str("a"), "b": Int(msg="b")}
    assert validate({"a": "x", "b": 1, "extra": "no", "id": 5}, s) == {"a": "x", "b": 1}
    assert validate({"a": "x"}, s, partial=True) == {"a": "x"}
    assert validate({}, s, partial=True) == {}
    assert err(s, {"a": " ", "b": 1}, partial=True).message == "Completa el campo a."
    assert err(s, None).message == "Completa el campo a."
    assert err(s, [1]).message == "Completa el campo a."


def test_primer_error_sigue_el_orden_del_esquema():
    """El error devuelto es el del primer campo que falla segun el orden del esquema."""
    s = {"a": Str("a"), "b": Str("b")}
    assert err(s, {}).message == "Completa el campo a."
