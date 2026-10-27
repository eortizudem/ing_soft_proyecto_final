# LibriGest · Biblioteca Ducky

Sistema web de gestión bibliotecaria para la Universidad Ducky (proyecto final de Ingeniería de Software). Cubre el ciclo completo de la biblioteca: usuarios y perfiles, catálogo y ubicación física, compras y recepción, **préstamos, renovaciones y devoluciones**, **lista de espera**, **multas, pagos, pérdida y daño**, **asistente conversacional**, **notificaciones simuladas** y reportes. Todo vive en una base PostgreSQL compartida y los permisos se validan en el servidor.

## Restricciones del usuario (prevalecen sobre los documentos de requisitos)

| # | Restricción | Cómo se cumple |
| --- | --- | --- |
| U1 | Docker + PostgreSQL + Flask; sin otros frameworks ni ORM | Flask 3 + psycopg 3 con SQL explícito (`app/core/db.py`, `app/core/repo.py`) |
| U2 | Frontend ligero: JavaScript vanilla + CSS plano, **sin build, sin bundler, sin CDNs** | Módulos ES nativos servidos por Flask; fuentes y logos locales en `app/web/assets/` |
| U3 | Esquema oficial de **21 tablas**; solo cambios aditivos, necesarios y documentados | Cinco adiciones S-1..S-5, sin tablas nuevas (ver [Base de datos](#base-de-datos)) |
| U4 | MVC modular unificado: cada módulo contiene su backend, su frontend y sus pruebas | `app/modules/<m>/{model,service,controller}.py`, `web/{model,view,controller}.js`, `tests/` |
| U5 | Helpers y componentes compartidos; nada se reimplementa en los módulos | [`app/core/README.md`](app/core/README.md) y [`app/web/js/components/README.md`](app/web/js/components/README.md) |
| U6 | Scripts de operación en Python (solo biblioteca estándar) | `scripts/*.py` |
| U7 | La "app" nativa se satisface con la vista web responsiva | Rutas móviles `#/movil` y `#/movil/asistente`; sin React Native |

## Stack

| Capa | Tecnología |
| --- | --- |
| Contenedores | Docker + Docker Compose (servicios `db` y `web`, `restart: unless-stopped`, healthchecks) |
| Base de datos | PostgreSQL 16 (`postgres:16-alpine`) con extensión `unaccent` |
| Backend | Python 3.12, Flask 3, psycopg 3, gunicorn (2 workers) |
| Frontend | JavaScript vanilla (ESM) y CSS plano |
| Pruebas | pytest contra la base de datos real del contenedor (219 pruebas) |

## Requisitos

- **Docker Desktop** (o Docker Engine con Compose v2), en ejecución.
- **Python 3** en el equipo anfitrión, solo para `scripts/`.
- Puerto **8000** libre.

## Inicio rápido

```bash
python3 scripts/levantar.py
```

Abre <http://localhost:8000> e inicia sesión con una [cuenta demo](#cuentas-de-demostración). El script crea `.env` desde `.env.example` si falta, construye la imagen, levanta los contenedores, espera a `/api/health` e imprime las credenciales. En el primer arranque PostgreSQL aplica `db/01_schema.sql` y `db/02_seed.sql`, y la aplicación completa la semilla demo (`app/seed.py`).

> El código de `web` se copia dentro de la imagen (no hay volumen). Tras editar código, vuelve a ejecutar `python3 scripts/levantar.py` antes de probar.

## Scripts

| Script | Para qué | Opciones |
| --- | --- | --- |
| `scripts/levantar.py` | Construye y levanta los contenedores | `--no-build`, `--logs`, `--down` |
| `scripts/recrear_db.py` | Recrea la BD y la siembra (**destruye los datos**) | `-y/--yes`, `--sin-semilla` |
| `scripts/respaldo.py` | Respaldo `pg_dump -Fc` en `backups/` | `--salida DIR`, `--db NOMBRE`, `--usuario U` |
| `scripts/restaurar.py` | Restaura un respaldo o lo verifica | `archivo.dump`, `--db`, `--usuario`, `-y/--yes`, `--verificar` |
| `scripts/medir_rendimiento.py` | Mide p50/p95 de los endpoints críticos | `--url`, `-n`, `-c/--concurrentes`, `--limite`, `--usuario`, `--clave`, `--escritura` (+ `--db`) |
| `scripts/cargar_datos_volumen.py` | Carga el dataset de volumen de D-15 (≥ 5 000 usuarios, ≥ 10 000 ejemplares, ≥ 20 000 préstamos) en la BD aparte `librigest_volumen` | `--db`, `--usuarios`, `--ejemplares`, `--prestamos`, `--eliminar`, `-y` (la BD principal solo con confirmación) |

```bash
python3 scripts/levantar.py --no-build --logs      # sin reconstruir y siguiendo logs
python3 scripts/levantar.py --down                 # detiene (los datos quedan en el volumen pgdata)

python3 scripts/recrear_db.py -y                   # vuelve al estado demo
python3 scripts/recrear_db.py -y --sin-semilla     # solo esquema

python3 scripts/respaldo.py                        # backups/librigest_YYYYmmdd_HHMMSS.dump (+ .conteos)
python3 scripts/restaurar.py backups/<archivo>.dump --verificar   # restaura en BD temporal y compara conteos
python3 scripts/restaurar.py backups/<archivo>.dump -y            # restaura sobre la BD (reemplaza datos)

python3 scripts/medir_rendimiento.py -n 20 -c 20 --limite 3.0     # sale con código 1 si p95 > 3 s
python3 scripts/medir_rendimiento.py --escritura                   # además mide crear préstamo, renovar, devolver y pagar (limpia sus datos)
python3 scripts/cargar_datos_volumen.py                            # crea y llena librigest_volumen (procedimiento completo: docs/operacion.md, sección 3)
```

`recrear_db.py` borra el esquema `public`, aplica todos los `db/*.sql` en orden (con `--sin-semilla` omite los que contienen "seed"), ejecuta `python -m app.seed` en el contenedor `web` e imprime el conteo por tabla. Los scripts de `db/` solo corren automáticamente con el volumen `pgdata` vacío; `docker compose down -v` + `levantar.py` también reinicia desde cero.

## Cuentas de demostración

La semilla (`app/seed.py`) crea datos de circulación que ejercitan cada regla. Los permisos de cada perfil se editan en **Perfiles** (admin).

| Perfil | Matrícula | Contraseña | Qué probar |
| --- | --- | --- | --- |
| Administrador | `ADM001` | `Admin123` | Todo. Editar políticas (`#/politicas`), cancelar un adeudo, cambiar permisos en Perfiles, importar o actualizar la lista de alumnos, ver historial de un usuario |
| Bibliotecario | `BIB001` | `Biblioteca123` | Prestar (`#/prestamos/nuevo`), renovar, devolver, registrar pago de Laura, reportar pérdida/daño, resolver consultas para el bibliotecario del asistente, reporte de alumnos con adeudos y su aviso |
| Alumno (María) | `A0512345` | `Alumno123` | Tiene 1 préstamo (LIB001) y está en lista de espera de LIB005: pregunta al asistente "¿qué libros tengo?", abre **Lista de espera** y **Notificaciones** (en ambas ve solo lo suyo) |
| Alumno (Carlos) | `A0512980` | `Alumno123` | Préstamo **vencido** (LIB005): no puede pedir otro (`PRESTAMOS_VENCIDOS`); aparece en reportes de alumnos con adeudos y vencidos. Si BIB001 lo devuelve, se avisa a María |
| Alumno (Laura) | `A0513001` | `Alumno123` | Adeudo de retraso **pendiente** ($20): bloqueada con `MULTAS_PENDIENTES` hasta que se registre el pago |
| Docente | `DOC001` | `Docente123` | 3 préstamos activos (su límite): un cuarto se rechaza con `LIMITE_EJEMPLARES`; renovar LIB005 se rechaza por lista de espera |
| Catálogo | `CAT001` | `Catalogo123` | Fichas, ejemplares (baja/reactivar), etiquetas, pendientes de catalogar, importar CSV, reportes |
| Compras | `COM001` | `Compras123` | Solicitudes con presupuesto mensual, recibir el pedido y su factura (`SOL001` está pendiente) |
| Colaborador | `COL001` | `Colabora123` | Catálogo y compras, reportes y búsqueda; **sin** préstamos |
| Visitante | *(sin cuenta)* | — | Botón **Consultar como visitante**: búsqueda y asistente, sin consultas de estado propio |

Datos sembrados útiles: libros `LIB001`..`LIB007` (`LIB003` y `LIB006` son consulta interna; `LIB007` es **reservado**), `SOL000` (compra recibida, FAC-2026-001, base del precio de reposición) y `SOL001` (pendiente). `LIB005` queda sin ejemplares disponibles (Carlos y DOC001 los tienen).

## Módulos

Permiso = clave de menú = `section` de las rutas. Las pantallas son rutas de hash (`#/…`); las rutas de menú aparecen solo con permiso **y** ruta registrada. "Sesión" = cualquier usuario autenticado.

| Módulo | Funcionalidad | Endpoints principales (`/api/…`) | Pantallas (`#/…`) | Permiso |
| --- | --- | --- | --- | --- |
| `auth` | Login, visitante, logout, recuperación de contraseña | `POST login`, `visitante`, `logout`, `recuperar`, `recuperar/confirmar`; `GET me` | Inicio de sesión, recuperar contraseña | público / sesión |
| `inicio` | Tablero por perfil: personal (conteos, presupuesto) y estado propio | `GET stats` | `inicio` | sesión |
| `usuarios` | Alta, edición, baja lógica, **historial**, **actualización desde Servicios Escolares** con Servicios Escolares, **importación CSV** | `GET/POST usuarios`, `GET/PUT usuarios/<id>`, `POST usuarios/<id>/toggle`, `GET usuarios/<id>/historial`, `GET/POST usuarios/actualización/simulada`, `POST usuarios/importar` | `usuarios`, `usuarios/nuevo`, `usuarios/:id`, `usuarios/:id/editar`, `usuarios/actualizar`, `usuarios/importar` | `usuarios` |
| `perfiles` | Matriz rol-permiso | `GET roles`, `PUT roles/<rol>/permisos/<permiso>` | `perfiles` | sesión / `perfiles` |
| `catalogo` | Fichas, búsqueda sin acentos, ubicación, **ejemplares** (baja con motivo, reactivar), **etiquetas** imprimibles, **pendientes de catalogar**, importación CSV | `GET libros`, `GET libros/<id>`, `POST/PUT libros`, `POST libros/<id>/toggle`, `GET temas`, `GET libros/<id>/ejemplares`, `GET libros/<id>/etiqueta`, `GET libros/pendientes`, `POST libros/importar`, `POST ejemplares/<id>/baja`, `POST ejemplares/<id>/reactivar` | `catalogo`, `libros/nuevo`, `libros/pendientes`, `libros/importar`, `libros/:id`, `libros/:id/editar`, `buscar`, `libros/:id/ubicacion`, `movil`, `movil/:id` | `catalogo` (alta/baja); `buscar`/sesión (consulta) |
| `compras` | Solicitudes con **presupuesto mensual**, envío, cancelación, **recibir el pedido completo o por partes, con factura** | `GET/POST compras`, `GET compras/<id>`, `GET compras/presupuesto`, `POST compras/<id>/enviar`, `/cancelar`, `/recibir` | `compras`, `compras/nueva`, `compras/revisar`, `compras/:id`, `compras/:id/recibir` | `compras` |
| `prestamos` | Validar y registrar préstamo (RN-01), renovar, devolver, recibo (correo/WhatsApp, imprimir, PDF), **políticas** editables | `GET prestamos`, `POST prestamos/validar`, `POST prestamos`, `GET prestamos/<id>`, `POST prestamos/<id>/renovar`, `/devolver`, `GET prestamos/<id>/recibo`, `POST prestamos/<id>/recibo/enviar`, `GET/PUT politicas` | `prestamos`, `prestamos/nuevo`, `prestamos/:id`, `politicas`, `politicas/:id` | `prestamos`; políticas: `perfiles` para editar |
| `espera` | Lista de espera FIFO con reservado y expiración; los usuarios se unen y cancelan por su cuenta | `GET espera`, `GET espera/libros`, `POST espera`, `GET espera/mias`, `POST espera/unirse`, `DELETE espera/<id>` | `espera`, `espera/nueva`, `espera/mias`, `espera/unirse/:id_libro` | `espera` (gestión); sesión (`mias`, `unirse`, cancelar la propia) |
| `adeudos` | Multas, **pago con referencia de Tesorería**, cancelación (admin), **pérdida** y **daño**, tipo de cambio | `GET adeudos`, `GET adeudos/<id>`, `POST adeudos/<id>/pago`, `/cancelar`, `GET adeudos/reposicion`, `GET adeudos/prestamo/<id>`, `POST adeudos/perdida`, `POST adeudos/danio`, `GET tipo-cambio` | `adeudos`, `adeudos/:id`, `adeudos/:id/pago`, `adeudos/:id/cancelar`, `adeudos/perdida/:id`, `adeudos/danio/:id` | `adeudos` (cancelar: rol `admin`) |
| `asistente` | Chatbot por reglas: FAQ, reglas con valores reales de la política, búsqueda de libros, estatus propio, **paso a bibliotecario** | `POST asistente/mensajes`, `GET asistente/conversaciones/<id>`, `POST …/opinion`, `GET asistente/consultas`, `POST asistente/consultas/<id>/resolver` | `asistente`, `movil/asistente`, `asistente/consultas`, `asistente/consultas/:id` | `asistente`; lista de avisosja: `prestamos` |
| `reportes` | Catálogo, usuarios, **alumnos con adeudos** (+ aviso a Servicios Escolares), **inventario por estante**, **préstamos vencidos**, **préstamos por periodo**, **indicadores** (asistente sin pasar a bibliotecario, consultas para el bibliotecario pendientes, discrepancias de inventario, préstamos por mes) e **errores**; pantalla, PDF e impresión; el formulario muestra solo los filtros del tipo elegido | `GET reportes/<tipo>`, `POST reportes/con_adeudos/aviso` | `reportes`, `reportes/:tipo` | `reportes`; además `usuarios` (usuarios) o `prestamos` (alumnos con adeudos, vencidos, préstamos) |
| `notificaciones` | Avisos enviados (simulados) (todos los canales) y "mis notificaciones" | `GET notificaciones`, `GET notificaciones/mias` | `notificaciones`, `notificaciones/mias` | `notificaciones`; `mias`: sesión |
| `info` | FAQ, estado del servicio, diseño, guía y funciones | `GET faq`, `GET health` | `diseno`, `guia`, `funciones` | público / `diseno`, `guia`, `funciones` |

Errores: `{"error": "mensaje"}`. Reglas incumplidas: **422** `{"error", "motivos":[{codigo, mensaje}]}`; conflicto de estado: 409; inexistente: 404; validación: 400; sin sesión: 401; sin permiso: 403.

## Arquitectura

**MVC modular por módulo (vertical slices):** backend, frontend y pruebas en una sola carpeta.

```
proyecto_final/
├── docker-compose.yml  Dockerfile  requirements.txt  pytest.ini  conftest.py  .env.example
├── db/
│   ├── 01_schema.sql            esquema (21 tablas + adiciones S-1..S-5)
│   └── 02_seed.sql              roles, permisos, políticas, libros, ejemplares, intenciones, FAQ
├── scripts/                     levantar  recrear_db  respaldo  restaurar  medir_rendimiento  cargar_datos_volumen  (_pg: ayudas)
├── docs/
│   ├── operacion.md             respaldo, rendimiento, accesibilidad, 3 clics
│   └── requisitos/              matriz_trazabilidad  requerimientos  reglas_de_negocio  propuesta_por_sprint
├── backups/                     respaldos .dump (no se versionan)
└── app/
    ├── __init__.py              create_app(): registra los módulos automáticamente
    ├── config.py                variables de entorno
    ├── seed.py                  usuarios y datos demo (idempotente)
    ├── testing.py               utilidades de prueba
    ├── core/                    ayudas del backend (ver app/core/README.md)
    │   └── tests/
    ├── web/                     shell del frontend
    │   ├── index.html  css/  assets/
    │   └── js/
    │       ├── main.js          carga tolerante de los módulos y arranque del router
    │       ├── core/            api, router, session, layout (menú), ui, theme, pdf, crud
    │       └── components/      UI compartida (ver README de componentes)
    └── modules/
        └── <módulo>/            auth inicio usuarios perfiles catalogo compras prestamos espera
            │                    adeudos asistente reportes notificaciones info
            ├── __init__.py      `bp = make_blueprint(__name__)` (3 líneas)
            ├── model.py         datos (SQL vía core.repo)
            ├── service.py       reglas, esquemas de validación, bitácora
            ├── controller.py    rutas HTTP /api/…
            ├── tests/           pruebas pytest del módulo
            └── web/             model.js (API) · view.js (HTML puro) · controller.js (rutas y eventos)
```

### Capas

| Backend | Frontend | Responsabilidad |
| --- | --- | --- |
| `model.py` | `model.js` | Datos: SQL / llamadas `fetch` |
| `service.py` | `view.js` | Reglas y validación / HTML con los componentes compartidos |
| `controller.py` | `controller.js` | Solo HTTP y permisos / rutas del navegador, eventos y orquestación |

Flujo: `controller → service → model` en el servidor; `controller → model / view` en el navegador. Un módulo **no importa** el `model/service` de otro (salvo `catalogo.model.add_ejemplares`); la coordinación va por `app/core/` (p. ej. `circulacion`, `espera`, `notificaciones`) y por SQL de solo lectura.

### Cómo se registran los módulos y cómo Flask sirve el frontend

- `create_app()` llama a `register_modules` (`app/core/module.py`): recorre `app/modules/`, importa todo paquete con `__init__.py` y su `controller.py`, y registra su `bp`. **Agregar un módulo no requiere tocar el núcleo.**
- `make_blueprint` declara `static_folder="web"` y `static_url_path="/m/<módulo>"`: `app/modules/<m>/web/controller.js` se sirve en `/m/<m>/controller.js` (igual `model.js`, `view.js`).
- `GET /` entrega `app/web/index.html`; `/css`, `/js` y `/assets` salen de `app/web/`.
- `main.js` importa `auth` e `info` de forma estática y el resto (`MODULES`) de forma dinámica y tolerante: un módulo ausente o roto se omite con `console.warn`. Cada `controller.js` exporta `routes = [{path, perm, section, action}]`; el router (hash) las registra y `core/layout.js` arma el menú con las rutas permitidas.

## Componentes y helpers compartidos

- **Backend** — [`app/core/README.md`](app/core/README.md): `repo`, `validators`, `auth`, `errors` (`ApiError.reglas`, `exigir`), `bitacora` (`@audit`), `calendario` (días hábiles), `parametros`, `notificaciones`, `circulacion` (única fuente de RN-01..06), `espera`, `consultas`, `serializers`, `http`.
- **Frontend** — [`app/web/js/components/README.md`](app/web/js/components/README.md): `page`, `listPage`, `dataTable`, `formView`/`bindForm`, `detailView`, `receiptBlock`, `statusBadge`/`labels`, `meter`, `chatPanel`, `confirmAction`, `printHtml`, etc.
- Regla: **los módulos no reimplementan nada de esto** (sin SQL dinámico propio, sin validación a mano, sin tablas/formularios/etiquetas ad hoc).

## Base de datos

21 tablas definidas en `db/01_schema.sql`:

| Grupo | Tablas |
| --- | --- |
| **S1** | `permiso`, `rol`, `rol_permiso`, `usuario`, `bitacora`, `recuperacion_contrasena`, `reporte_generado`, `solicitud_compra`, `ubicacion`, `libro`, `detalle_solicitud`, `ejemplar` |
| **S2** | `politica_prestamo`, `prestamo`, `adeudo`, `renovacion`, `lista_espera` |
| **S3** | `intencion`, `conversacion`, `mensaje`, `pregunta_frecuente` |

**Cambios aditivos al diseño oficial** (documentados en la cabecera de `db/01_schema.sql` y en la matriz de trazabilidad, sección 8; no se agregan tablas):

| # | Cambio | Motivo |
| --- | --- | --- |
| S-0 | `detalle_solicitud.descripcion` | Guardar el título solicitado cuando `id_libro` es `NULL` (libro aún no catalogado) |
| S-1 | `ejemplar.motivo_baja` (`perdido`, `robado`, `danado`, `obsoleto`) | RF-11: motivo de baja por ejemplar |
| S-2 | `libro.tipo_uso` admite `reservado` | RF-10: bibliografía de cátedra, solo mostrador |
| S-3 | `solicitud_compra`: estado `recibida`, `factura_folio`, `factura_total`, `fecha_recepcion`; `detalle_solicitud.cantidad_recibida` | RF-06 recepción y factura; precio de la última compra para RN-04 |
| S-4 | `reporte_generado.tipo` ampliado (`con_adeudos`, `inventario_estante`, `prestamos_vencidos`, `prestamos`, `indicadores`, `errores`) | RF-16, RF-28, PS-MET-02/03, PS-S3-06 |
| S-5 | Índices únicos parciales `uq_prestamo_ejemplar_abierto` y `uq_espera_usuario_libro_activa` | Consistencia concurrente (un ejemplar no se presta dos veces; una espera activa por usuario y libro) |
| S-6 | `bitacora.id_usuario` admite `NULL` | PS-S3-06: errores sin sesión (acción `error_sistema`) |

**Valores "ENUM"** (el diseño no los especificaba; son `VARCHAR` con `CHECK`):

| Campo | Valores |
| --- | --- |
| `usuario.estado`, `libro.estado` | `activo`, `inactivo` |
| `usuario.fuente_validacion` | `servicios_escolares`, `recursos_humanos`, `manual` |
| `libro.tipo_uso` | `prestamo_externo`, `consulta_interna`, `reservado` |
| `ejemplar.estado` | `disponible`, `prestado`, `baja` |
| `ejemplar.motivo_baja` | `perdido`, `robado`, `danado`, `obsoleto` |
| `solicitud_compra.estado` | `pendiente`, `enviada`, `recibida`, `cancelada` |
| `reporte_generado.tipo` | `catalogo_completo`, `catalogo_activo`, `usuarios`, `con_adeudos`, `inventario_estante`, `prestamos_vencidos`, `prestamos` |
| `reporte_generado.formato` | `pantalla`, `pdf`, `impresion` |
| `prestamo.estado` | `activo`, `devuelto`, `vencido` (caché; ver "vencido" abajo) |
| `adeudo.tipo` / `adeudo.estado` | `retraso`, `danio`, `perdida` / `pendiente`, `pagado`, `cancelado` |
| `lista_espera.estado` | `en_espera`, `notificado`, `recogido`, `cancelado` |
| `conversacion.canal` | `web`, `movil` |
| `mensaje.emisor` | `usuario`, `asistente` |

## Reglas de negocio implementadas

Todas las decisiones de circulación salen de `app/core/circulacion.py` (RN-01..RN-06). Los puntos marcados D-xx son **Supuesto del equipo**, pendientes de validar por el Product Owner (detalle en [`docs/requisitos/matriz_trazabilidad.md`](docs/requisitos/matriz_trazabilidad.md), sección 2). Los números son parámetros editables en `politica_prestamo` (pantalla **Políticas**) o variables de entorno; cambiarlos no requiere tocar código.

| Regla | Valor implementado | Decisión |
| --- | --- | --- |
| **RN-01 Autorizar préstamo** | Usuario activo con política vigente, **sin adeudos pendientes**, **sin préstamos vencidos**, por debajo de su límite; libro activo, de **préstamo externo** y con ejemplar disponible no reservado para otro | D-01, D-02 |
| **Límites** | Alumno **2** ejemplares simultáneos; docente **3** (con 2 prestados se rechaza el 3.º) | D-01 |
| **RN-05/06 Vigencia** | Alumno **5** días hábiles; docente **10** | D-03 |
| **Días hábiles** | Lunes a viernes; los festivos cuentan como hábiles; el día 1 es el siguiente hábil; el vencimiento es **inclusivo** (devolver ese día no multa) | D-03 |
| **"Vencido"** | `fecha_devolucion IS NULL AND fecha_vencimiento < CURRENT_DATE`; `prestamo.estado` es solo caché | D-24 |
| **RN-02/06 Renovación** | Suma **un periodo completo** al vencimiento actual; máx. **2** (alumno) o **3** (docente) por préstamo. Se rechaza si el préstamo está vencido, hay adeudos, se alcanzó el máximo o el libro tiene **lista de espera** activa | D-05, D-06 |
| **RN-03 Multa** | **$10.00 MXN por día hábil** de retraso, igual para alumno y docente, **sin tope**; se genera al devolver (adeudo `retraso`). Un préstamo vencido sin devolver muestra "multa estimada" | D-04 |
| **Pago de multa** | Lo registra personal con una **referencia de Tesorería** (3–40 caracteres); queda en bitácora. Solo el **admin** puede cancelar (con motivo) | D-10 |
| **RN-04 Reposición (pérdida)** | Precio de la **última compra recibida** del libro (o `precio_referencia`) en **USD × tipo de cambio** (`TIPO_CAMBIO_USD_MXN`, 18.00 simulado), 2 decimales; ejemplar a `baja/perdido`; aviso a Servicios Escolares y Tesorería; las multas de retraso se cobran aparte | D-07 |
| **Daño** | **50 %** del valor de reposición por defecto (editable de 10 a 100 %); opción de dar de baja el ejemplar (`danado`) | D-08 |
| **Lista de espera** | Solo libros de préstamo externo **sin ejemplares disponibles**; FIFO; una entrada activa por usuario y libro. Al devolverse un ejemplar se **notifica al primero** y se le aparta **2 días hábiles** (`ESPERA_DIAS_RESERVA`); vencido el plazo pasa al siguiente (expiración perezosa al consultar). Un ejemplar reservado solo se presta al usuario notificado | D-19 |
| **Suspendido** | No se almacena: es el estado calculado "préstamo vencido o adeudo pendiente"; bloquea nuevos préstamos | D-09 |
| **Reservado** | Libro de bibliografía de cátedra (`reservado`): visible en búsqueda, no se presta | D-20 |
| **Compras** | Presupuesto mensual `PRESUPUESTO_MENSUAL_USD` (5000 USD); lo usado es la suma de solicitudes no canceladas del mes y una solicitud que lo excede se rechaza (422 `PRESUPUESTO_EXCEDIDO`). Recibido por partes o total con folio de factura; las líneas ligadas a un libro suman ejemplares, las demás quedan "pendientes de catalogar". Precios en **USD**, pesos en **MXN** | D-22, D-25, D-28 |
| **Inventario por estante** | Solo personal con permiso `reportes` | D-21 |
| **Rol Colaborador** | Perfil de apoyo con `catalogo` y `compras`, sin préstamos | D-12 |
| **Alumnos y docentes** | No operan el préstamo (lo registra el bibliotecario); sí consultan su estado con el asistente, ven sus notificaciones y se unen o cancelan su lista de espera | D-27 |

Otras reglas vigentes: matrícula de 3 a 10 caracteres, correo válido, contraseña mínima de 6; no se da de baja una cuenta con préstamos abiertos o adeudos pendientes, la propia cuenta ni al último administrador; el administrador no puede perder `usuarios` ni `perfiles`; clave de libro única de 3 a 10 caracteres y no se dan de baja libros con préstamos activos ni ejemplares prestados; sesión por cookie firmada (HttpOnly, SameSite=Lax, 12 h).

### Asistente conversacional (basado en reglas, sin LLM)

Normaliza el texto (minúsculas, sin acentos), detecta el tema de la pregunta por palabras clave y similitud con `pregunta_frecuente`, y responde con datos reales: reglas desde `politica_prestamo`, búsqueda de libros (máx. 5, con disponibilidad y ubicación) y, con sesión iniciada, estatus de préstamos y multas propios. Una petición explícita ("hablar con un bibliotecario") o dos mensajes consecutivos no entendidos **pasan a bibliotecario** la conversación a la bandeja del bibliotecario (`#/asistente/consultas`, permiso `prestamos`). Cada mensaje queda en `mensaje`; el visitante solo ve sus propias conversaciones.

## Notificaciones e integraciones simuladas

No se envía nada a sistemas externos. `app/core/notificaciones.py::enviar` registra cada aviso en `bitacora` (`accion = notif_<canal>`) y se muestra en **Notificaciones** con la etiqueta "Simulado".

| Canal | Cuándo se genera |
| --- | --- |
| `email` | Recibo de préstamo, aviso a la lista de espera, pago de adeudo, pérdida/daño |
| `whatsapp` | Recibo de préstamo si el operador lo elige (canales combinables) |
| `servicios_escolares` | Pérdida de material; aviso de alumnos con adeudos (reporte `con_adeudos`) |
| `tesoreria` | Pérdida de material; factura al recibir una compra |

La actualización desde Servicios Escolares es un archivo simulado (`app/modules/usuarios/simulado/servicios_escolares.json`) más la importación de lista de alumnos por CSV (`matricula,nombre_completo,correo,rol,estado`). Cambiar a un proveedor real solo exige modificar `core/notificaciones.py::enviar` y el origen de la actualización.

## Pruebas

Con los contenedores levantados:

```bash
docker compose exec -T web pytest                 # las 236 pruebas
docker compose exec -T web pytest app/modules/prestamos
docker compose exec -T web pytest app/core
```

`pytest.ini` busca `test_*.py` en `app/core` y `app/modules`. Usan la BD real del contenedor mediante `app/testing.py` y `conftest.py` (fixtures `anon admin alumno alumno2 catalogo comprador bibliotecario docente colaborador login_as`, y fábricas `make_user`, `make_book`, `make_loan`). Los resultados de las pruebas E2E en navegador se registran en la matriz de trazabilidad.

## Rendimiento

Meta: percentil 95 ≤ 3 s por endpoint (RNF-03/05/11/13, D-15). `scripts/medir_rendimiento.py` inicia sesión, llama a cada endpoint crítico (libros, usuarios, préstamos, adeudos, espera, compras, notificaciones, asistente, reportes) `-n` veces una a una y luego `-c` solicitudes concurrentes. Con `--escritura` mide también crear préstamo, renovar, devolver y registrar pago. El dataset de D-15 se carga con `scripts/cargar_datos_volumen.py`. Resultados en [`docs/operacion.md`](docs/operacion.md) sección 3: con el volumen completo (5 000 usuarios, 10 002 ejemplares, 20 664 préstamos) el p95 máximo es 0.28 s una a una y 2.43 s con 20 concurrentes (lecturas), y 0.07 s en los flujos de escritura. Los listados de usuarios, préstamos y multas devuelven por defecto los primeros 500 registros (`?limite=`, máx. 2 000) y la pantalla avisa cuando se alcanza el tope.

## Errores y indicadores (PS-S3-06, PS-MET-02/03)

Los errores 500 del servidor y los errores de JavaScript del navegador (`POST /api/errores`, con límite de frecuencia: 5 por minuto por IP) se guardan en `bitacora` con acción `error_sistema` (en `bitacora.id_usuario` puede ir NULL si no hubo sesión). El personal con permiso `reportes` los consulta en **Reportes → Errores**; **Reportes → Indicadores** resume el asistente, el inventario y los préstamos por periodo.

## Respaldo y restauración

RPO 24 h (respaldo diario programado) y RTO 30 min. `respaldo.py` genera el `.dump` y un `.conteos`; `restaurar.py --verificar` restaura en una BD temporal, compara conteos por tabla y no toca la BD real. Procedimientos, programación con cron/Programador de tareas, recuperación ante desastre, checklist de accesibilidad y procesos de 3 clics: [`docs/operacion.md`](docs/operacion.md).

## Variables de entorno

Se leen de `.env` (creado desde `.env.example` por `levantar.py`) y las usa `docker-compose.yml`.

| Variable | Valor por defecto | Uso |
| --- | --- | --- |
| `POSTGRES_DB` | `librigest` | Nombre de la base de datos |
| `POSTGRES_USER` | `librigest` | Usuario de PostgreSQL |
| `POSTGRES_PASSWORD` | `librigest` | Contraseña de PostgreSQL |
| `SECRET_KEY` | `change-me-please` (`.env.example`) / `dev-secret-change-me` (compose) | Firma de cookies de sesión; **cámbiala en producción** |
| `TIPO_CAMBIO_USD_MXN` | `18.00` | Tipo de cambio simulado para reposición (RN-04) |
| `PRESUPUESTO_MENSUAL_USD` | `5000` | Presupuesto mensual de adquisiciones |
| `ESPERA_DIAS_RESERVA` | `2` | Días hábiles que se aparta un libro al primero de la lista de espera |
| `DEMO_MOSTRAR_TOKEN` | `true` (demo) | `true`: la recuperación de contraseña devuelve el código en pantalla. `false` (producción): la API solo responde `ok` y el código queda como correo simulado en Notificaciones |
| `HTTPS` | `false` | `true` cuando un proxy inverso termina TLS: la cookie de sesión se marca `Secure` (siempre `HttpOnly` y `SameSite=Lax`) |
| `WEB_CONCURRENCY` | `4` | Procesos de gunicorn |
| `DATABASE_URL` | construida por compose | Conexión de la aplicación (no va en `.env`) |

Tras cambiar variables: `docker compose up -d web`.

## Documentación de requisitos (`docs/requisitos/`)

| Archivo | Contenido |
| --- | --- |
| [`matriz_trazabilidad.md`](docs/requisitos/matriz_trazabilidad.md) | Estado de cada requisito con evidencia `archivo:línea`, decisiones D-01..D-29, plan por paquetes (ejecutado) y verificación |
| [`requerimientos.md`](docs/requisitos/requerimientos.md) | Checklist de requerimientos funcionales y no funcionales |
| [`reglas_de_negocio.md`](docs/requisitos/reglas_de_negocio.md) | Checklist de reglas de negocio, roles y contexto |
| [`propuesta_por_sprint.md`](docs/requisitos/propuesta_por_sprint.md) | Checklist de la propuesta por sprint |
| [`decisiones_para_validacion.md`](docs/requisitos/decisiones_para_validacion.md) | Hoja de revisión de D-01..D-29 con columna de firma del Product Owner (pendiente) |
| [`../uat.md`](docs/uat.md) | Guion de pruebas de aceptación (UAT) por rol con resultados del E2E del 2026-10-27 |
| [`../operacion.md`](docs/operacion.md) | Guía de operación (fuera de `requisitos/`) |

## Alcance y limitaciones

- **Integraciones simuladas:** Servicios Escolares, Tesorería, correo y WhatsApp no existen como servicios reales; todo queda en la lista de avisos en `bitacora` (la conexión real queda fuera de alcance).
- **Sin app nativa:** la vista web responsiva (`#/movil`, `#/movil/asistente`) cubre la "APP"; no hay React Native, Redis ni JWT (cookie de sesión firmada).
- **Recuperación de contraseña:** no envía correo; con `DEMO_MOSTRAR_TOKEN=true` (demo) la pantalla muestra el token generado; con `false` solo queda en la lista de avisos simulada.
- **Asistente:** basado en reglas y FAQ, sin modelo de lenguaje ni SLA de respuesta del bibliotecario.
- **Calendario:** sin festivos; solo se excluyen sábado y domingo (D-03).
- **Fuera de alcance (D-18):** préstamo de revistas, vigilancia de puerta y colocación física de libreros.
- **Decisiones D-xx** sin validar por el Product Owner; las políticas y el tipo de cambio son parámetros.
- **Seguridad:** el servidor no termina TLS (usar proxy inverso, ver `docs/operacion.md` sección 7); las contraseñas demo son públicas. Para un despliegue real cambia `SECRET_KEY`, las credenciales de PostgreSQL y usa HTTPS.
- **Pantallas informativas:** "Guía de demostración" y "Funciones" (`info`) describen solo los módulos originales; aún no listan los de circulación.
