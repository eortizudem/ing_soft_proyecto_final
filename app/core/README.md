# app/core: ayudas globales del backend

Regla: **los modulos no reimplementan nada de esto**. Capas: `model.py` (datos, usa `repo`), `service.py`
(reglas + esquemas de validacion + `@audit`), `controller.py` (solo HTTP: `body()`, `query_args()`, devuelve el
resultado del servicio). Los modulos nuevos (prestamos, asistente) deben seguir el mismo patron.

## Catalogo

| Modulo | Ayuda | Para que |
|---|---|---|
| `module.py` | `make_blueprint(__name__)`, `register_modules(app, pkg)` | `__init__.py` de modulo de 3 lineas; `create_app` registra solo todo `app/modules/<m>/` |
| `http.py` | `body(strict=False)`, `query_args(spec)`, `ok(data, status, **extra)`, `created(data)` | Entrada/salida HTTP |
| `serializers.py` | `to_json(x)`, `nest(row, key, fields)`, `JSONProvider` | date/datetime -> ISO, Decimal -> float; los controladores devuelven dicts/listas/filas directo |
| `validators.py` | `validate(data, schema, partial=False)`, `Str Email Int Dec Enum Bool Date List` | Validacion declarativa con mensajes en espanol |
| `repo.py` | `fetch_one/fetch_all/execute`, `select`, `build_where`, `get_or_404`, `or_404`, `insert`, `update`, `exists`, `count`, `get_or_create`, `tope` (limite de listados: `select(..., limit=repo.tope(n))`, 500 por defecto, max 2000) | SQL dinamico seguro (`psycopg.sql`) |
| `estado.py` | `toggle_estado(table, pk, id, load=, guard=, extra=)` | Activar/desactivar con guardas |
| `bitacora.py` | `log(id_usuario, accion, detalle)`, `@audit(accion, detail)` | Bitacora |
| `auth.py` | `@login_required`, `@permission_required("p")`, `require_permission("p", user)`, `has_permission`, `current_user` | Acceso |
| `errors.py` | `ApiError(mensaje, status=400, extra=None)`, `ApiError.reglas(motivos)`, `motivo(codigo, msg)`, `exigir(motivos)` | Errores de negocio -> `{"error", **extra}`; reglas incumplidas -> 422 `{"error", "motivos":[{codigo, mensaje}]}` |
| `calendario.py` | `es_habil`, `sumar_habiles(desde, n)`, `habiles_entre(desde, hasta)` | Dias habiles lun-vie (D-03); `habiles_entre(d, sumar_habiles(d, n)) == n` |
| `parametros.py` | `tipo_cambio()`, `presupuesto_mensual()`, `dias_reserva_espera()` | Parametros de entorno (`config.py`): `TIPO_CAMBIO_USD_MXN`, `PRESUPUESTO_MENSUAL_USD`, `ESPERA_DIAS_RESERVA` |
| `errores.py` | `registrar(origen, resumen, id_usuario)`, `dentro_del_limite(cliente)`, `parsear` | Bitacora de errores (accion `error_sistema`, PS-S3-06): 500 del servidor y errores JS; conexion propia, nunca lanza |
| `notificaciones.py` | `enviar(canal, asunto, cuerpo, id_usuario, destino=None)`, `enviar_a_usuario`, `validar_canales`, `parsear`, `CANALES` | lista de avisos simulada en `bitacora` (`notif_<canal>`, D-11) |
| `circulacion.py` | ver abajo | Reglas unicas de prestamo/renovacion/multa/reposicion (RN-01..06, D-24) |
| `app/testing.py` + `conftest.py` | `login`, `client_as`, `make_user`, `make_book`, `make_loan`, `user_payload`, `libro_payload`, fixtures `anon admin alumno alumno2 catalogo comprador bibliotecario docente colaborador login_as` | Pruebas |

## Circulacion (`circulacion.py`): una sola fuente para prestamos, espera, adeudos y asistente

Puras (sin BD): `fecha_vencimiento(fecha_prestamo, dias)`, `dias_retraso(vencimiento, hasta)`, `multa_retraso(dias, tarifa)`,
`esta_vencido(venc, devolucion, hoy)` (D-24), `evaluar_prestamo(**ctx)` y `evaluar_renovacion(**ctx)` (devuelven lista de
motivos; vacia = permitido), `fecha_renovacion`, `limite_reserva`, `valor_reposicion_mxn`, `monto_danio`, `redondear`.
Con BD (solo lectura): `contexto_usuario(id)` (conteos, politica, `suspendido`), `contexto_libro(id, id_usuario)`
(disponibles, reservados), `autorizar_prestamo(id_usuario, id_libro)`, `autorizar_renovacion(id_prestamo)`,
`valor_reposicion(id_libro, tipo_cambio=None)`, `politica_vigente(id_rol)`. Los codigos de motivo son constantes del modulo
(`MULTAS_PENDIENTES`, `LIBRO_NO_DISPONIBLE`...). Convertir a 422: `exigir(r["motivos"])`.
```python
r = circulacion.autorizar_prestamo(u["id_usuario"], id_libro)     # {autorizado, motivos, politica, fecha_vencimiento_estimada...}
exigir(r["motivos"], "No se puede prestar el libro.")             # 422 {"error", "motivos": [...]}
dias = circulacion.dias_retraso(p["fecha_vencimiento"], date.today())
monto = circulacion.multa_retraso(dias, politica["multa_diaria"])
```
Vencido = `fecha_devolucion IS NULL AND fecha_vencimiento < CURRENT_DATE` (nunca confiar en `prestamo.estado`).
Los modulos escriben en sus tablas; este modulo no escribe nada.

## Ejemplos

**Controller** (solo HTTP):
```python
@bp.get("/api/libros")
@login_required
def listar():
    a = query_args({"q": "", "tema": "", "disponibles": False})   # str / bool ("1","true") / int
    return service.listar(current_user(), **a)                     # dict/lista/fila: Flask lo serializa

@bp.post("/api/libros")
@permission_required("catalogo")
def crear():
    return created(service.crear(body(), current_user()))          # 201
```
`body()` devuelve `{}` si el JSON no es un objeto (`body(strict=True)` lanza 400). `ok()` -> `{"ok": true}`;
`ok(user=u)` -> `{"user": u}`.

**Validacion** (esquema en el servicio; solo devuelve las claves del esquema; error = primer campo que falla):
```python
SCHEMA = {
    "clave":  Str("clave", upper=True, pattern=CODE_RE, pattern_msg="La clave debe tener..."),
    "titulo": Str("título", max=200),                       # "Completa el campo título." / "...admite máximo 200..."
    "anio":   Int(1000, 2100, msg="Introduce un año entre 1000 y 2100."),
    "precio": Dec(0, 99999999, places=2, msg="Precio inválido."),
    "tipo":   Enum(("a", "b"), "Selecciona un tipo válido."),      # o Enum(callable, ...) para valores desde BD
    "correo": Email("correo institucional", msg="Correo inválido."),
    "activo": Bool(msg="Debe ser verdadero o falso."),
    "desde":  Date(msg="Fecha inválida."),
    "lineas": List({"cantidad": Int(1, 10, msg="...")}, min=1, msg="Agrega al menos una línea."),
    "nota":   Str("nota", required=False, default=""),
}
data = validate(body, SCHEMA)                  # validate(body, SCHEMA, partial=True): PATCH, omite ausentes
```
Opciones utiles de `Str`: `min`, `strip=False`, `strict=True` (no acepta numeros), `required_msg`, `max_msg`, `min_msg`.
`Enum(..., status=404)` cambia el codigo HTTP.

**Repo** (identificadores validados y comparados con `information_schema`; los valores siempre van como parametros):
```python
row  = repo.insert("libro", {"clave": "X1", "titulo": "T"}, returning="id_libro")   # -> {"id_libro": 9}
repo.update("libro", "id_libro", 9, {"estado": "inactivo"}, returning=None)
libro = repo.get_or_404("libro", "id_libro", 9, "No se encontró el libro.")
repo.exists("usuario", {"matricula": m, "correo": c}, ci=("correo",), any_of=True, exclude=("id_usuario", id_actual))
rows = repo.select(BASE_SQL, {"u.estado": estado, "v.disponibles__gt": 0},        # None / "" se ignoran
                   search=(q, ["u.matricula", "u.nombre"]),                         # unaccent + ILIKE
                   order="u.matricula")                                             # "col [ASC|DESC]"
where, params = repo.build_where({"estado": "activo"}, search=(q, ["titulo"]))      # para consultas propias
```
Operadores de filtro: igualdad, lista (`ANY`), sufijos `__gt __gte __lt __lte __ne`. Los nombres de tabla/columna
vienen **solo del codigo**, nunca de la peticion.

**Estado + bitacora** (servicio):
```python
@audit(lambda u: "usuario_baja" if u["estado"] == "inactivo" else "usuario_reactivar",
       lambda u: f"Cambio de estado de {u['matricula']}")        # detail(resultado) o detail(resultado, args)
def alternar(id_usuario, actor):                                  # el argumento se llama `actor`
    toggle_estado("usuario", "id_usuario", id_usuario, load=obtener,
                  guard=lambda fila, nuevo: ...,                  # lanza ApiError para impedirlo
                  extra={"inactivo": {"fecha_baja": date.today()}, "activo": {"fecha_baja": None}})
    return model.get(id_usuario)
```
`@audit` registra solo si la funcion termino sin error; `log(id_usuario, accion, detalle)` se usa directo cuando
el actor no es un argumento (login, recuperar contrasena, reportes).

**Modulo nuevo**: `app/modules/<m>/__init__.py` = `bp = make_blueprint(__name__)`; crea `model.py`, `service.py`,
`controller.py` (con `from . import bp`) y `tests/test_<m>.py`. No hay que registrar nada.

**Pruebas**: `make_user(rol="alumno")`, `make_book(ejemplares=2)` insertan directo en BD (se limpian al final de la
sesion); `login_as("ADM001", "Admin123")` o los fixtures `admin`, `alumno`, `alumno2`, `catalogo`, `comprador`, `bibliotecario`, `docente`, `colaborador`, `anon`.
`make_loan(id_usuario, id_libro)` crea un prestamo activo (vence en 7 dias naturales; ajusta `fecha_vencimiento` con SQL para casos vencidos). `conftest.py` borra al final de la sesion lo creado en `mensaje, conversacion, lista_espera, adeudo, renovacion, prestamo, ...`.
Tests de funciones que usan la BD fuera de una peticion: `with app.app_context():` y `db.get_conn().commit()` si deben persistir.
Pruebas del core en `app/core/tests/`; ejecutar con `docker compose exec -T web pytest`.

**Compartido entre modulos (no reimplementar)**: `circulacion` (reglas D-24, `contexto_usuario/libro`, `cerrar_prestamo`),
`espera.notificar_espera(id_libro)` (reservado D-19 + aviso; lo llaman prestamos, adeudos y el barrido de espera),
`consultas` (fragmentos SQL `disponibles`, `prestamos_abiertos`, `prestamos_vencidos`, `adeudos_*`; busquedas
`usuario_por_matricula`, `libro_por_clave`) y `serializers.texto_ubicacion`. "Prestamo abierto" = `fecha_devolucion IS NULL`.
