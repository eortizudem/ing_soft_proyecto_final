# LibriGest · Estándar de código

Reglas para desarrollar en el proyecto y mantener el código consistente en backend, frontend, base de datos, pruebas y scripts. Todas salen del código existente: si una regla y el código no coinciden, se corrige el código o se actualiza este documento en el mismo cambio.

Convención del documento: **Debe** = obligatorio. **No debe** = prohibido. Los ejemplos marcados con ✅ son el patrón correcto y los marcados con ❌ son el error típico.

Documentos relacionados: [`app/core/README.md`](../app/core/README.md) (catálogo de ayudas del backend), [`app/web/js/components/README.md`](../app/web/js/components/README.md) (catálogo de componentes), [`docs/operacion.md`](operacion.md) (operación, accesibilidad, 3 clics) y [`README.md`](../README.md).

## Índice

1. [Principios y restricciones](#1-principios-y-restricciones-que-prevalecen)
2. [Estructura del proyecto y anatomía de un módulo](#2-estructura-del-proyecto-y-anatomía-de-un-módulo)
3. [Backend (Python / Flask)](#3-backend-python--flask)
4. [Base de datos](#4-base-de-datos)
5. [Frontend (JavaScript)](#5-frontend-javascript)
6. [CSS y UI](#6-css-y-ui)
7. [Accesibilidad](#7-accesibilidad-wcag-21-aa-básico)
8. [Pruebas](#8-pruebas)
9. [Rendimiento](#9-rendimiento)
10. [Scripts y operación](#10-scripts-y-operación)
11. [Git](#11-git)
12. [Checklist antes de hacer commit](#12-checklist-antes-de-hacer-commit)

---

## 1. Principios y restricciones que prevalecen

Estas restricciones del equipo prevalecen sobre cualquier documento de requisitos (ver tabla U1..U7 del [README](../README.md#restricciones-del-usuario-prevalecen-sobre-los-documentos-de-requisitos)).

| Tema | Regla |
|---|---|
| Plataforma | **Debe** correr con Docker + PostgreSQL 16 + Flask. **No debe** añadir otros frameworks de servidor. |
| Acceso a datos | **Debe** usar psycopg 3 con SQL explícito (`app/core/db.py`, `app/core/repo.py`). **No debe** usar ORM (SQLAlchemy, Peewee, etc.). |
| Frontend | **Debe** ser lo más ligero posible: JavaScript vanilla (módulos ES nativos) y CSS plano. **No debe** usar React, bundlers, transpiladores, CDNs ni librerías (npm). Fuentes y logos son locales en `app/web/assets/`. |
| Esquema | **Debe** respetar el esquema oficial de **21 tablas**. Solo se permiten adiciones necesarias y documentadas (sección 4). |
| Arquitectura | **Debe** ser MVC modular unificado: cada módulo trae backend, frontend y pruebas en su carpeta (sección 2). |
| Reutilización | **Debe** usar los helpers de `app/core/` y los componentes de `app/web/js/components/`. **No debe** duplicar código: si algo se repite en dos módulos, se sube a `core` o a `components`. |
| Estilos | **Debe** usar solo las clases canónicas y los tokens de `base.css` (sección 6). |
| Idioma | UI, mensajes de error, docstrings, comentarios (JS, CSS, Python y scripts), mensajes de commit, nombres de pruebas y documentación **van en español y con acentos y eñes** (en identificadores se escribe sin acentos). Los identificadores de código también (`prestamo`, `adeudo`, `valor_reposicion`; módulos de `core` como `excepciones.py` y `bitacora_errores.py`; funciones como `alternar_estado`), salvo vocabulario técnico propio de JS/HTTP (`list`, `save`, `render`, `routes`). |
| Palabras simples | La UI usa palabras de uso diario. |
| Términos de biblioteca | **Se conservan** los términos reales del oficio: *adeudo*, *valor de reposición*, *vigencia*, *ejemplar*, *renovación*, *ficha bibliográfica*. |

Palabras simples en la UI, los valores `CHECK` y los nombres de acciones:

| ✅ Usar | ❌ Evitar |
|---|---|
| Cancelar adeudo (`adeudo_cancelar`, estado `cancelado`) | condonar |
| Pasar a bibliotecario (`pasar_a_bibliotecario`) | escalar |
| Consultas para el bibliotecario | incidentes escalados |
| Errores (`error_sistema`) | incidentes |

Otras restricciones transversales:

- **No debe** haber secretos en el repositorio (sección 11). La configuración sale de variables de entorno (`app/config.py`, `.env`).
- La "app" nativa se satisface con la vista web responsiva (rutas `#/movil`, `#/movil/asistente`); no se añade tecnología nativa.
- Integraciones externas (Servicios Escolares, Tesorería, correo, WhatsApp) son **simuladas**: quedan en `bitacora` como avisos (`notif_<canal>`).

---

## 2. Estructura del proyecto y anatomía de un módulo

```text
proyecto_final/
├── docker-compose.yml  Dockerfile  requirements.txt  pytest.ini  conftest.py  .env.example
├── db/                  01_schema.sql (esquema), 02_seed.sql (catálogos y datos base)
├── scripts/             levantar  recrear_db  respaldo  restaurar  medir_rendimiento  cargar_datos_volumen  (_pg: ayudas)
├── docs/                operacion.md  uat.md  estandar_de_codigo.md  requisitos/
└── app/
    ├── __init__.py      create_app(): registra los módulos automáticamente
    ├── config.py        variables de entorno
    ├── seed.py          usuarios y datos demo (idempotente)
    ├── testing.py       utilidades de prueba
    ├── core/            ayudas del backend (+ tests/)
    ├── web/             index.html, css/ (base, components, layout), assets/, js/
    │   └── js/          main.js, core/ (api, router, session, layout, ui, theme, pdf, crud, errores), components/
    └── modules/<m>/     un directorio por módulo
```

### Anatomía de un módulo (`app/modules/<m>/`)

```text
<m>/
├── __init__.py        bp = make_blueprint(__name__)       (no se escribe nada más)
├── model.py           solo SQL, vía app.core.repo / app.core.db
├── service.py         reglas de negocio, validación, bitácora
├── controller.py      solo HTTP (rutas /api/...)
├── tests/test_<m>.py  pruebas de integración contra la BD real
└── web/
    ├── model.js       llamadas a la API
    ├── view.js        HTML puro (datos -> componentes)
    └── controller.js  rutas hash + eventos; exporta `routes`
```

`__init__.py` del módulo (modelo exacto de `usuarios`):

```python
"""Módulo `usuarios`: blueprint Flask de gestión de cuentas (RF-01, RF-03, RF-04). Capa: registro del módulo MVC."""

from app.core.module import make_blueprint

bp = make_blueprint(__name__)
```

Excepciones aceptadas: un módulo sin pantalla no lleva `web/` ni aparece en `MODULES` de `main.js`, y uno sin SQL propio omite `model.py`: el único caso hoy es `errores`, que solo expone `POST /api/errores` y delega la persistencia en `app/core/bitacora_errores.py`. Cualquier otro módulo **debe** traer `model.py` y `web/`. Un módulo puede tener recursos extra (`usuarios/simulado/servicios_escolares.json`).

### Cómo se registra y se sirve

- **Backend:** `register_modules` (`app/core/module.py`) recorre `app/modules/*` e importa cada paquete con `__init__.py` y su `controller.py`, y registra el `bp`. **No debe** registrarse el blueprint a mano en `create_app`.
- **Estáticos:** `make_blueprint` sirve `app/modules/<m>/web/` en **`/m/<m>/`** (p. ej. `/m/usuarios/controller.js`). El shell estático (`index.html`, `css/`, `js/`, `assets/`) se sirve desde `app/web/` en la raíz.
- **Frontend:** a diferencia del backend, el navegador **no** descubre los módulos solos: cada carpeta se lista en `MODULES` de `app/web/js/main.js` (`auth` e `info` van con import estático). `main.js` los importa de forma tolerante: un módulo roto se omite con aviso y nunca rompe el shell.
- **Contenedor:** el código se copia dentro de la imagen (sin volumen). Tras editar, **debe** reconstruirse con `python3 scripts/levantar.py` antes de probar.

### Checklist: crear un módulo nuevo

1. Crear `app/modules/<m>/__init__.py` con `bp = make_blueprint(__name__)`.
2. Crear `model.py`, `service.py`, `controller.py` (con `from . import bp, service`).
3. Si el módulo es una función habilitable por perfil: añadir el permiso `<m>` en `db/02_seed.sql` (`INSERT INTO permiso` y las listas por rol de la matriz `rol_permiso`) y recrear la BD con `python3 scripts/recrear_db.py -y`.
4. Crear `web/model.js`, `web/view.js`, `web/controller.js` y exportar `routes` (`path`, `perm`, `section`, `action`).
5. Añadir `'<m>'` a `MODULES` en `app/web/js/main.js`.
6. Si debe aparecer en el menú: añadir la entrada `['<m>', 'Etiqueta']` a `NAV` en `app/web/js/core/layout.js` (la clave es el permiso y también la ruta). Si tiene títulos de miga propios, usar `EXTRA_TITLES`.
7. Etiquetas de estados/enums nuevos: añadirlas a `LABELS` (y `TONES`) en `app/web/js/components/labels.js`; **no** en el módulo.
8. Crear `tests/test_<m>.py` (sección 8) con permisos, validaciones, reglas y errores.
9. Actualizar la tabla de módulos del `README.md` (endpoints, rutas, permiso) y, si aplica, la matriz de trazabilidad.
10. Verificar: `docker compose exec -T web pytest app/modules/<m>`, `node --check` de cada `.js` y prueba manual en el navegador.

---

## 3. Backend (Python / Flask)

### 3.1 Estilo

- Python 3.12, sangría de 4 espacios, comillas dobles, líneas de hasta ~120 caracteres.
- Nombres en `snake_case`; constantes en `MAYUSCULAS` (`ESTADOS`, `NO_ENCONTRADA`, `SCHEMA_CREAR`); funciones privadas del módulo con prefijo `_` (`_shape`, `_guard_baja`, `_BASE`).
- Un nombre que choca con una palabra reservada o integrada lleva guion bajo final (`model.list_`).
- Mensajes al usuario en español, con tilde y signos de apertura; las claves del JSON, sin tildes (`nombre_completo`, `fecha_vencimiento`).
- Los comentarios y docstrings **deben** llevar tildes (como en `usuarios` y `prestamos`).
- Cada archivo `.py` abre con un docstring de módulo que indica la **capa** y qué cubre (`"""Servicio de usuarios (capa service MVC): ..."""`).

### 3.2 Responsabilidad por capa

| Capa | Debe | No debe |
|---|---|---|
| `model.py` | Solo SQL vía `app.core.repo` (`select`, `insert`, `update`, `exists`, `get_or_create`, `fetch_one`, `fetch_all`, `execute`) y fragmentos de `app.core.consultas`. | Importar `flask.request`, validar, lanzar errores de negocio, registrar bitácora, decidir reglas. |
| `service.py` | Validar con `app.core.validators`, aplicar reglas, coordinar transacciones, `@audit`, notificaciones, lanzar `ApiError`. Las reglas de circulación salen de `app.core.circulacion`. | Tocar `request`/`session`, devolver objetos de Flask, escribir SQL a mano. |
| `controller.py` | Declarar rutas, leer entrada con `app.core.http` (`body`, `query_args`), aplicar el decorador de acceso y delegar en `service`. | SQL, reglas, validación, `try/except` de negocio. |

✅ Controlador (patrón de `usuarios`):

```python
@bp.post("/api/usuarios")
@permission_required("usuarios")
def crear():
    """POST /api/usuarios — alta de cuenta. Payload: ... Respuesta: 201 con la cuenta. Errores: 400 ..."""
    return created(service.crear(body(), current_user()))
```

❌ SQL o reglas en el controlador:

```python
@bp.post("/api/usuarios")
def crear():
    d = request.get_json()                       # usar body()
    db.execute("INSERT INTO usuario ...", ...)   # SQL va en model.py
    if d["rol"] == "admin": ...                  # la regla va en service.py
```

Reglas adicionales:

- **No debe** importarse un módulo desde otro (`from app.modules.prestamos import ...` dentro de `app/modules/adeudos`). Lo compartido se sube a `app/core/` (ya existen `circulacion`, `espera`, `consultas`, `notificaciones`, `calendario`, `parametros`). Las pruebas sí pueden importar `app.modules.<m>.service` para probar funciones directamente.
- **No debe** reimplementarse una regla de negocio (RN-01..RN-06, D-24...): se llama a `core/circulacion` (`autorizar_prestamo`, `autorizar_renovacion`, `dias_retraso`, `multa_retraso`, `valor_reposicion`, `cerrar_prestamo`...). Un módulo escribe en sus tablas; `circulacion` solo lee.
- Los controladores devuelven dicts, listas o filas directamente: `JSONProvider` los serializa. **No debe** llamarse `jsonify` en controladores.
- Un `import` tardío solo se justifica para evitar ciclos y **debe** llevar un comentario (`# import tardio: evita ciclos`).

### 3.3 Errores

- Los errores de negocio **se lanzan** con `ApiError(mensaje, status=400, extra=None)` (`app/core/excepciones.py`); el manejador global responde `{"error": mensaje, **extra}`.
- El mensaje va en español, dirigido al usuario, con la acción a seguir cuando aplique. Los textos repetidos se definen como constante del módulo (`NO_ENCONTRADA = "No se encontró la cuenta."`).
- Para un recurso inexistente **debe** usarse `or_404(fila, mensaje)` o `repo.get_or_404(...)`.
- Reglas incumplidas: **422** con `motivos: [{codigo, mensaje}]`, construido con `motivo(codigo, mensaje)` y lanzado con `exigir(motivos, mensaje)`. Los `codigo` son constantes estables en `MAYUSCULAS` (`MULTAS_PENDIENTES`, `LIBRO_NO_DISPONIBLE`): el frontend y las pruebas dependen de ellos.

| Status | Uso |
|---|---|
| 200 / 201 | Éxito / creación (`created(...)`) |
| 400 | Datos inválidos, duplicados, guardas de la cuenta (valor por defecto de `ApiError`) |
| 401 / 403 | Sin sesión / sin permiso (los lanzan los decoradores de `core/auth`) |
| 404 | Recurso inexistente |
| 409 | Conflicto de estado (p. ej. préstamo ya devuelto) |
| 422 | Reglas de negocio incumplidas, con `motivos` |
| 500 | Error inesperado: lo atrapa `excepciones.register`, lo guarda en bitácora de errores y responde mensaje genérico |

✅ `exigir(r["motivos"], "No se puede prestar el libro.")`   ❌ `return {"error": "no"}, 422`

### 3.4 Validación

La validación vive en el servicio, es **declarativa** y usa `app.core.validators` (`Str`, `Email`, `Int`, `Dec`, `Enum`, `Bool`, `Date`, `List`, `CODE_RE`).

```python
SCHEMA = {
    "matricula": Str("matrícula / nómina", upper=True, pattern=CODE_RE,
                     pattern_msg="La matrícula debe tener de 3 a 10 letras, números o guiones."),
    "correo": Email("correo institucional", msg="Introduce un correo institucional válido."),
    "rol": Enum(model.roles_asignables, "Selecciona un perfil válido.", label="perfil"),
}
SCHEMA_CREAR = {**SCHEMA, "password": Str("contraseña", **_PWD)}      # variantes por composición
data = validate(d, SCHEMA)                                            # PATCH: validate(d, SCHEMA, partial=True)
```

- Un esquema por operación (`SCHEMA_CREAR`, `SCHEMA_EDITAR`, `SCHEMA_POLITICA`), definido a nivel de módulo.
- `validate` solo devuelve las claves del esquema; el primer campo que falla produce el error 400. **No debe** leerse del payload crudo un campo que no esté en el esquema.
- Los mensajes de validación son específicos y en español ("Completa el campo título.", "Introduce un año entre 1000 y 2100.").
- **No debe** validarse con `if` sueltos lo que un esquema puede expresar.

### 3.5 Acceso a datos y seguridad SQL

- Una conexión por petición (`db.get_conn`). `db.init_app` confirma (`commit`) si el status es < 400 y revierte (`rollback`) en caso contrario: **no debe** llamarse `commit()` en código de petición. Solo se confirma a mano fuera de una petición (`with app.app_context(): ... db.get_conn().commit()`).
- **Los valores siempre van como parámetros** (`%s` o dict de `repo`). **No debe** concatenarse ni usarse f-string con datos del usuario.
- Los **identificadores** (tabla, columna, `ORDER BY`) vienen **solo del código**, nunca de la petición, y se construyen con `psycopg.sql`/`repo.ident`. `repo.insert/update` solo aceptan columnas reales (lista blanca de `information_schema`).
- Los f-strings en SQL solo se permiten para incrustar fragmentos propios del código (`consultas.prestamos_abiertos('u')`, constantes de módulo), nunca valores.

✅

```python
repo.select(_BASE, {"r.nombre": rol, "u.estado": estado},          # None / "" se ignoran
            search=(q, ["u.matricula", "u.nombre_completo"]),      # unaccent + ILIKE
            order="u.matricula", limit=repo.tope(limite))
```

❌ `repo.fetch_all(f"SELECT * FROM usuario WHERE nombre = '{nombre}' ORDER BY {orden}")`

- Concurrencia: lo que decide con datos compartidos se bloquea con `FOR UPDATE` dentro de la transacción (ver `prestamos/model.py`).
- Una consulta que **ya existe** en `core/consultas` (disponibles, préstamos abiertos/vencidos, adeudos pendientes/monto, `usuario_por_matricula`, `libro_por_clave`) **debe** reutilizarse.
- **"Préstamo abierto" (D-24)** = `fecha_devolucion IS NULL`; **vencido** = abierto y `fecha_vencimiento < CURRENT_DATE`. La definición única está en `core/consultas` (`ABIERTO`, `VENCIDO`). **No debe** decidirse con `prestamo.estado` (es solo un caché).

### 3.6 Formato de respuestas JSON

- Fechas y fechas-hora en **ISO 8601**; los `Decimal` salen como **número** (lo hace `core/serializers`: `Decimal -> float`). **No debe** formatearse fechas ni importes como texto en el backend: el formato visible es del frontend (`components/format.js`).
- Claves en `snake_case` y sin tildes. Objetos relacionados se anidan con `nest(row, "usuario", [...])` en una función `_shape` del servicio, no en el controlador.
- Éxito sin datos: `ok()` → `{"ok": true}`; con datos extra: `ok(user=u)`.
- Errores: siempre `{"error": "mensaje"}` (+ `motivos` en 422). Fuera de `/api` se deja la página de error por defecto.
- **Listados con límite:** todo listado grande recibe `limite` y usa `repo.tope(limite)` (500 por defecto, máximo 2000). **No debe** devolverse una tabla completa sin tope.

### 3.7 Rutas, nombres y permisos

| Qué | Regla | Ejemplo |
|---|---|---|
| Recurso | `/api/<recurso>` en **plural**, español | `/api/prestamos`, `/api/usuarios` |
| Detalle | `/api/<recurso>/<int:id_<recurso>>` | `/api/prestamos/<int:id_prestamo>` |
| Acción sobre un recurso | `POST /api/<recurso>/<id>/<accion>` (verbo en infinitivo o sustantivo de la acción) | `/renovar`, `/devolver`, `/estado`, `/pago`, `/cancelar` |
| Acción sin id | `POST /api/<recurso>/<accion>` | `/api/prestamos/validar`, `/api/usuarios/importar` |
| Crear / editar | `POST` / `PUT` | `POST /api/usuarios`, `PUT /api/usuarios/<id>` |
| Borrar | `DELETE` (solo si el diseño lo pide) | `DELETE /api/espera/<id>` |
| Función del controlador | Verbo corto en español | `listar`, `obtener`, `crear`, `actualizar`, `alternar` |
| Función del servicio | Misma idea; `alternar` para el cambio de estado | `service.alternar(id, actor)` |
| Función del modelo | `list_`, `get`, `insert`, `update`, `find_*`, `count_*` | `model.list_(...)` |

- Cada ruta lleva **un** decorador de acceso: `@permission_required("<permiso>")` (401/403) o `@login_required` (solo sesión). Una ruta pública es excepción deliberada (login, `health`, FAQ) y **debe** comentarse. Reglas por rol más finas se resuelven en el servicio con `require_permission(permiso, user)`.
- El nombre del permiso es el del módulo (`prestamos`, `usuarios`, `adeudos`...) y coincide con `perm` de la ruta del frontend y con la clave en `NAV`.
- El argumento que identifica a quien actúa se llama `actor`: así lo detecta `@audit`.
- Se sigue un único estilo de ruta por recurso: los segmentos de URL son una palabra en español; si hace falta un nombre compuesto se usa `snake_case`, igual que los valores de dominio (`/api/tipo_cambio`, `/api/reportes/con_adeudos`). **No debe** usarse kebab-case.

### 3.8 Bitácora y notificaciones

- Toda operación que cambia datos y tiene un actor **debe** auditarse con `@audit(accion, detalle)` en la función de servicio (se registra solo si la función terminó sin error). Usar `log(id_usuario, accion, detalle)` solo si el actor no es un argumento (login, recuperación, reportes).
- La `accion` se escribe en `snake_case` con la forma `<entidad>_<verbo>` (`usuario_crear`, `usuario_editar`, `adeudo_cancelar`) y cabe en 40 caracteres; el detalle, en 200.
- Los avisos (correo, WhatsApp, Servicios Escolares, Tesorería) se envían con `core/notificaciones.enviar(...)` / `enviar_a_usuario(...)`; quedan en `bitacora` con acción `notif_<canal>` (D-11). **No debe** haber envíos reales.
- Los errores 500 y los de JavaScript se registran con `core/bitacora_errores.registrar(...)` (acción `error_sistema`); esa función nunca lanza.

### 3.9 Configuración

- Toda configuración sale de variables de entorno, centralizada en `app/config.py` (`Config`). Una variable nueva **debe** añadirse a: `config.py` (con valor por defecto), `.env.example`, `docker-compose.yml` y la tabla "Variables de entorno" del `README.md`.
- Los parámetros de negocio se leen con `app/core/parametros.py` (`tipo_cambio()`, `presupuesto_mensual()`, `dias_reserva_espera()`), **no** con `os.environ` en un módulo.
- Valores por defecto de desarrollo permitidos; **nunca** credenciales reales. `SECRET_KEY` se cambia en cualquier entorno que no sea de desarrollo.

### 3.10 Docstrings y documentación de endpoints

- Todo módulo, función, clase y método (también los internos y los decoradores anidados) lleva docstring **en español**, estilo Google: resumen en una línea, detalle opcional, y `Args:`, `Returns:`, `Raises:` cuando aplican.
- Se citan las referencias de requisitos que implementa: `RF-xx`, `RN-xx`, `D-xx`, `RNF-xx`, `PS-...`.
- Cada endpoint **debe** documentarse en el docstring de su función de controlador con: método y ruta, permiso, parámetros (`Query:` / `Payload:` / `Body:`), respuesta y errores.

✅

```python
@bp.get("/api/usuarios/<int:id_usuario>/historial")
@permission_required("usuarios")
def historial(id_usuario):
    """GET /api/usuarios/<id_usuario>/historial — historial (RF-04). Respuesta: prestamos, renovaciones,
    adeudos, espera y bitacora. Errores: 404.
    """
    return service.historial(id_usuario)
```

✅ Servicio:

```python
def obtener(id_usuario):
    """Obtiene una cuenta o falla si no existe.

    Args:
        id_usuario: Identificador de la cuenta.

    Returns:
        Dict de la cuenta.

    Raises:
        ApiError: 404 si no existe.
    """
    return or_404(model.get(id_usuario), NO_ENCONTRADA)
```

### 3.11 Modelos de lenguaje (IA)

- Toda llamada a un LLM **debe** pasar por `app/core/ia.py` (`ia.disponible()`, `ia.chat(sistema, mensajes)`); **no debe** haber `urllib`/`requests` hacia Ollama ni otro proveedor en un módulo, ni dependencias nuevas para eso.
- **Debe** haber siempre un plan B sin IA: se captura `ia.IAError` (desactivada, sin conexión, tiempo agotado, respuesta vacía) y se responde con la lógica de reglas, marcando el origen (`fuente: "ia" | "reglas"`). La app **debe** funcionar con `ASISTENTE_IA=0` y sin el contenedor `ollama`.
- **No debe** enviarse al modelo información de otros usuarios: el contexto sale de consultas filtradas por el `id_usuario` de la sesión (los visitantes no tienen datos propios). El texto del usuario va **solo** en el rol `user`; el contexto va en el mensaje de sistema como datos, y el modelo no tiene herramientas ni acceso a la base.
- **Debe** verificarse la respuesta antes de mostrarla (cifras y títulos respaldados por el contexto) y limitarse su longitud; las decisiones de negocio (paso a bibliotecario, permisos, montos) **no** las toma el modelo.
- Las pruebas **no** usan un Ollama real: se reemplaza `ia.chat`/`ia.disponible` por un falso; `conftest.py` desactiva la IA por defecto. Una prueba de integración con el modelo real se omite si no está disponible.

---

## 4. Base de datos

- El esquema oficial (21 tablas) está en `db/01_schema.sql`; los catálogos y datos base, en `db/02_seed.sql`. Se aplican en orden alfabético al crear el volumen de PostgreSQL.
- **No debe** renombrarse ni eliminarse ninguna tabla ni columna del diseño oficial.
- **Cambios solo aditivos y necesarios.** Cada adición **debe** llevar, en el SQL, el comentario `-- Adición al diseño (S-n): motivo (RF/RN/D)` junto al cambio y una línea en la lista "ADICIONES AL DISEÑO OFICIAL" del encabezado de `01_schema.sql`. **No se agregan tablas** nuevas sin acuerdo del equipo.
- Cada tabla lleva `COMMENT ON TABLE <t> IS '[S1|S2|S3] ...'` (el prefijo es el sprint) y un comentario de línea sobre su `CREATE TABLE`.
- Convenciones del esquema: PK `id_<tabla>` con `GENERATED BY DEFAULT AS IDENTITY`; FK `ON DELETE RESTRICT` (salvo detalles que dependen de su padre: `CASCADE`); índice `idx_*` sobre cada FK; estados con campo (`estado`, `activa`) en lugar de borrado físico; tablas y columnas en `snake_case`, español, sin tildes.
- **Enumeraciones:** se modelan como `VARCHAR(n)` + `CHECK (col IN (...))`, no como tipos `ENUM`. Los valores los define el equipo y usan palabras simples (sección 1). Al añadir un valor: actualizar el `CHECK`, `LABELS`/`TONES` en `labels.js` y los esquemas `Enum(...)` del servicio.
- Un cambio al esquema **debe** reflejarse en: `db/01_schema.sql`, `scripts/recrear_db.py` (lista `TABLAS`, si cambian las tablas), `conftest.py` (`_TABLAS`, si las pruebas crean filas en ellas) y la documentación.
- La **semilla** se divide así: catálogos, políticas, libros y FAQ en `db/02_seed.sql`; usuarios con hash y datos demo de circulación en `app/seed.py`. `app/seed.py` **debe** ser idempotente (`seed_if_empty`, puede correr varias veces). `02_seed.sql` no contiene contraseñas ni hashes.
- Para volver al estado demo: `python3 scripts/recrear_db.py -y`. **No debe** editarse la BD de un entorno a mano para "arreglar" datos de demostración.
- Los cálculos de negocio (vencido, abierto, adeudo pendiente) se definen una vez en `core/consultas` (sección 3.5); no se repiten como SQL propio en cada módulo.

---

## 5. Frontend (JavaScript)

### 5.1 Estilo

- JavaScript moderno, módulos ES nativos (`import`/`export`), sin transpilación. Sangría de 2 espacios, comillas simples, punto y coma.
- `camelCase` para funciones y variables (`listPage`, `syncPreview`, `emptyUser`), `MAYUSCULAS` para constantes (`LIST_LIMIT`, `MODULES`). Los **campos que vienen de la API** conservan el `snake_case` del backend (`u.nombre_completo`).
- Funciones flecha para utilidades de una expresión (`export const list = (...) => ...`); `function` declarada para handlers de ruta y funciones con varias sentencias.
- **Imports absolutos** desde la raíz del sitio, nunca rutas relativas largas: `/js/core/api.js`, `/js/components/index.js`, `/m/<m>/controller.js`. Solo se usa `./model.js` y `./view.js` dentro del propio módulo.
- Los componentes se importan **siempre** de `/js/components/index.js`, no de cada archivo.
- Sin `console.log`; `console.warn` solo para módulos que no cargan (`main.js`).
- Sin variables globales en `window`, sin `onclick=` en el HTML, sin `eval`, sin `innerHTML` con texto sin escapar.

### 5.2 Capas

| Archivo | Debe | No debe |
|---|---|---|
| `model.js` | Solo habla con la API a través de `api` (`/js/core/api.js`): `api.get/post/put/delete`, `query({...})`, `encodeURIComponent(id)`. Normaliza el cuerpo (`trim`) y define valores por defecto de formularios (`emptyUser`). | `fetch` directo, DOM, HTML, toasts. |
| `view.js` | Funciones **puras** (datos → HTML) que usan componentes y la plantilla `html`. | `fetch`, `document`, eventos, estado mutable. |
| `controller.js` | Define las rutas, pide datos al modelo, pinta con la vista (`ctx.render`) y conecta eventos con las ayudas de `core/crud.js` y de componentes. Exporta `routes`. | Armar HTML a mano, `fetch`, lógica de negocio. |

✅ `model.js`

```js
/** @module modules/usuarios/model — llamadas a la API `/api/usuarios` y utilidades de datos para el módulo de usuarios */
import { api, query, LIST_LIMIT } from '/js/core/api.js';

export const list = ({ q = '', rol = '', estado = '' } = {}) => api.get('/usuarios' + query({ q, rol, estado, limite: LIST_LIMIT }));
export const alternar = (id) => api.post(`/usuarios/${encodeURIComponent(id)}/estado`);
```

✅ `controller.js` (rutas y listado)

```js
const filters = { q: '', rol: '', estado: '' };      // a nivel de módulo: los filtros sobreviven a la navegación

async function list(params, ctx) {
  await listPage(ctx, { markup: view.listPage(roles, filters), filters, load: model.list,
                        render: (users) => view.rows(users, map), summary: view.summary });
}

export const routes = [
  { path: 'usuarios', perm: 'usuarios', section: 'usuarios', action: list },
  { path: 'usuarios/:id', perm: 'usuarios', section: 'usuarios', action: detail },
];
```

### 5.3 Plantilla `html` y escape

- `html\`...\`` (`/js/core/ui.js`) **escapa** todo valor interpolado salvo los que ya son `Safe` (resultado de otro `html\`\``, de un componente o de `raw()`); los arrays se unen; `false`/`null`/`undefined` no se renderizan.
- **No debe** concatenarse HTML con `+` ni plantillas de texto normales con datos del usuario.
- `raw(...)` solo con contenido propio y confiable, nunca con datos de la API o del usuario.
- Para ocultar por permiso se usa `when: can('perm')` en el componente (`btn`) o un `${cond && html\`...\`}`.

✅ `` html`<p class="muted">${u.nombre_completo}</p>` ``   ❌ `` `<p>${u.nombre_completo}</p>` `` (sin escape)

### 5.4 Componentes y ayudas: úsalos, no los reescribas

Todo el marcado repetible vive en `app/web/js/components/` (catálogo en su README). **No debe** escribirse markup propio de tablas, formularios, toolbars, badges, tarjetas, modales, detalles ni chat.

| Necesito | Uso |
|---|---|
| Página con título/acciones | `page({ title, desc, actions, body })` |
| Botón o enlace | `btn({ label, href \| action, data, variant: 'primary' \| 'danger' \| 'link', when })` |
| Tabla | `dataTable({ rows, columns, empty })` (columnas `{ label, key }` o `{ label, render }`) |
| Búsqueda y filtros | `toolbar({ search, filters })` + `resultsPanel()`; enlace en el controlador con `listPage` |
| Formulario | `formView({ id, fields, actions })`, `submitButton`; enlace con `editPage` o `bindForm` |
| Detalle | `detailView({ title, sub, badge, items, actions })` |
| Estados | `statusBadge(tipo, valor)`, `badge`, `emptyState`, `notice` |
| Confirmación | `confirmAction({ title, message, confirmLabel })` → `Promise<boolean>`; baja/reactivar con `bindAlternar` |
| Botones `data-action` | `onAction(root, { nombre: handler })` (deshabilita el botón mientras corre y muestra errores) |
| Recibo, medidor, chat | `receiptBlock` + `printHtml`/`core/pdf.js`, `meter`, `chatPanel`/`bindChat` |

Reglas:

- **Etiquetas de enumeraciones** (estado, tipo, canal...) solo en `components/labels.js` (`LABELS`, `TONES`); se usan con `label()`, `labelItems()`, `statusBadge()`. **No debe** haber mapas `{ activo: 'Activo' }` locales en un módulo.
- **Formato** de dinero, fechas, número, ubicación, persona y libro solo con `components/format.js` (`money`, `usd`, `number`, `date`, `datetime`, `today`, `location`, `person`, `book`, `count`). **No debe** haber `toLocaleString`, `Intl` ni `new Date(...).toLocale...` en los módulos.
- Si falta un componente o una etiqueta: se **añade** a `components/` (con su CSS canónico y su entrada en el README de componentes), no se improvisa en el módulo. Cuando un trabajo no puede tocar `labels.js`, se avisa en el informe en lugar de duplicar.
- Las primitivas de bajo nivel (`html`, `raw`, `attrs`, `$`, `$$`, `toast`, `showError`, `setFlash`) vienen de `core/ui.js`.

### 5.5 Router, sesión y permisos

- Cada ruta es `{ path, perm, section, action(params, ctx) }`, y opcionalmente `roles` (nombres de rol). `path` usa `:param` (`'usuarios/:id/editar'`); las rutas literales tienen prioridad sobre las parametrizadas.
- `perm` es **obligatorio** en toda ruta de gestión y es el permiso de backend; el servidor sigue siendo la autoridad (los permisos se validan siempre en el servidor, el frontend solo oculta).
- `ctx.query` contiene los parámetros de `#/ruta?a=b` ya parseados. `ctx.render(html)` devuelve el `<main>` o `null` si la navegación quedó obsoleta: **debe** comprobarse `if (!main) return;` cuando se usa directamente.
- Enlaces internos con `btn({ href: 'ruta' })` (genera `#/ruta`); navegación por código con `go('ruta')` de `core/router.js`. **No debe** escribirse `href="#/..."` a mano.
- Las entradas del menú solo aparecen si el usuario tiene el permiso **y** hay una ruta registrada con ese nombre.
- Una ruta puede aceptar permiso(s) múltiples (`perm: ['a', 'b']`: basta uno).

### 5.6 Errores en el frontend

- Las llamadas a `api` lanzan `Error` con `message`, `status`, `data` y los campos del JSON (`err.motivos` en 422). `listPage`, `editPage`, `bindForm`, `onAction` y `bindAlternar` ya capturan y muestran el error; en código propio se usa `showError(err)`, que lista los `motivos`.
- **No debe** usarse `alert()` ni `console.error` como manejo de errores.
- Un error de una llamada **secundaria** no debe romper la pantalla: se degrada con valor por defecto (`model.historial(id).catch(() => empty)`; `roles()` devuelve `[]` ante error).
- Los errores de JavaScript no capturados se reportan solos (`core/errores.js`, máximo 5 por carga).
- Éxito de una acción: mensaje con `setFlash(...)` (lo hacen `editPage` y `bindAlternar`) o `toast(...)`; mensajes cortos y en español.

### 5.7 JSDoc

- Todo archivo abre con `/** @module modules/<m>/<capa> — descripción */` (`core/<archivo>` y `components/<archivo>` para los compartidos).
- Toda función exportada y todo handler llevan JSDoc con descripción y `@param {tipo} nombre - texto` y `@returns {tipo} texto` (y `@throws`/`@example` cuando ayudan). En `model.js` se indica además el endpoint que llama y el permiso.
- Constantes de módulo y variables de estado, con `/** @type {...} */`.

```js
/**
 * Historial del usuario (RF-04). Llama a GET /api/usuarios/:id/historial.
 * @param {number|string} id - Identificador de la cuenta.
 * @returns {Promise<{prestamos: Object[], renovaciones: Object[], adeudos: Object[], espera: Object[], bitacora: Object[]}>}
 */
export const historial = (id) => api.get(`/usuarios/${encodeURIComponent(id)}/historial`);
```

---

## 6. CSS y UI

Hay exactamente tres hojas, cargadas desde `index.html` en este orden: `css/base.css` (tokens, fuentes, reset), `css/components.css` (componentes canónicos) y `css/layout.css` (shell, sidebar, páginas, impresión).

- **Sin CSS por módulo.** **No debe** crearse un `.css` dentro de `app/modules/<m>/web/`. Si un módulo necesita un estilo nuevo y reutilizable, se añade la clase canónica a `components.css` (o `layout.css` si es estructura) con su componente en `components/`.
- **Sin estilos en línea:** ni `style="..."` en el HTML generado ni `element.style.x = ...` para apariencia. Solo se alternan clases o el atributo `hidden`.
- **Solo tokens de `base.css`**, nunca valores sueltos:

| Tema | Tokens |
|---|---|
| Espaciado (márgenes, `gap`, `padding`) | `--space-1` (4px) a `--space-8` (64px) |
| Radios | `--radius` (8px), `--radius-lg` (14px) |
| Altura de controles | `--control-height` (44px) |
| Borde / foco | `--border`, `--ring` |
| Color | `--primary`, `--dark`, `--accent`, `--bg`, `--surface`, `--soft`, `--text`, `--muted`, `--line`, `--good`/`--good-bg`, `--warn`/`--warn-bg`, `--bad`/`--bad-bg`, `--info-bg` |
| Tipografía | `--font`, `--mono` |
| Layout | `--page-x`, `--page-max` |

✅ `padding:var(--space-4);`   ❌ `padding:15px;`, `color:#c00;`

(Los únicos valores literales aceptados están en `@media print` y en sombras del shell.)

- **Clases canónicas** (las que generan los componentes): `.page`, `.page-header`, `.page-actions`, `.toolbar`, `.field`, `.form`, `.form-grid`, `.form-actions`, `.card`, `.card-list`, `.grid`, `.table-wrap`, `.detail-grid`, `.detail-item`, `.actions`, `.row-actions`, `.btn`, `.badge`, `.notice`, `.empty`, `.modal`, `.meter`, `.chat`, `.receipt`, `.stack`, `.muted`, `.sr-only`. **No debe** inventarse una variante (`.my-table`, `.tabla-prestamos`); se usa la canónica o se amplía el componente.
- **Controles** (inputs, selects, textareas, botones): fondo **blanco**, borde `var(--border)`, altura mínima **44 px** (`--control-height`) para que sean fáciles de pulsar.
- **Formato del archivo CSS:** una propiedad por línea, sin espacio tras `:` (`margin:0;`), una regla por bloque, comentarios de sección `/* ---- Tablas ---- */`.
- **Responsive:** la interfaz **debe** verse y operarse sin desbordar horizontalmente a **390 px** de ancho (y hasta 320 px). Las tablas van dentro de `.table-wrap` (scroll propio). Los puntos de corte existentes son `1100px` y `760px`; **no debe** añadirse otro sin motivo.
- **Impresión:** lo imprimible se inyecta en `#print-root` (`printHtml`) y se estiliza en `@media print` de `layout.css` (`#print-root .receipt`, tablas, `h1`). **No debe** crearse otra mecánica de impresión; los PDF salen de `core/pdf.js`.
- **Tema:** el color y el logo del usuario los aplica `core/theme.js`; **no debe** fijarse un color de marca en el CSS de un módulo.
- **Fuentes y logos** son locales (`/assets/roboto-*.woff2`, `logo.svg`). **No debe** enlazarse nada externo (CDN, Google Fonts).

---

## 7. Accesibilidad (WCAG 2.1 AA básico)

La lista completa de verificación está en [`docs/operacion.md`](operacion.md) (sección 5). Reglas de desarrollo:

- `<html lang="es">`, enlace "Saltar al contenido" (`.skip`) y **un único `<h1>`** por pantalla (lo genera `page()`).
- Todo campo con `<label for>` (lo hace `formField`); los obligatorios se indican con texto/asterisco, **no solo con color**; los errores de validación usan `aria-invalid` y se asocian al campo.
- Todo botón o enlace tiene **nombre accesible**: texto visible, o `aria-label` si solo es un icono (`menu-toggle`).
- Las imágenes informativas llevan `alt` con texto (`alt="Logo LibriGest"`); las decorativas, `alt=""` o `aria-hidden`.
- **Foco visible** siempre (`:focus-visible` en `base.css`): **no debe** usarse `outline:none` sin un reemplazo.
- Todo se opera con teclado. El modal (`confirmAction`) usa `role="dialog"`, `aria-modal`, `aria-labelledby`, **atrapa el foco** (Tab/Shift+Tab), cierra con Esc y **devuelve el foco** al elemento que lo abrió. Un diálogo nuevo se hace con `confirmAction`, no a mano.
- Mensajes dinámicos en regiones `aria-live`: `#toast` (`role="status"`, `aria-live="polite"`), el registro del chat (`role="log"`, `aria-live="polite"`) y `role="alert"` para errores (`#alert`).
- Los estados no dependen solo del color: toda insignia (`badge`) lleva **texto**.
- **Contraste** de texto ≥ **4.5:1** (≥ 3:1 en texto grande); se usan los colores de los tokens, ya validados.
- Las tablas llevan `<th scope>` y una página utilizable con zoom al 200 %.
- **Regla de 3 clics:** los procesos principales (prestar, devolver, renovar, registrar pago, buscar y ubicar, registrar libro, crear solicitud de compra) **deben** completarse en **máximo 3 clics** desde el inicio, sin contar escritura. Si un cambio de UI añade un clic a uno de ellos, se actualiza la tabla de [`operacion.md`](operacion.md#6-procesos-de-3-clics-rnf-07-d-17) y se justifica.

---

## 8. Pruebas

- Framework: **pytest**, contra la **base de datos real** del contenedor (no hay mocks de BD). Configuración en `pytest.ini` (`testpaths = app/core app/modules`, archivos `test_*.py`, `--import-mode=importlib`).
- **Ubicación:** `app/modules/<m>/tests/test_<m>.py` por módulo y `app/core/tests/test_<ayuda>.py` por ayuda de `core`. Un módulo grande puede partirse en varios archivos `test_<m>_<tema>.py`.
- **Cada regla de negocio y cada error documentado tiene al menos una prueba**: permisos (anónimo → 401, sin permiso → 403), validaciones (400), inexistente (404), conflicto (409), reglas con `motivos` (422, se verifican los `codigo`), caso feliz y bitácora cuando aplica.
- Una prueba es una función `test_<qué_verifica>()` con nombre **en español** y descriptivo (`test_sin_permiso_responde_403`, no `test_permission_403`; sin sufijos de letra como `_f`; los archivos adicionales se nombran por tema: `test_usuarios_historial_y_actualizacion.py`), con docstring de una línea cuando el nombre no basta; sin clases. Helpers locales con prefijo `_` (`_validar`, `_prestar`, `_loan_for`).
- El módulo de pruebas abre con un docstring que lista lo que cubre y las referencias RN/RF/D.

### Fixtures y utilidades (`conftest.py`, `app/testing.py`)

| Utilidad | Uso |
|---|---|
| `app` | Aplicación Flask de la sesión (`create_app()`). |
| `anon` | Cliente sin sesión. |
| `admin` (único fixture de administrador; no hay alias), `alumno`, `alumno2`, `catalogo`, `comprador`, `bibliotecario`, `docente`, `colaborador` | Clientes ya autenticados con las cuentas semilla. |
| `login_as(matricula, password)` | Cliente autenticado con una cuenta concreta. |
| `make_user(rol="alumno")`, `make_book(ejemplares=2)`, `make_loan(id_usuario, id_libro)` | Insertan datos únicos directo en BD. |
| `user_payload(**over)`, `libro_payload(**over)` | Cuerpos válidos para POST. |
| `sql(query, params)` | SQL directo (autocommit) para preparar o verificar datos (p. ej. forzar un préstamo vencido). |
| `monkeypatch`, `tmp_path` | Para fijar fechas (`date.today()`) o archivos simulados. |

```python
def test_sin_permiso_responde_403(alumno, anon):
    assert alumno.get("/api/usuarios").status_code == 403
    assert anon.get("/api/usuarios").status_code == 401
```

- **Datos únicos:** usar `make_*`/`payload` (sufijo aleatorio `uniq()`), **no** matrículas o claves fijas que pueden chocar entre corridas.
- **Limpieza:** el fixture `limpiar_datos` de `conftest.py` borra al terminar la sesión todo lo creado (ids mayores al máximo previo) en las tablas de `_TABLAS`. Si el módulo crea filas en una tabla nueva, **debe** añadirse ahí en el orden que respete las FK. **No debe** una prueba dejar la semilla modificada: lo que altera de la semilla (política, estado de un ejemplar) lo restaura.
- Pruebas de funciones de servicio fuera de una petición: `with app.app_context():` y `db.get_conn().commit()` si deben persistir.
- Cuando un cambio toca `core/`, se corre toda la suite; cuando toca un módulo, al menos la de ese módulo y las que lo consumen.

### Cómo correr

```bash
python3 scripts/levantar.py                         # reconstruye la imagen: el código se copia dentro de ella
docker compose exec -T web pytest                   # toda la suite
docker compose exec -T web pytest app/modules/prestamos
docker compose exec -T web pytest app/core
```

- **JavaScript:** `node --check <archivo>.js` en cada `.js` modificado (no hay build ni pruebas de unidad de JS).
- **UI:** todo cambio de interfaz **debe** probarse en el navegador (Chrome): flujo feliz, error del servidor, estado vacío, teclado, 390 px de ancho e impresión si aplica. Una prueba de pytest que pasa no demuestra que la pantalla funcione.

---

## 9. Rendimiento

- Meta: **percentil 95 ≤ 3 s** por endpoint crítico (RNF-03/05/11/13, D-15).
- Se mide con `python3 scripts/medir_rendimiento.py -n 20 -c 20 --limite 3.0` (sale con código 1 si p95 > 3 s) y `--escritura` para crear préstamo, renovar, devolver y pagar (limpia sus datos).
- Para volumen (≥ 5 000 usuarios, ≥ 10 000 ejemplares, ≥ 20 000 préstamos): `python3 scripts/cargar_datos_volumen.py` crea `librigest_volumen`; procedimiento en [`operacion.md`](operacion.md) (sección 3).
- **Debe** limitarse todo listado (`repo.tope`, `LIST_LIMIT` en el frontend; el frontend envía `limite` y `count(n, noun, LIST_LIMIT)` avisa si el listado está acotado).
- **Debe** evitarse el patrón N+1: los conteos/sumas por fila se resuelven con subconsultas de `core/consultas` en el mismo `SELECT`, no con una consulta por fila.
- Al añadir un endpoint de listado o de reporte, se agrega a `medir_rendimiento.py` y se verifica con datos de volumen.

---

## 10. Scripts y operación

Los scripts de `scripts/` automatizan el stack y se ejecutan en el equipo anfitrión.

- **Solo biblioteca estándar de Python** (sin `pip install`); `python3 scripts/<script>.py`.
- **Multiplataforma** (macOS, Linux, Windows): rutas con `pathlib` y **desde `__file__`** (`RAIZ = Path(__file__).resolve().parent.parent`), nunca desde el directorio actual ni con separadores fijos.
- `subprocess` con **lista de argumentos** (`["docker", "compose", "up", "-d"]`), **no** `shell=True` ni cadenas con datos del usuario.
- Los comandos de Docker usan `docker compose` (Compose v2) con `cwd=RAIZ`.
- Mensajes y `--help` **en español**; errores en `stderr` con el formato `ERROR: <mensaje>` mediante la función `salir(msg, codigo=1)` (`_pg.py` agrupa ayudas comunes; `levantar.py` y `recrear_db.py` definen la suya).
- Cada script abre con un docstring con: propósito, uso (con ejemplos), pasos, **códigos de salida** y, si aplica, una nota de **SEGURIDAD**; cada función lleva docstring con `Args`/`Returns`/`Raises`.
- **Códigos de salida:** `0` correcto, `1` error o cancelación; `2` uso inválido (como en `medir_rendimiento.py`). Se implementa `main()` que devuelve el código y `if __name__ == "__main__": sys.exit(main())`.
- **Acciones destructivas** (borrar o reemplazar datos: `recrear_db.py`, `restaurar.py`, `cargar_datos_volumen.py --eliminar`) **deben** pedir confirmación `[s/N]` (por defecto, no) y ofrecer `-y/--yes` para automatizar. Sin terminal interactiva y sin `-y`, no proceden. Sugieren el respaldo previo (`respaldo.py`).
- Las credenciales de PostgreSQL se leen de `.env` o del entorno (`_pg.py`), nunca van escritas en el script.
- Un script nuevo se documenta en la tabla "Scripts" del `README.md` y, si es operativo, en `docs/operacion.md`.

---

## 11. Git

- **Commits sin atribución:** **no debe** haber líneas `Co-Authored-By`, "Generated with ..." ni marcas de herramientas en el mensaje del commit, ni en PR.
- Mensajes **en español**, en palabras simples, en una línea que diga qué cambió (modo imperativo o infinitivo, como en el historial: "Agregar documentación al código"); cuerpo opcional con el porqué. Un commit = un cambio coherente.
- **No debe** subirse (ya excluido por `.gitignore`): `.env`, `backups/`, `*.dump`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.venv/`, `venv/`, `node_modules/`, `.DS_Store`. Un archivo generado nuevo se añade a `.gitignore` en el mismo cambio.
- **Sin secretos:** ni contraseñas reales, ni `SECRET_KEY` de producción, ni tokens. Los únicos valores de ejemplo viven en `.env.example` y en la semilla demo (contraseñas públicas de demostración).
- **No debe** subirse código comentado, `print`/`console.log` de depuración ni archivos temporales.
- Cambios que afectan a la operación (variables, puertos, scripts) actualizan `README.md`, `.env.example` y `docs/operacion.md` en el mismo commit.

---

## 12. Checklist antes de hacer commit

**General**

- [ ] Respeta las restricciones: sin ORM, sin librerías ni CDNs en el frontend, sin build, sin nuevas tablas.
- [ ] Todo texto visible, mensaje, docstring y comentario está en español, con palabras simples y los términos de biblioteca correctos.
- [ ] No hay código duplicado: se reutilizó `app/core/` y `app/web/js/components/`.
- [ ] No hay secretos ni archivos ignorados en el commit; el mensaje no lleva atribución.

**Backend**

- [ ] `model.py` solo SQL, `service.py` reglas y validación, `controller.py` solo HTTP; sin imports entre módulos.
- [ ] Reglas de circulación tomadas de `core/circulacion` y "abierto/vencido" de `core/consultas` (D-24).
- [ ] SQL parametrizado; identificadores solo desde el código; listados con `repo.tope`.
- [ ] Errores con `ApiError`/`exigir` y el status correcto; 422 con `motivos`.
- [ ] Operaciones con actor auditadas con `@audit`; endpoints y funciones con docstring completo (método, ruta, permiso, payload, respuesta, errores).
- [ ] Variables nuevas en `config.py`, `.env.example`, `docker-compose.yml` y `README.md`.

**Base de datos**

- [ ] Cambio aditivo con `-- Adición al diseño (S-n): motivo`, encabezado de `01_schema.sql` y `COMMENT ON TABLE`.
- [ ] Enumeraciones como `VARCHAR` + `CHECK` con palabras simples; `labels.js` y esquemas `Enum` actualizados.
- [ ] Semilla (`02_seed.sql`, `app/seed.py`) coherente e idempotente; `recrear_db.py -y` funciona.

**Frontend**

- [ ] `model.js` solo API, `view.js` puro, `controller.js` con `routes`; sin `fetch` fuera de `core/api.js`.
- [ ] Sin markup propio de tablas/formularios/toolbars/badges; etiquetas en `labels.js`; formato en `format.js`.
- [ ] Todo valor interpolado pasa por `html` (escapado); `raw()` solo con contenido propio.
- [ ] Módulo nuevo: añadido a `MODULES` (`main.js`) y a `NAV` (`layout.js`) con su permiso.
- [ ] JSDoc con `@module`, `@param`, `@returns`; `node --check` sin errores.

**CSS y accesibilidad**

- [ ] Solo tokens `var(--...)` y clases canónicas; sin `style=` ni CSS por módulo.
- [ ] Controles blancos con borde y ≥ 44 px; sin desbordes a 390 px; impresión correcta si aplica.
- [ ] Labels, nombres accesibles, `alt`, foco visible, contraste ≥ 4.5:1, `aria-live` en mensajes dinámicos.
- [ ] Los procesos principales siguen en ≤ 3 clics.

**Pruebas y operación**

- [ ] Hay pruebas para cada regla y error nuevos; `docker compose exec -T web pytest` pasa completo.
- [ ] El cambio de UI se probó en el navegador (tras `python3 scripts/levantar.py`).
- [ ] Endpoints de listado/reporte nuevos medidos con `scripts/medir_rendimiento.py` (p95 ≤ 3 s).
- [ ] Scripts nuevos: solo biblioteca estándar, rutas desde `__file__`, `[s/N]` y `-y` si son destructivos.
- [ ] README y documentación actualizados (módulos, scripts, variables, trazabilidad).
