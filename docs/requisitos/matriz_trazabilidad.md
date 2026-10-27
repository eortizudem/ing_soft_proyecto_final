# LibriGest (Biblioteca Ducky) - Matriz de trazabilidad y plan de implementación

Fecha de corte de la re-evaluación: 2026-10-27 (tras implementar los Sprints 0-3). Base: código en `app/`, `db/`, `scripts/`, `docs/operacion.md`, `README.md` y los tres checklists de `docs/requisitos/` (`reglas_de_negocio.md`, `requerimientos.md`, `propuesta_por_sprint.md`).
Las rutas de evidencia son relativas a la raíz del proyecto (`archivo:línea`).

Leyenda de estado: ✅ Cumple · 🟡 Parcial · ❌ Falta · ⛔ No aplica (conflicto con una restricción del usuario o fuera del producto).
Criterio de ✅: implementado en código, con prueba `pytest` (236 pruebas pasan) o evidencia directa. La verificación en navegador está en la sección 9 (E2E en Chrome, 2026-10-27).

## 0. Resumen

| Sección | Filas | ✅ | 🟡 | ❌ | ⛔ |
|---|---|---|---|---|---|
| RN / RO / CTX (3.1) | 17 | 13 | 3 | 0 | 1 |
| RF-01..33 (3.2) | 33 | 33 | 0 | 0 | 0 |
| RNF-01..14 (3.3) | 14 | 14 | 0 | 0 | 0 |
| PS (3.4, filas agrupadas) | 84 | 64 | 13 | 0 | 7 |
| **Total** | **148** | **124** | **16** | **0** | **8** |

Una fila de PS puede agrupar varios IDs (p. ej. PS-S2-07..11); las filas mixtas se cuentan por su primer estado. Los ítems de gestión de proyecto no se cuentan (sección 4).

**Hallazgo principal:** los Sprints 0-3 están implementados de punta a punta. Existen los módulos `prestamos`, `espera`, `adeudos`, `asistente` y `notificaciones`, y se ampliaron `compras`, `catalogo`, `usuarios`, `reportes` e `inicio`. Las 6 reglas de negocio operan desde una única fuente (`app/core/circulacion.py`). Lo que sigue en 🟡 es lo que no se cierra desde el código: validación del Product Owner (`decisiones_para_validacion.md`), UAT con usuarios reales (`docs/uat.md`), cronometraje en mostrador, TLS (proxy inverso, documentado) y la conexión real a sistemas externos (⛔, simulada). La medición con el dataset de D-15, la auditoría de accesibilidad y el conteo de clics se cerraron (sección 9).

**Riesgos y estado actual**

1. ~~Semilla contradice las reglas~~ **Resuelto (P0)**: políticas alumno 5/2/2/$10 y docente 10/3/3/$10 en días hábiles (`db/02_seed.sql:61-65`).
2. ~~Núcleo de circulación acoplado~~ **Resuelto**: `app/core/circulacion.py` (reglas puras y autorización) más `app/core/espera.py` y `app/core/notificaciones.py`; "vencido" definido una vez (D-24, `app/core/consultas.py:13-14`).
3. **Ambigüedades sin dueño:** la sección 2 sigue siendo **Supuesto del equipo**; el Product Owner debe validar D-01..D-29 (PS-S0-08, PS-S2-15).
4. ~~Esquema oficial de 21 tablas~~ **Cumplido**: 6 adiciones aditivas documentadas en la cabecera de `db/01_schema.sql:3-13` y en la sección 8; sin tablas nuevas.
5. **Integraciones externas** (Servicios Escolares, Tesorería, correo, WhatsApp): simuladas con los avisos `notif_*` en `bitacora` (D-11) y el archivo `app/modules/usuarios/simulado/servicios_escolares.json` (D-23). PS-S4-08 queda fuera.
6. ~~Sin respaldo/restore ni medición~~ **Resuelto**: `scripts/respaldo.py`, `restaurar.py --verificar`, `medir_rendimiento.py` y `docs/operacion.md`. Medición con el dataset de D-15 (`scripts/cargar_datos_volumen.py`) y auditoría WCAG AA: hechas (sección 9).
7. **Defectos detectados al inicio:** ~~etiqueta de adeudos en usuarios~~ corregido (`usuarios/model.py:9-11`, `usuarios/web/view.js:72`). El token de recuperación solo se devuelve con `DEMO_MOSTRAR_TOKEN=true` (demo, `auth/controller.py:33-35`). Sigue vigente: el directorio no es un repositorio git (PS-TEC-10).
8. **Inconsistencias doc/código abiertas:** (a) ~~Guía y Funciones sin los módulos nuevos~~ resuelto: `app/modules/info/web/model.js:32-48`; (b) D-27 se amplió en la práctica: alumnos y docentes pueden unirse y cancelar su lista de espera (`espera/controller.py:20-41`) y ver sus notificaciones (`notificaciones/controller.py:15`).

---


## 1. Restricciones del usuario (prevalecen sobre los documentos)

| # | Restricción | Efecto sobre los documentos |
|---|---|---|
| U1 | Docker + PostgreSQL + Flask. Sin NestJS/Express/otros frameworks; sin ORM; psycopg 3 con SQL explícito (`app/core/db.py:1-50`). | ⛔ PS-TEC-03 (Node/NestJS/Express). |
| U2 | Aplicación lo más ligera posible: JS vanilla + CSS plano, sin React, sin paso de build, sin CDNs (`app/web/index.html:10-13`, fuentes locales `app/web/assets/`). | ⛔ PS-TEC-01 (React+TS), PS-TEC-02 (React Native/Expo), PS-TEC-05/PS-S1-11 (Redis). |
| U3 | BD sigue el diseño oficial "Diseño Completo de la Base de Datos" (21 tablas, `db/01_schema.sql`). Cambios solo aditivos, estrictamente necesarios y documentados (sección 8). | Reglas que requieran tablas nuevas se resuelven con tablas existentes (`bitacora`, `conversacion`, config en entorno). |
| U4 | MVC modular unificado: cada módulo `app/modules/<m>/` contiene todo su backend (`model.py`, `service.py`, `controller.py`), su frontend (`web/model.js`, `view.js`, `controller.js`) y `tests/`. | Todo el trabajo nuevo = módulos nuevos o existentes con esa estructura. |
| U5 | Scripts Python: `scripts/levantar.py` (levanta contenedores) y `scripts/recrear_db.py` (recrea y siembra BD). | Los scripts nuevos (respaldo/restauración) siguen el mismo estilo (solo biblioteca estándar). |
| U6 | Estilos consistentes entre vistas (mismos márgenes en búsquedas, filtros y contenido; inputs de texto con fondo blanco y borde). | Los `view.js` nuevos reutilizan los helpers de `app/web/js/core/ui.js` y las clases de `components.css`; no se crean estilos ad hoc. |
| U7 | "APP" nativa se satisface con la vista web responsiva/móvil (`#/movil`). | ⛔ App React Native (PS-S1-08 parte App, PS-TEC-02, PS-ALC-06 parte app, PS-S3 parte App). |

Consecuencias adicionales: ⛔ JWT (PS-S0-05, PS-TEC-06): se usa cookie de sesión firmada de Flask (`app/config.py:7-9`, `app/core/auth.py:9-14`), que cumple el objetivo (autenticación usuario/contraseña con hash, RBAC) sin JWT.

---

## 2. Decisiones por ambigüedad (todas: **Supuesto del equipo**, pendientes de validación del Product Owner)

| ID | Ambigüedad (origen) | Decisión propuesta | Justificación |
|---|---|---|---|
| D-01 | Límite de ejemplares (A-01 RN, A-7 RF, A-26) | **Alumno: máximo 2 simultáneos en total** (con 2 ya prestados se rechaza el 3.º). **Docente: máximo 3.** Valores en `politica_prestamo.max_libros`. | Lectura literal ("no tiene más de dos") permitiría 3, contradice el espíritu de RN-02/RN-06 ("no exceda"). Profesor: sin dato; 3 > alumno, coherente con sus 3 renovaciones; editable por política. |
| D-02 | Elegibilidad del profesor (A-03, A-26) | El docente está sujeto a las mismas condiciones de RN-01 (sin multas, sin vencidos, bajo su límite, libro disponible y de préstamo externo). | Tratamiento uniforme (ISO 9001: "procedimientos uniformes"). |
| D-03 | Días hábiles (A-22, A-23, A-25) | Hábil = lunes a viernes; **festivos cuentan como hábiles** (sin calendario). El día 1 es el siguiente día hábil al del préstamo; si se presta en sábado/domingo se cuenta desde el lunes. El vencimiento es **inclusivo** (devolver el día de vencimiento no genera multa). `dias_prestamo` se interpreta en días hábiles: alumno 5, docente 10. | Mínimo viable y verificable; texto de RN-05/06 solo excluye sábado y domingo. |
| D-04 | Multa (A-11..A-15) | **$10.00 MXN por día hábil de retraso** (misma tarifa alumno y docente, `politica_prestamo.multa_diaria`). Retraso = días hábiles en (fecha_vencimiento, fecha_devolución]. **Sin tope.** Se genera al registrar la devolución (adeudo `retraso`) o al reportar pérdida. Un préstamo vencido sin devolver muestra "multa estimada" (no persistida). Cancelación: solo `admin`. | Consistente con la vigencia en días hábiles (sábado/domingo no generan multa). Sin tope porque la fuente no lo define; la cancelación cubre casos excepcionales. |
| D-05 | Renovación (A-06..A-09, A-10) | Renovar suma **un periodo completo** (`dias_prestamo` hábiles) a la **fecha de vencimiento actual**. Se rechaza si: préstamo vencido (hoy > vencimiento), usuario con adeudos pendientes, `num_renovaciones >= max_renovaciones` (alumno 2, docente 3), o el libro tiene lista de espera activa (`en_espera`/`notificado`). Límite **por préstamo**. | Evita beneficiar a morosos y respeta a quien espera; "según fecha de vencimiento" se interpreta como "no vencido". |
| D-06 | Quién registra/autoriza renovación (A-5 RF, A-10) | Bibliotecario y Administrador pueden registrarla; la validación automática (RNF-09) sustituye la autorización manual del Administrador, que queda en bitácora (`prestamo_renovar`). | Matriz: Bibliotecario tiene acceso al módulo; autorización explícita no es automatizable sin flujo de aprobación no pedido. |
| D-07 | Pérdida (A-16..A-21, A-29) | Valor de reposición = **precio de la última compra recibida** del libro (`detalle_solicitud.precio_unitario` de la última solicitud `recibida`; si no hay, `libro.precio_referencia`) **en USD** × **tipo de cambio** de la variable `TIPO_CAMBIO_USD_MXN` (simulado Banxico/FIX, default 18.00), redondeo a 2 decimales. Aplica también a docentes. Las multas por retraso acumuladas hasta el reporte se cobran como adeudo `retraso` aparte. El ejemplar queda `baja` con `motivo_baja='perdido'`. | RN-04 pide USD × tipo de cambio actual; no hay tabla de tipo de cambio (U3), se parametriza por entorno y se puede sobrescribir por reporte. Todos los precios de compra/catálogo se capturan en USD (etiquetar en UI). |
| D-08 | Daño (RF-25, sin fórmula) | Adeudo `danio` = **50 %** del valor de reposición por defecto, editable por el bibliotecario entre 10 % y 100 %; con opción "dar de baja el ejemplar" (`motivo_baja='danado'`). | La fuente cita daño sin fórmula; 50 % es un punto medio defendible, parametrizable. |
| D-09 | Suspensión y época de exámenes (A-31, A-15 RF) | "Suspendido" **no se almacena**: es el estado calculado "alumno con préstamo vencido sin devolver o adeudo pendiente"; bloquea nuevos préstamos por RN-01. La lista RF-28 se genera **manualmente** (botón) por Administrador/Bibliotecario y el aviso a Servicios Escolares queda en la lista de avisos simulada. | No hay regla ni calendario; evita estado persistente no previsto por el esquema. |
| D-10 | Flujo de pago de multas (A-30, RF-27) | El alumno paga en Tesorería y entrega el comprobante; el Bibliotecario registra el pago con una **referencia de Tesorería** obligatoria (se guarda en `bitacora.detalle`; `adeudo` no tiene columna) y fecha. Estado `pagado`. | Cumple RO-04.f/RO-06 sin tabla nueva. |
| D-11 | Notificaciones externas (A-10 RF, PS-RIE-05) | **Avisos enviados (simulados)** en `bitacora` (`accion = 'notif_email' / 'notif_whatsapp' / 'notif_servicios_escolares' / 'notif_tesoreria'`, `detalle = "<destino>\|<asunto>: <cuerpo>"` truncado a 200). Se expone con UI en el módulo `notificaciones`. Interfaz única `app/core/notificaciones.py::enviar(...)` = adaptador intercambiable; correo es el canal mínimo; los canales de RF-19 (email, WhatsApp, impresión) son **opcionales y combinables** por el operador. | Satisface visibilidad (RNF-10/PS-S2-06) sin credenciales reales (PS-S4-08 fuera). |
| D-12 | Rol "Colaborador" (A-2 RF, A-6 PS) | Se crea el perfil **`colaborador`** (dato semilla, no esquema): personal de apoyo con acceso a mantenimiento de libros (permisos `catalogo` + `compras`), búsqueda, reportes y asistente; **sin** préstamos. Los perfiles `catalogo` y `comprador` se conservan (RF-01). El `bibliotecario` recibe además `catalogo` (la matriz le da acceso a Mantenimiento de libros). | Cierra PS-S0-01 literal sin esquema nuevo; sigue la matriz del cliente. |
| D-13 | Chatbot (PS-S3-07, A-15 PS) | **Asistente basado en reglas**: normaliza texto (minúsculas, sin acentos), detecta el tema de la pregunta (intención) por palabras clave (diccionario en `service.py`) y por similitud con `pregunta_frecuente`; consultas de estado propio por SQL (requiere sesión de usuario, no visitante); búsqueda de libros reutilizando SQL del catálogo; explicación de reglas leyendo `politica_prestamo`; **paso a bibliotecario**: crea una conversación pendiente (`conversacion.resuelta=false` + mensaje con intención `pasar_a_bibliotecario`) visible en una bandeja del bibliotecario; no hay SLA. Sin LLM. | Cumple "motor híbrido de intents + base de conocimiento" con las 4 tablas S3 existentes, sin dependencias externas (U2). |
| D-14 | Respaldo/restauración (A-11 RF, PS-S0-06) | `scripts/respaldo.py` (`pg_dump -Fc` vía `docker compose exec db`) y `scripts/restaurar.py` (`pg_restore`), con `--verificar` que restaura en una BD temporal y compara conteos (la "prueba documentada"). RPO 24 h (respaldo diario programado con cron/Programador de tareas, documentado), RTO 30 min. | Sin RPO/RTO en la fuente; valores razonables para el alcance. |
| D-15 | Tiempo de respuesta ≤ 3 s (A-11 RF, A-12 PS) | Percentil 95 ≤ 3 s por endpoint con el dataset demo ampliado (≥ 5 000 usuarios, ≥ 10 000 ejemplares, ≥ 20 000 préstamos), un usuario a la vez más prueba de 20 solicitudes concurrentes. Medido con `scripts/medir_rendimiento.py`. | Fuente sin carga ni percentil. |
| D-16 | Accesibilidad (A-12 RF, PS-S1-10) | Objetivo **WCAG 2.1 AA (criterios básicos)**: contraste ≥ 4.5:1, foco visible, navegación completa por teclado, etiquetas en todos los campos, `aria-live` para mensajes, `lang="es"`, saltar al contenido. Checklist manual + revisión estática. | La propuesta lo cita como "referencia"; se adopta AA básico como criterio verificable. |
| D-17 | 3 clics (A-13 RF) | Procesos medidos desde la pantalla de inicio con la barra lateral: **prestar** (Préstamos → Nuevo préstamo → Confirmar), **devolver**, **renovar**, **registrar pago**, **buscar y ver ubicación**, **registrar libro**, **crear solicitud de compra**. Máximo 3 clics (sin contar escritura). | Define los procesos que cuentan. |
| D-18 | Revistas, puerta, libreros físicos (A-32, A-33) | **Fuera de alcance:** préstamo de revistas (sin reglas), vigilancia de puerta y colocación física. La ubicación en librero sí es dato del catálogo (RF-09). | Sin reglas ni datos. |
| D-19 | Lista de espera (RF-22, A-8 PS) | Solo para libros activos de préstamo externo **sin ejemplares disponibles**; FIFO; una entrada activa por usuario y libro; al devolverse un ejemplar se notifica al primero y se le **aparta el ejemplar 2 días hábiles** (`fecha_limite_recoger`); vencido el plazo pasa al siguiente. El préstamo de un ejemplar reservado solo se autoriza al usuario notificado. | Fuente solo menciona "lista de espera"; el esquema (`posicion`, `notificado`, `fecha_limite_recoger`) sugiere este flujo. |
| D-20 | "Reservado" vs "consulta externa" (A-17 RF) | Terminología: "consulta externa" = **préstamo externo**; "consulta interna" = solo sala; **"reservado"** = libro reservado (bibliografía de cátedra), no se presta, se consulta en mostrador. Requiere ampliar el CHECK de `libro.tipo_uso` (sección 8). | Distingue reservado de consulta interna sin tabla nueva. |
| D-21 | Listas parciales de existencia (A-6 RF, RF-16; en pantalla: «Inventario por estante») | Solo **personal** (admin, bibliotecario, catalogo, colaborador) mediante permiso `reportes`, aunque la matriz diga "todos". Los usuarios ven existencia/disponibilidad en la búsqueda (RF-14/15). | Es un instrumento de inventario interno. |
| D-22 | Presupuesto mensual (RF-05) | Variable `PRESUPUESTO_MENSUAL_USD` (default 5 000 USD, sin tabla). Usado del mes = suma `total_estimado` de solicitudes no canceladas del mes; una solicitud que exceda el disponible se rechaza (422). | No hay tabla de presupuesto en el diseño oficial. |
| D-23 | Servicios Escolares / lista de alumnos (A-14, PS-S0-11) | Simulado: archivo `app/modules/usuarios/simulado/servicios_escolares.json` + importación de CSV del lista de alumnos desde la UI; ambos hacen alta/modificación/baja y marcan `fuente_validacion='servicios_escolares'`. | PS-SUP-03 (lista de alumnos tabular) y PS-RIE-02 (servicios simulados). |
| D-24 | Definición única de "vencido" | **Vencido ⇔ `fecha_devolucion IS NULL AND fecha_vencimiento < CURRENT_DATE`.** `prestamo.estado='vencido'` es solo un caché actualizado de forma perezosa; ningún paquete debe depender de él. | Evita divergencias entre módulos sin tareas programadas. |
| D-25 | Recepción de libros (A-6, RF-06) | Actor: Comprador/Administrador/Colaborador (permiso `compras`). Soporta recepción parcial (`detalle_solicitud.cantidad_recibida`); al recibir con `id_libro` se agregan ejemplares; títulos nuevos quedan "pendientes de catalogar" para el Administrador del Catálogo. Enlace a Tesorería = aviso simulado con folio de factura. | Fuente no indica actor. |
| D-26 | Visitante | Solo búsqueda y asistente (sin consultas de estado propio). | Ya es el comportamiento actual (`app/modules/auth/service.py:25-30`). |
| D-27 | Alcance de "Alumno/Profesor" en préstamos (A-4 RF) | Alumnos y docentes **no operan** el préstamo, la renovación ni el pago (los registra el personal; la matriz no los habilita). **Implementado además (autoservicio):** consultan su estado vía asistente, ven sus notificaciones (`notificaciones/mias`) y se unen o cancelan su propia lista de espera (`espera/mias`, `espera/unirse`). | Respeta la matriz de usuarios. |
| D-28 | Moneda | Pesos = **MXN**; precios de compra/catálogo = **USD**. | Cierra A-14, A-9. |
| D-29 | Sprint de cada requisito | Se conserva el sprint del documento de requerimientos; RN sin sprint se asignan al de su módulo. | A-10 RN. |

---


---

## 3. Matriz de trazabilidad

Evidencia re-evaluada contra el código actual. "Falta" indica solo lo que sigue pendiente.

### 3.1 Reglas de negocio (RN) y roles (RO), contexto (CTX)

| ID | Requisito | Estado | Evidencia | Falta | Referencias cruzadas |
|---|---|---|---|---|---|
| RN-01 | Autorización de préstamo (sin multas, ≤ límite, sin vencidos; libro disponible y préstamo externo) | ✅ | `core/circulacion.py:77-104` (`evaluar_prestamo`), `:188-203`; `prestamos/service.py:89-107,148-166`; pruebas `prestamos/tests/test_prestamos.py:88-139` | — | RF-17, RF-18, RNF-09, PS-S2-01 |
| RN-02 | Renovación (según vencimiento, ≤ 2 renovaciones alumno) | ✅ | `core/circulacion.py:107-126,204-227`; `prestamos/service.py:171-177`; pruebas `test_prestamos.py:241,259` | — | RF-21, PS-S2-04 |
| RN-03 | Multa $10 por día de retraso (alumno y profesor) | ✅ | `core/circulacion.py:62-69`; adeudo al devolver `prestamos/service.py:182-197`; semilla `db/02_seed.sql:61-65`; pruebas `test_prestamos.py:297-322` | — | RF-25, PS-S2-09 |
| RN-04 | Reposición por pérdida = última compra USD × tipo de cambio | ✅ | `core/circulacion.py:134-137,230-242`; `adeudos/service.py:122-139`; `GET /api/tipo-cambio` `adeudos/controller.py:66`; `core/parametros.py:13` | — | RF-25, RF-26 |
| RN-05 | Vigencia alumno 5 días hábiles | ✅ | `core/calendario.py:13-45`; `core/circulacion.py:57-59`; política `db/02_seed.sql:61-65`; prueba `test_prestamos.py:156-166` | — | RF-20, PS-S2-03 |
| RN-06 | Docentes: 3 renovaciones, multa $10, 10 días hábiles | ✅ | Política docente `db/02_seed.sql:61-65`; `evaluar_renovacion` `core/circulacion.py:107`; prueba `test_prestamos.py:241` | — | RF-20, RF-21 |
| RO-01 | Administrador de Biblioteca | ✅ | Perfil `admin` con los 15 permisos `db/02_seed.sql:17-23` | — | RF-01 |
| RO-02 | Comprador de Libros (solicita con lista y presupuesto) | ✅ | `compras/service.py:53-62` (presupuesto), `:71-85` (422 `PRESUPUESTO_EXCEDIDO`), `:109-149`; permiso `db/02_seed.sql:24-25` | — | RF-05 |
| RO-03 | Administrador del Catálogo (fichas y etiquetas) | ✅ | Ficha `catalogo/service.py:80-107`, etiqueta `:169-172`; UI imprimir/PDF `catalogo/web/controller.js:69-72` | — | RF-07 |
| RO-04 | Bibliotecario (a–h) | ✅ | Perfil con `catalogo prestamos espera adeudos reportes notificaciones` `db/02_seed.sql:21-23`; prestar/recibir/renovar `prestamos/controller.py:7-52`; pagos `adeudos/service.py:91-103`; alumnos con adeudos `reportes/service.py:31-37,96-106`; localizar `catalogo/web/controller.js:131`. Sub-ítems .a/.c/.d: ⛔ D-18 | — | RF-17..28 |
| RO-05 | Profesor (consulta y solicita préstamos, Regla 6) | 🟡 | Consulta y asistente `db/02_seed.sql:26-27`; se une/cancela su espera `espera/controller.py:20-41`; sus avisos `notificaciones/controller.py:15`; préstamo bajo Regla 6 con 10 días/3 libros `circulacion.py:77-104` | El préstamo lo registra el bibliotecario (D-27); no hay solicitud de préstamo en línea | RN-06 |
| RO-06 | Alumno (consulta, solicita préstamos/renovaciones, paga en Tesorería) | 🟡 | Consulta `catalogo/controller.py:7-15`; espera propia `espera/service.py:86-90`; pago en Tesorería con referencia `adeudos/service.py:22-29` | Préstamo, renovación y pago los registra el personal (D-10, D-27); sin solicitud en línea | RF-27 |
| CTX-01 | Automatizar préstamo y devolución | ✅ | `prestamos/service.py:148-197` | — | RF-17..28 |
| CTX-02 | Eliminar inconsistencia catálogo vs disponibilidad | ✅ | Disponibilidad viva `catalogo/model.py:8-14`, `core/consultas.py:17`; índice único `db/01_schema.sql:179`; `SKIP LOCKED` `prestamos/model.py:66-68`; prueba `test_prestamos.py:222` | — | RNF-08, PS-S1-09 |
| CTX-03 | Reducir tiempos de atención | 🟡 | Préstamo/devolución/renovación en 3 clics (`prestamos/web/controller.js`); validación en vivo; fila "Tiempo de atención" en `indicadores` documenta que no es derivable `reportes/service.py:45-70` | Sin cronometraje < 1 min en mostrador (PS-MET-01) | PS-MET-01, RNF-11 |
| CTX-04 | Inventarios con listas parciales | ✅ | Reporte `inventario_estante` `reportes/service.py:50-54`, `reportes/model.py:63` | — | RF-16 |
| CTX-05 | Certificación ISO 9001:2015 | ⛔ | Objetivo institucional, no requisito de software. Aporta: procedimientos uniformes (D-02), trazabilidad vía bitácora | — | — |

### 3.2 Requerimientos funcionales (RF)

| ID | Requisito | Estado | Evidencia | Falta | Referencias cruzadas |
|---|---|---|---|---|---|
| RF-01 | Perfiles (6) | ✅ | CRUD `usuarios/controller.py:7-35`; 8 roles incl. `colaborador` `db/02_seed.sql:2-5` | — | PS-S0-01 |
| RF-02 | Roles y permisos | ✅ | `perfiles/service.py:10-27`, `perfiles/controller.py:13`, `core/auth.py:48-74`, matriz `db/02_seed.sql:17-28` | — | PS-S0-02, PS-NFR-05 |
| RF-03 | Alta/baja/modificación alumnos y profesores (sincronizado con Servicios Escolares) | ✅ | `usuarios/service.py:62-106`; actualización desde Servicios Escolares `:198-238`, importación CSV `:240-269`; `usuarios/simulado/servicios_escolares.json`; `fuente_validacion` `db/01_schema.sql:41-43` | — | PS-S0-03, PS-S0-11 |
| RF-04 | Historial de préstamos, renovaciones, multas, adeudos por usuario | ✅ | `usuarios/service.py:109-120`, `usuarios/controller.py:37`; UI `usuarios/web/view.js:85-103`; etiqueta corregida `:72` | — | PS-S0-04, PS-GEN-23 |
| RF-05 | Solicitud de compra con presupuesto mensual | ✅ | `compras/service.py:53-62,71-85,98-106`; barra `compras/web/view.js:10`; `GET /api/compras/presupuesto` `compras/controller.py:13` | — | RO-02 |
| RF-06 | Recepción de libros y factura, enlace a Tesorería | ✅ | `compras/service.py:109-149` (parcial/total, ejemplares, aviso `tesoreria`); estado `recibida` `db/01_schema.sql:90`; UI `compras/web/view.js:92-98` | Aviso a Tesorería simulado (D-11) | PS-S1-01 |
| RF-07 | Ficha bibliográfica y etiquetado de libros nuevos | ✅ | Etiqueta `catalogo/service.py:169-172`; imprimir/PDF `catalogo/web/controller.js:69-72`, `view.js:103-111`; pendientes `catalogo/service.py:175` | — | RO-03, PS-S1-02 |
| RF-08 | Alta de libros (autor, tema, título, clave, editorial, existencias) | ✅ | `catalogo/service.py:20-39,80-88`, `catalogo/controller.py:35` | — | PS-S1-03 |
| RF-09 | Asignar ubicación en librero (Bibliotecario) | ✅ | Ubicación en alta/edición `catalogo/service.py:67-77`; bibliotecario con `catalogo` `db/02_seed.sql:21-23` | — | PS-S1-03 |
| RF-10 | Marcar libros reservados o de consulta externa | ✅ | `tipo_uso` con `reservado` `db/01_schema.sql:115`, `catalogo/service.py:14`; `LIB007` `db/02_seed.sql:50`; no prestable `core/circulacion.py:98-99` | — | RF-18 |
| RF-11 | Baja/actualización de fichas de libros perdidos, robados, dañados, obsoletos | ✅ | `catalogo/service.py:146-166` (baja con motivo, reactivar), `ejemplar.motivo_baja` `db/01_schema.sql:147`; baja de libro `:110-122` | — | PS-S1-05 |
| RF-12 | Listado con filtros (autor, tema, título, clave, editorial, disponibilidad) | ✅ | `catalogo/controller.py:9-15`, `catalogo/model.py:32-45` | — | PS-S1-06 |
| RF-13 | Consulta por autor, tema, título, clave, editorial | ✅ | `catalogo/model.py:39` (6 columnas), sin acentos `core/repo.py:103,137`, UI `catalogo/web/controller.js:128` | — | PS-S1-08 |
| RF-14 | Existencia y ubicación física | ✅ | `catalogo/model.py:5-17`, ruta `libros/:id/ubicacion` `catalogo/web/controller.js:131`, móvil `:129-130` | — | PS-S1-08 |
| RF-15 | Disponibilidad en tiempo real (externo/interno) | ✅ | Cálculo vivo `catalogo/model.py:12-17`, `core/consultas.py:17`; filtro `disponibilidad` `catalogo/controller.py:11` | — | RNF-08 |
| RF-16 | Listas parciales de existencia (pantalla: Inventario por estante) | ✅ | `reportes/service.py:50-54` (planta/pasillo/librero/tema; existencia sin bajas, prestados, conteo físico), `reportes/model.py:63`; UI `reportes/web/view.js:12` | — | CTX-04, PS-S1-07 |
| RF-17 | Validar condición del solicitante (Regla 1) | ✅ | `POST /api/prestamos/validar` `prestamos/service.py:89-107`, `prestamos/controller.py:13` | — | RN-01, RNF-09 |
| RF-18 | Validar condición del libro | ✅ | `core/circulacion.py:97-104` (inactivo, no prestable, sin copias, reservado) | — | RN-01, RF-10 |
| RF-19 | Registro de préstamo y recibo (email, WhatsApp, impresión) | ✅ | `prestamos/service.py:111-166` (folio `REC-`, canales email/WhatsApp simulados); imprimir/PDF `prestamos/web/controller.js:91-92` | Envío simulado (D-11) | PS-S2-02, PS-S2-06, RNF-10 |
| RF-20 | Vigencia 5/10 días hábiles | ✅ | `core/calendario.py:18-45`, `core/circulacion.py:57-59` | — | RN-05, RN-06 |
| RF-21 | Renovación 2/3 autorizada por Administrador | ✅ | `prestamos/service.py:171-177` (autorización automática D-06; bitácora `prestamo_renovar`) | — | RN-02, RN-06 |
| RF-22 | Lista de espera | ✅ | `espera/service.py:22-106`, `core/espera.py:18-41`; UI `espera/web/controller.js:66-69`; pruebas `espera/tests/test_espera.py` | — | PS-S2-05 |
| RF-23 | Registro de devolución y actualización de disponibilidad | ✅ | `prestamos/service.py:182-197` (ejemplar `disponible`, `core/circulacion.py:245`) | — | PS-S2-07 |
| RF-24 | Validar fecha de vencimiento contra fecha actual | ✅ | `prestamos/service.py:188`; `core/circulacion.py:62-64,72-74` | — | PS-S2-08 |
| RF-25 | Multas por retraso, daño y pérdida | ✅ | Retraso `prestamos/service.py:193-195`; pérdida `adeudos/service.py:122-139`; daño `:142-160` | — | RN-03, RN-04, PS-S2-09 |
| RF-26 | Aviso automático a Servicios Escolares y Tesorería por pérdida | ✅ | `adeudos/service.py:134-135` (canales `servicios_escolares` y `tesoreria`) | Simulado (D-11) | PS-S2-10, PS-S2-12 |
| RF-27 | Registro de pago de multa | ✅ | `POST /api/adeudos/<id>/pago` `adeudos/service.py:90-103` (referencia 3-40, bitácora `adeudo_pago`); cancelar `:106-114` | — | PS-S2-11 |
| RF-28 | Lista de alumnos con adeudos en época de exámenes y aviso a Servicios Escolares | ✅ | `reportes/service.py:31-37,45-49,96-106`; botón `reportes/web/view.js:39`; `POST /api/reportes/con_adeudos/aviso` `reportes/controller.py:15` | — | PS-S2-10 |
| RF-29 | Chatbot: consultas frecuentes (horarios, políticas, ubicación, disponibilidad) | ✅ | `asistente/service.py:116-135` (intenciones + FAQ), `:162-169`; 16 intenciones y 11+ FAQ `db/02_seed.sql:67-100` | — | PS-S3-01 |
| RF-30 | Chatbot: apoyo en búsqueda de libros | ✅ | `asistente/service.py:137-145,246-256,266-272` (máx. 5, con disponibilidad y ubicación) | — | PS-S3-02 |
| RF-31 | Chatbot: estatus propio de préstamos, renovaciones, multas | ✅ | `asistente/service.py:211-245,273-279` (visitante: pide iniciar sesión) | — | PS-S3-03 |
| RF-32 | Chatbot: explicación de reglas | ✅ | `asistente/service.py:170-210` (lee `politica_prestamo`) | — | PS-S3-04 |
| RF-33 | Pasar la consulta a un Bibliotecario | ✅ | `asistente/service.py:257-264,356-374`; pantalla `asistente/web/controller.js:68-69`; `GET/POST /api/asistente/consultas` `asistente/controller.py:25-31` | — | PS-S3-05 |

### 3.3 Requerimientos no funcionales (RNF)

| ID | Requisito | Estado | Evidencia | Falta | Referencias cruzadas |
|---|---|---|---|---|---|
| RNF-01 | Autenticación usuario/contraseña | ✅ | `auth/service.py` (hash werkzeug), cookie HttpOnly/SameSite y `Secure` con `HTTPS=true` `config.py:17-19`; código de recuperación solo si `DEMO_MOSTRAR_TOKEN` `auth/controller.py:33-35`; pruebas `auth/tests/test_auth.py` | — | PS-S0-05, PS-NFR-05 |
| RNF-02 | Backup y restore | ✅ | `scripts/respaldo.py`, `scripts/restaurar.py` (`--verificar`), volumen `docker-compose.yml:12`; procedimiento y salida real `docs/operacion.md:16-68` | `backups/` está vacío ahora: repetir `respaldo.py` + `restaurar.py --verificar` en el E2E | PS-S0-06, PS-NFR-06 |
| RNF-03 | ≤ 3 s en gestión de usuarios | ✅ | `scripts/cargar_datos_volumen.py:50` (5 000 usuarios, 10 002 ejemplares, 20 664 préstamos); `scripts/medir_rendimiento.py:31-47`; usuarios p95 0.043 s / 0.276 s con 20 concurrentes; tope `?limite=` `core/repo.py:154-170`, `usuarios/model.py:13-17` | — | PS-NFR-01 |
| RNF-04 | Microservicios o APIs para entidades externas | ✅ | API REST por módulo (`app/modules/*/controller.py`); adaptador `core/notificaciones.py:22-40`; actualización desde Servicios Escolares `usuarios/service.py:198-238` | Conexión real ⛔ (PS-S4-08) | PS-TEC-08, PS-TEC-13 |
| RNF-05 | ≤ 3 s en mantenimiento y búsqueda | ✅ | Búsqueda sin acentos `core/repo.py`; `libros` p95 0.175 s y `libros?q=` 0.200 s (1.22 s / 1.32 s con 20 concurrentes) con el dataset de volumen; sin índices nuevos (planes con los existentes) | — | PS-NFR-01 |
| RNF-06 | Interfaz multiplataforma, amigable (discapacidad visual) | ✅ | `lang="es"`, saltar al contenido `index.html:2,16`; región `aria-live` persistente `#toast` (`index.html:19`, `core/ui.js:49-55`, `css/components.css:473-495`); `:focus-visible` `css/base.css:125`; `aria-*` en `components/form.js`, `modal.js`, `notice.js`; vista móvil. Auditoría E2E en Chrome (sección 9): etiquetas, nombres accesibles, alt, trampa de foco, contraste ≥ 4.5:1 (`--good #256b29`, `--warn #9a5700`), 390 px sin desbordamiento en 29 rutas | Prueba con lector de pantalla real (solo se verificó el árbol de accesibilidad) | PS-S1-10, PS-NFR-04 |
| RNF-07 | Navegación ≤ 3 clics | ✅ | Menú lateral `core/layout.js`; prestar/devolver/renovar/pago `prestamos/web/controller.js`, `adeudos/web/controller.js`; crear y enviar solicitud en 3 clics con "Guardar y enviar" `compras/web/controller.js:44-57`, `compras/web/view.js:53`; tabla `docs/operacion.md` sección 6; los 7 procesos verificados en Chrome (sección 9) | — | PS-NFR-03 |
| RNF-08 | Catálogo en tiempo real | ✅ | Sin caché, disponibilidad de `ejemplar` `catalogo/model.py:12-17`; `uq_prestamo_ejemplar_abierto` `db/01_schema.sql:179`; `FOR UPDATE SKIP LOCKED` `prestamos/model.py:50-68`; prueba de concurrencia `test_prestamos.py:222` | — | PS-S1-09, PS-NFR-07 |
| RNF-09 | Validación automática (Reglas 1, 2, 5, 6) | ✅ | `core/circulacion.py:77-126,188-227` única fuente; la usan prestamos, espera, adeudos, asistente | — | RN-01, RN-02, RN-05, RN-06 |
| RNF-10 | Notificación de estatus del préstamo (email/WhatsApp) | ✅ | `core/notificaciones.py:22-40`; recibo `prestamos/service.py:128-142`; lista de avisosja `notificaciones/service.py:18-27`, UI "Simulado" `notificaciones/web/view.js:34` | Simulado (D-11) | PS-S2-06 |
| RNF-11 | ≤ 3 s en préstamos/devoluciones | ✅ | `medir_rendimiento.py:127-175` (`--escritura`: crear, renovar, devolver, pagar): p95 0.064 / 0.052 / 0.042 / 0.042 s con el dataset de volumen; listado `prestamos` 0.053 s (0.425 s con 20 concurrentes) | — | PS-NFR-01 |
| RNF-12 | Disponibilidad 24/7 del chatbot | ✅ | `restart: unless-stopped` `docker-compose.yml:4,23`; healthchecks `:13-18,36-41`, `Dockerfile:9`; `GET /api/health` `info/controller.py:9` | — | PS-S3-06, PS-NFR-02 |
| RNF-13 | ≤ 3 s en chatbot | ✅ | `asistente/mensajes` p95 0.033 s (0.223 s con 20 concurrentes) con el dataset de volumen; sin llamadas externas | — | PS-NFR-01 |
| RNF-14 | Integración multiplataforma (Web y App) del chatbot | ✅ | Ruta móvil `asistente/web/controller.js:67`; canal `movil` `db/01_schema.sql:228`, `asistente/service.py:28` | App nativa ⛔ (U7) | PS-S3-09 |

### 3.4 Propuesta por sprint (PS)

| ID | Requisito | Estado | Evidencia | Falta | Referencias cruzadas |
|---|---|---|---|---|---|
| PS-GEN-01 | Plataforma integral (portal web, acceso móvil, integraciones) | 🟡 | Portal web + vista móvil + 13 módulos | Integraciones reales ⛔ (simuladas) | PS-S4-08 |
| PS-GEN-02 | Revisión por sprint con criterios de aceptación | ✅ | Criterios por paquete en la sección 6 (ejecutados) | PO debe aceptar | — |
| PS-GEN-03 | Alcance: usuarios, catálogo, búsqueda, préstamos, devoluciones, multas, notificaciones, chatbot | ✅ | `app/modules/{usuarios,catalogo,prestamos,adeudos,notificaciones,asistente}` | — | RF-17..33 |
| PS-GEN-06 | Metas: ≤ 3 s, tiempo real, ≤ 3 clics, chatbot 24/7, validación automática | ✅ | Ver RNF-03/05/07/08/09/12: medición con volumen y 3 clics verificados | — | RNF |
| PS-GEN-07 | Solución modular con trazabilidad e integración segura | ✅ | Módulos verticales; `@audit` `core/bitacora.py:22`; acciones `prestamo_*`, `espera_*`, `adeudo_*`, `asistente_*`, `compra_*`, `ejemplar_*` | — | PS-GEN-23 |
| PS-GEN-09 | Arquitectura modular y APIs definidas | ✅ | `register_modules` `core/module.py:14-23`, `app/__init__.py:21`; API en `README.md` | — | — |
| PS-GEN-10 | Módulo de usuarios completo | ✅ | Perfiles, altas, historial `usuarios/service.py:109`, colaborador `db/02_seed.sql:5`, respaldo | — | RF-03/04, PS-S0-01/06 |
| PS-GEN-11 | Catálogo y mantenimiento del acervo | ✅ | Ver RF-05..11 | — | — |
| PS-GEN-12 | Búsqueda multiplataforma | ✅ | RF-13..15; "App" = vista móvil (U7) | — | — |
| PS-GEN-13 | Préstamos y devoluciones con reglas, recibos, espera, multas, pagos | ✅ | `prestamos`, `espera`, `adeudos` | — | — |
| PS-GEN-14 | Integraciones institucionales y notificaciones | 🟡 | Notificaciones simuladas `core/notificaciones.py:22-40`; lista de alumnos simulado | Conexión real ⛔ | PS-S2-12 |
| PS-GEN-15 | Chatbot 24/7 | ✅ | `asistente` + `restart` (RNF-12) | — | RF-29..33 |
| PS-GEN-16 | Web completa; app solo búsqueda y chatbot; RBAC | ✅ | RBAC `core/auth.py:48-74`; `movil` y `movil/asistente` | App nativa ⛔ (U7) | PS-TEC-11 |
| PS-GEN-17 | Catálogo y disponibilidad sincronizados | ✅ | Ver RNF-08 | — | — |
| PS-GEN-18 | Validación automática uniforme | ✅ | `core/circulacion.py` única fuente | — | RNF-09 |
| PS-GEN-19/20/21/22 | ≤ 3 s; ≤ 3 clics; notificaciones; atención 24/7 | ✅ | Ver RNF-03/07/10/12 (notificaciones simuladas, D-11) | — | — |
| PS-GEN-23 | Trazabilidad, historial por usuario, evidencia | ✅ | `bitacora` en circulación; historial `usuarios/service.py:109-120` | — | — |
| PS-MET-01 | Registrar préstamo/devolución en < 1 min | 🟡 | Flujo de 3 clics con validación en vivo; el servidor responde en 0.06 s (RNF-11) | Cronometraje con usuarios en mostrador | CTX-03, PS-S2-13 |
| PS-MET-02 | Discrepancias < 1 % con trazabilidad por ejemplar | ✅ | Reporte `indicadores`: ejemplares «prestado» sin préstamo abierto, «disponible» con préstamo abierto, libros activos sin ejemplares y % de discrepancias `reportes/service.py:45-70`, `reportes/model.py:90-100`; pruebas `reportes/tests/test_reportes.py` (`test_indicadores_discrepancias_de_inventario`); el dataset de volumen arroja 0 discrepancias | La meta se mide con inventario físico real (`inventario_estante`) | RF-16 |
| PS-MET-03 | Chatbot absorbe ~40 % de consultas | ✅ | Reporte `indicadores`: % resueltas sin pasar a bibliotecario, % atendidas sin pasar a bibliotecario y consultas para el bibliotecario pendientes `reportes/service.py:45-70`, `reportes/model.py:80-88`, `core/consultas.py` (`CON_BIBLIOTECARIO`); prueba `test_indicadores_asistente_y_periodos` | — | PS-S3-08 |
| PS-MET-04 | Conciliación de pagos mismo día | ✅ | Pago con fecha y referencia al instante `adeudos/service.py:90-103` | Tesorería real ⛔ | PS-S2-12 |
| PS-MET-05 | Consulta continua Web/App | ✅ | `restart: unless-stopped` `docker-compose.yml:4,23` | — | RNF-12 |
| PS-S0-01 | Perfiles alumno, profesor, colaborador, bibliotecario, administrador | ✅ | 8 roles `db/02_seed.sql:2-5` | — | RF-01 |
| PS-S0-02 | RBAC mínimo privilegio | ✅ | `core/auth.py:48-74`, `perfiles/service.py:10-27` | — | RF-02 |
| PS-S0-03 | Altas, bajas, cambios | ✅ | `usuarios/service.py:62-106` | — | RF-03 |
| PS-S0-04 | Historial por usuario | ✅ | Ver RF-04 | — | — |
| PS-S0-05 | Autenticación, JWT, hash seguro | ✅ / ⛔ JWT | Hash `auth/service.py:55,92`; JWT ⛔ por U1 (cookie de sesión) | — | RNF-01 |
| PS-S0-06 | Backup/restore con prueba documentada | ✅ | `docs/operacion.md:16-68`, `scripts/respaldo.py`, `scripts/restaurar.py` | — | RNF-02 |
| PS-S0-07 | Hito: base segura y operativa | ✅ | S0 funcional con respaldo | — | — |
| PS-S0-08 | Taller de reglas / matriz de decisión validada por PO | 🟡 | Sección 2 de este documento y hoja de revisión con firma `docs/requisitos/decisiones_para_validacion.md` (0 de 29 firmadas) | Validación y firma del PO (no se cierra desde el código) | PS-S2-15, PS-RIE-01 |
| PS-S0-11 | Importación del lista de alumnos | ✅ | `usuarios/service.py:240-269`, actualización `:198-238`; UI `usuarios/web/controller.js:52-80` | — | RF-03 |
| PS-S1-01 | Solicitud y recepción de material | ✅ | `compras/service.py:71-85,109-149` | — | RF-06 |
| PS-S1-02 | Ficha bibliográfica completa | ✅ | Campos `db/01_schema.sql:105-121`; ficha imprimible `catalogo/web/view.js:103-111` | — | RF-07 |
| PS-S1-03 | Alta y ubicación física | ✅ | `catalogo/service.py:80-88` | — | RF-08, RF-09 |
| PS-S1-04 | Control de estados del ejemplar | ✅ | `ejemplar.estado` `db/01_schema.sql:144`; listado/baja/reactivar `catalogo/service.py:129-166`, UI `catalogo/web/view.js:85-96` | — | — |
| PS-S1-05 | Bajas y actualizaciones | ✅ | Ver RF-11 | — | — |
| PS-S1-06 | Filtros | ✅ | Ver RF-12 | — | — |
| PS-S1-07 | Inventarios parciales | ✅ | Ver RF-16 | — | — |
| PS-S1-08 | Búsqueda por 5 criterios; App y Web | ✅ (Web) / ⛔ (App nativa) | RF-13..15; U7 | — | — |
| PS-S1-09 | Catálogo en tiempo real con concurrencia | ✅ | Ver RNF-08 | — | — |
| PS-S1-10 | Accesibilidad | ✅ | Ver RNF-06 (auditoría E2E) | — | — |
| PS-S1-11 | Caché Redis | ⛔ | U2 (sin Redis; consultas directas a PostgreSQL) | — | — |
| PS-S1-12 | Diagnóstico de datos y carga de prueba | ✅ | Importación CSV con errores por línea `catalogo/service.py:183-200`; dataset de carga `scripts/cargar_datos_volumen.py` (verifica mínimos y discrepancias) | — | PS-RIE-03 |
| PS-S2-01 | Validaciones automáticas por tipo de usuario | ✅ | Ver RN-01 | — | — |
| PS-S2-02 | Recibos | ✅ | Ver RF-19 | — | — |
| PS-S2-03 | Control de vigencias | ✅ | Ver RF-20 | — | — |
| PS-S2-04 | Renovaciones | ✅ | Ver RF-21 | — | — |
| PS-S2-05 | Lista de espera | ✅ | Ver RF-22 | — | — |
| PS-S2-06 | Notificaciones email y WhatsApp | ✅ | lista de avisos simulada (D-11), ver RNF-10 | Simulado | — |
| PS-S2-07..11 | Disponibilidad, vencimientos, multas, avisos, pagos | ✅ | Ver RF-23..28 | — | — |
| PS-S2-12 | Integración Tesorería/Servicios Escolares (servicios simulados en S2) | 🟡 | Adaptadores simulados `core/notificaciones.py`, `adeudos/service.py:134-135`, `reportes/service.py:103` | Conexión real ⛔ | RF-26 |
| PS-S2-13 | Registro < 1 min | 🟡 | Ver PS-MET-01 | Cronometraje con usuarios | — |
| PS-S2-15 | Precondición: matriz de reglas validada | 🟡 | Sección 2; hoja de firma `docs/requisitos/decisiones_para_validacion.md` | Firma del PO | PS-S0-08 |
| PS-S3-01 | FAQ | ✅ | `info/controller.py:4`, FAQ en el asistente `asistente/service.py:162-169` | — | — |
| PS-S3-02..05 | Búsqueda, estatus, reglas, paso a bibliotecario | ✅ | Ver RF-30..33 | — | — |
| PS-S3-06 | 24/7 con monitoreo y reinicio automático | ✅ | Reinicio y healthchecks `docker-compose.yml`; errores: 500 del servidor `core/errors.py:43-48`, errores JS `web/js/core/errores.js` + `POST /api/errores` `modules/errores/controller.py`, almacenamiento y límite `core/errores.py:32-60`, vista Reportes → Errores `reportes/service.py:73-79`; pruebas `errores/tests/test_errores.py` (7) | — | RNF-12 |
| PS-S3-07 | Motor híbrido de intents + base de conocimiento | ✅ | `asistente/service.py:50-135` (palabras clave + similitud Dice con FAQ); tablas `db/01_schema.sql:218-255` | — | — |
| PS-S4-01 | Regresión | ✅ | 219 pruebas `pytest` (`pytest.ini`, `app/core/tests/`, `app/modules/*/tests/`) | — | todos |
| PS-S4-02 | UAT | 🟡 | Guion formal por rol `docs/uat.md` (58 casos, resultados del E2E 2026-10-27) | Ejecución y firma de usuarios reales | — |
| PS-S4-03 | Seguridad (TLS, registros de acceso, permisos) | 🟡 | Registros `bitacora`; permisos en servidor `core/auth.py`; gunicorn `--access-logfile` `Dockerfile:12`; token de recuperación tras `DEMO_MOSTRAR_TOKEN` `config.py:31`, `auth/controller.py:33-35`; cookie `Secure` con `HTTPS` `config.py:19`; TLS por proxy documentado `docs/operacion.md` sección 7 | TLS no se despliega aquí (proxy inverso, fuera de alcance) | PS-NFR-05 |
| PS-S4-04 | Rendimiento | ✅ | `scripts/medir_rendimiento.py` (lecturas y `--escritura`), `scripts/cargar_datos_volumen.py`; resultados `docs/operacion.md` sección 3 | — | RNF-03 |
| PS-S4-05 | Despliegue Docker reproducible | ✅ | `docker-compose.yml`, `Dockerfile`, `scripts/levantar.py`, `scripts/recrear_db.py` | — | PS-TEC-07 |
| PS-S4-06/07 | Capacitación y documentación | ✅ | `README.md`, `docs/operacion.md`, READMEs de `core` y `components`; Guía y Funciones leen `MODULES` (`app/modules/info/web/view.js:22,37`) con los 9 módulos de interfaz: usuarios, buscar, préstamos, espera, adeudos, compras (incl. recepción), reportes (incl. indicadores e errores), notificaciones y asistente (`app/modules/info/web/model.js:32-48`) | Capacitación con usuarios reales: ver `docs/uat.md` | integración final |
| PS-S4-08 | Conexión real a Servicios Escolares y Tesorería | ⛔ | Sin credenciales/servicios (D-11, D-23); queda simulada | — | PS-RIE-02 |
| PS-NFR-01 | Rendimiento ≤ 3 s | ✅ | Ver RNF-03/05/11/13: p95 máx. 0.281 s una a una y 2.430 s con 20 concurrentes (volumen D-15) | — | — |
| PS-NFR-02 | Disponibilidad chatbot | ✅ | Ver RNF-12 | — | — |
| PS-NFR-03 | ≤ 3 clics | ✅ | Ver RNF-07 | — | — |
| PS-NFR-04 | Accesibilidad | ✅ | Ver RNF-06 | — | — |
| PS-NFR-05 | Seguridad (cifrado en tránsito, roles, mínimo privilegio, auditoría) | 🟡 | Roles y bitácora ✅; cookie `Secure`/`HttpOnly`/`SameSite`; token de recuperación configurable (PS-S4-03) | TLS por proxy (documentado, no desplegado) | — |
| PS-NFR-06 | Respaldo | ✅ | Ver RNF-02 | — | — |
| PS-NFR-07 | Consistencia | ✅ | Ver RNF-08 | — | — |
| PS-TEC-01 | Frontend React + TypeScript | ⛔ | U2 (vanilla JS/CSS, sin build) | — | — |
| PS-TEC-02 | App React Native / Expo | ⛔ | U7 (vista web móvil) | — | — |
| PS-TEC-03 | Backend Node/NestJS/Express | ⛔ | U1 (Flask) | — | — |
| PS-TEC-04 | PostgreSQL | ✅ | `db/01_schema.sql`, `docker-compose.yml:3`; auditoría vía `bitacora` | — | — |
| PS-TEC-05 | Redis | ⛔ | U2 | — | — |
| PS-TEC-06 | JWT + RBAC | ⛔ (JWT) / ✅ (RBAC) | Cookie de sesión `core/auth.py:9-14`, `config.py:7-9` | — | — |
| PS-TEC-07 | Docker + nube, backups, monitoreo | ✅ | Docker, `restart`, healthchecks, respaldos | Despliegue en nube fuera de alcance | — |
| PS-TEC-08 | REST/webhooks para integraciones | 🟡 | REST interna por módulo; externas simuladas | Webhooks/integración real ⛔ | — |
| PS-TEC-09 | Chatbot híbrido | ✅ | Ver PS-S3-07 | — | — |
| PS-TEC-11/12/13 | Móvil limitado; API REST documentada; adaptadores intercambiables | ✅ | Vista móvil; API en `README.md` (tabla de módulos); `core/notificaciones.py:22-40` | — | — |
| PS-ALC-01..06 | Alcance funcional (usuarios, catálogo, préstamos, integraciones, chatbot, web+app) | 🟡 | Ver filas anteriores | Integraciones reales y app nativa ⛔ | — |
| PS-ALC-07 | QA, UAT, seguridad, rendimiento, despliegue, capacitación, manuales | 🟡 | Ver PS-S4 | UAT, TLS, medición ampliada | — |
| PS-ALC-08 | Alcance base = matriz del cliente | ✅ | Este documento parte de la matriz | — | — |

---

## 4. Fuera del alcance del software (gestión de proyecto / contractual)

PS-META-01..07, PS-GEN-04/05/08 (duración, capacidad, inversión, objetivos de carta), PS-MET-10..16 (ceremonias Scrum), PS-DOD-01..06 (definición de terminado: se aplica como proceso; DoD-05 = RNF verificados), PS-TEC-10 y PS-DOD-03 (Git y revisión de código: el directorio **no es un repositorio git**; ejecutar `git init` es recomendable), PS-CAP-01/02, PS-RIE-01..07 (riesgos de proyecto; RIE-05 se mitiga con el adaptador de notificaciones), PS-SUP-01..07 (supuestos del cliente), PS-PRC-01..04, PS-TYC-01..12, PS-ALC-09..14 (exclusiones comerciales), PS-S0-09/10 (línea base de indicadores, infraestructura), PS-S4-09/10/11 (holgura, hito, garantía), firmas de conformidad, RF-sin-IDs/A-1 (criterios de aceptación se definen aquí), D-18 (revistas, puerta, libreros físicos).

---

## 5. Contratos transversales y paquete P0 (fundación) — **P0 COMPLETADO**

> **Estado de ejecución (secciones 5 a 8): EJECUTADO.** P0 y los paquetes A, B, C, D, E1, E2, F, G y H están implementados y con pruebas (219 pasan); la integración (I) quedó parcial: `README.md` e `info/web/view.js` (Guía y Funciones) por completar. La sección 5 documenta los contratos tal como se entregaron; las secciones 6 y 7 se conservan como registro del plan.
>
> | Paquete | Módulo / entregable | Estado |
> |---|---|---|
> | P0 | Esquema S-1..S-5, semilla, `core/*`, shell del frontend | ✅ hecho |
> | A | `prestamos` (validar, prestar, renovar, devolver, recibo, políticas) | ✅ hecho |
> | B | `espera` (alta, cancelación, expiración, autoservicio) | ✅ hecho |
> | C | `adeudos` (pago, cancelación, pérdida, daño, reposición) | ✅ hecho |
> | D | `asistente` (chatbot por reglas, consultas para el bibliotecario, vista móvil) | ✅ hecho |
> | E1 | `compras` (presupuesto, cancelar, recepción y factura) | ✅ hecho |
> | E2 | `catalogo` (ejemplares, baja/reactivar, etiqueta, pendientes, importar) | ✅ hecho |
> | F | `usuarios` (historial, actualización desde Servicios Escolares, importación CSV) | ✅ hecho |
> | G | `reportes` + `inicio` (alumnos con adeudos, inventario por estante, vencidos, préstamos, tablero) | ✅ hecho |
> | H | `notificaciones` + `scripts/respaldo.py`, `restaurar.py`, `medir_rendimiento.py`, `docs/operacion.md`, `restart` en compose | ✅ hecho |
> | I | Integración final: `README.md` reescrito; `info/web/view.js` pendiente | 🟡 parcial |
>
> **Desviaciones respecto al plan (aditivas, no contradicen los contratos):** `espera` agrega `GET /api/espera/libros`, `GET /api/espera/mias` y `POST /api/espera/unirse` (autoservicio de sesión); `adeudos` agrega `GET /api/adeudos/<id>` y `GET /api/adeudos/prestamo/<id>` (previsualización); `catalogo` agrega `GET/POST` de importación y pendientes; `GET /api/politicas` exige `prestamos` o `perfiles`; la ruta `politicas` vive en `prestamos` con permiso `perfiles`.

P0 se ejecutó primero y solo. Tras P0 **los archivos compartidos no pertenecen a ningún paquete**: ningún paquete A–H edita `db/*`, `app/seed.py`, `app/config.py`, `app/core/*`, `app/web/js/core/*`, `app/web/js/components/*` (incluye `labels.js`), `app/web/css/*`, `app/web/js/main.js`, `layout.js`, `conftest.py`, `app/testing.py`, `pytest.ini`, `scripts/levantar.py`, `scripts/recrear_db.py`. Si un paquete necesita algo ahí, lo dice en su informe (la fase de integración I lo aplica).

### 5.1 Qué dejó P0 (estado real del código)

| Área | Entregado |
|---|---|
| `db/01_schema.sql` | Adiciones S-1..S-5 (sección 8) con comentarios "Adición al diseño" y cabecera resumen |
| `db/02_seed.sql` | Rol `colaborador`; permisos `prestamos espera adeudos asistente notificaciones` (15 en total); matriz 5.3; políticas (alumno 5/2/2/$10, docente 10/3/3/$10, resto `activa=false`); 16 intenciones; 14 FAQ corregidas; libro `LIB007` (`reservado`) |
| `app/seed.py` | `COL001`/`Colabora123`, `A0513001` (Laura); demo: María 1 préstamo activo (LIB001) + espera en LIB005; Carlos préstamo **vencido** (LIB005, `estado='vencido'`); Laura préstamo devuelto con 2 días hábiles de retraso + adeudo `retraso` $20 **pendiente**; DOC001 3 préstamos (LIB001, LIB002, LIB005); `SOL000` recibida (FAC-2026-001; LIB001 a 42 USD, LIB002 a 30 USD) y `SOL001` pendiente. Vencimientos en días hábiles vía `core.circulacion` |
| `app/config.py` | `TIPO_CAMBIO_USD_MXN` (18.00), `PRESUPUESTO_MENSUAL_USD` (5000), `ESPERA_DIAS_RESERVA` (2); se leen con `core/parametros.py` |
| `app/core/` | `errors.py` (`ApiError(msg, status, extra)`, `ApiError.reglas`, `motivo`, `exigir`), `calendario.py`, `parametros.py`, `notificaciones.py`, `circulacion.py` (5.2); pruebas en `app/core/tests/test_{calendario,parametros,notificaciones,circulacion}.py`; `app/core/README.md` actualizado |
| Frontend shell | `main.js`: importación dinámica y tolerante de `/m/<m>/controller.js` (lista `MODULES`; un módulo ausente o roto se registra con `console.warn` y se omite); `core/router.js::hasRoute`; `core/layout.js` NAV con todos los módulos, visibles solo con permiso **y** ruta registrada |
| Componentes | `labels.js` con todos los enums nuevos; nuevos genéricos `receiptBlock` (detail.js), `meter` (meter.js), `chatBubble/chatPanel/appendChat/bindChat` (chat.js) + CSS; `components/README.md` actualizado |
| Pruebas / scripts | `conftest.py`: limpieza de `mensaje, conversacion, lista_espera`; fixtures `bibliotecario docente colaborador alumno2`; `perfiles` espera 15 permisos; `scripts/recrear_db.py` aplica todos los `db/*.sql` en orden (`--sin-semilla` omite los `*seed*`); `levantar.py` y cuentas demo (`auth/web/model.js`, README) incluyen `COL001` |
| Pendiente de otros dueños (al cierre de P0) | `docker-compose.yml`/`Dockerfile` (H: **hecho**, `restart`, volumen `./backups`, variables nuevas pasadas a `web`), `README.md` (**hecho**) e `info/web/*` (I: **pendiente**, Guía y Funciones sin los módulos nuevos) |

Nota: el código de `web` se copia en la imagen (no hay volumen); tras editar código ejecutar `python3 scripts/levantar.py` antes de `docker compose exec -T web pytest`. Los precios de `libro.precio_referencia`/`SOL001` de la semilla (850/800) se conservan porque las pruebas existentes los afirman; se interpretan como USD (D-28).

### 5.2 API interna de núcleo (firmas fijas; todos los paquetes la importan, nadie la reimplementa)

```python
# app/core/calendario.py  (D-03: lun-vie; festivos cuentan; el dia `desde` no se cuenta)
es_habil(d) -> bool
sumar_habiles(desde, n) -> date            # n>=0; sabado/domingo: el lunes es el dia 1
habiles_entre(desde, hasta) -> int         # (desde, hasta]; 0 si hasta <= desde

# app/core/parametros.py  (necesitan app context o usan Config)
tipo_cambio() -> Decimal ; presupuesto_mensual() -> Decimal ; dias_reserva_espera() -> int

# app/core/notificaciones.py  (D-11) CANALES = (email, whatsapp, servicios_escolares, tesoreria)
enviar(canal, asunto, cuerpo, id_usuario, destino=None)    # bitacora accion='notif_<canal>', detalle="<destino>|<asunto>: <cuerpo>"[:200]
enviar_a_usuario(canal, asunto, cuerpo, id_usuario)        # destino = correo (email) o matricula
validar_canales(lista|None, por_defecto=("email",)) -> list   # 400 si hay canal invalido
parsear(accion, detalle) -> {canal, destino, asunto, cuerpo}   # lo usa H para listar

# app/core/errors.py
ApiError(message, status=400, extra=None) ; ApiError.reglas(motivos, message) ; motivo(codigo, mensaje) ; exigir(motivos, message)
#   exigir([]) no hace nada; con motivos -> 422 {"error", "motivos":[{codigo, mensaje}]}

# app/core/circulacion.py  (RN-01..RN-06, D-01..D-09, D-24). Detalle y ejemplos: app/core/README.md
# puras:
fecha_vencimiento(fecha_prestamo, dias) ; dias_retraso(venc, hasta) ; multa_retraso(dias, tarifa) -> Decimal
esta_vencido(venc, devolucion, hoy) ; fecha_renovacion(venc_actual, dias) ; limite_reserva(desde=None) -> datetime
evaluar_prestamo(*, usuario_activo, politica, prestamos_abiertos, vencidos, adeudos_pendientes, libro_activo,
                 tipo_uso, disponibles, reservados=0, usuario_notificado=False) -> [motivo]
evaluar_renovacion(*, abierto, vencido, num_renovaciones, max_renovaciones, adeudos_pendientes, espera_activa) -> [motivo]
valor_reposicion_mxn(valor_usd, tipo_cambio) ; monto_danio(monto_reposicion, porcentaje=50) ; redondear(x)
# con BD (solo lectura):
politica_vigente(id_rol) ; contexto_usuario(id_usuario, hoy=None) ; contexto_libro(id_libro, id_usuario=None)
autorizar_prestamo(id_usuario, id_libro, hoy=None) -> {autorizado, motivos, usuario, politica, libro, disponibles,
        reservados, prestamos_abiertos, vencidos, adeudos_pendientes, adeudos_monto, suspendido, dias_prestamo,
        fecha_vencimiento_estimada}
autorizar_renovacion(id_prestamo, hoy=None) -> {permitido, motivos, prestamo, max_renovaciones, dias_prestamo,
        nueva_fecha_vencimiento, dias_retraso}      # usa la politica con la que se creo el prestamo (D-05)
valor_reposicion(id_libro, tipo_cambio=None) -> {id_libro, valor_usd, fuente, tipo_cambio, monto_mxn}
# codigos de motivo = constantes del modulo: USUARIO_INACTIVO SIN_POLITICA MULTAS_PENDIENTES PRESTAMOS_VENCIDOS
#   LIMITE_EJEMPLARES LIBRO_INACTIVO LIBRO_NO_PRESTABLE LIBRO_NO_DISPONIBLE LIBRO_RESERVADO_OTRO_USUARIO
#   PRESTAMO_CERRADO PRESTAMO_VENCIDO MAX_RENOVACIONES LISTA_ESPERA
```

**Quién escribe qué (tablas compartidas).** `prestamo`/`renovacion`/`ejemplar.estado`: A (C cierra préstamo por pérdida/daño; E2 solo baja/reactiva ejemplares no prestados). `adeudo`: A inserta `retraso` al devolver; C inserta `perdida`/`danio`/`retraso` por pérdida y cambia estado (pago/cancela). `lista_espera`: B alta/cancelación/renumeración/expiración; A transiciones `notificado` (al devolver) y `recogido` (al prestar). `solicitud_compra`/`detalle_solicitud`: E1; E2 solo enlaza `detalle_solicitud.id_libro`. `usuario`: F. `bitacora`: todos vía `core.bitacora`; H solo lee. `conversacion/mensaje`: D. `reporte_generado`: G. Los demás paquetes **leen** estas tablas con SQL propio solo para listados; toda decisión de negocio sale de `core.circulacion`.

**Convenciones comunes.** Errores `{"error": "..."}`; reglas incumplidas → **422** con `motivos` (`exigir`); conflicto de estado → 409; inexistente → 404 (`repo.get_or_404`); validación → 400 (`validate`). Fechas ISO; importes numéricos (`JSONProvider` convierte `Decimal`). Acciones de bitácora ≤ 40 caracteres con prefijo del módulo: `prestamo_*`, `espera_*`, `adeudo_*`, `asistente_*`, `compra_*`, `ejemplar_*`, `usuario_*`, `notif_*` (solo `core.notificaciones`). **"Vencido" = D-24.** Un módulo no importa el `model/service` de otro, salvo `app.modules.catalogo.model.add_ejemplares` (estable) y `app.core.*`; la integración es por SQL y por `core.circulacion`.

**Plantilla obligatoria de un módulo nuevo** (backend): `__init__.py` = `from app.core.module import make_blueprint` + `bp = make_blueprint(__name__)` (se registra solo); `model.py` (SQL con `repo`), `service.py` (esquemas `validate(...)`, reglas, `@audit`/`log`), `controller.py` (`from . import bp`; solo `body()`, `query_args()`, `created()`, `@permission_required`/`@login_required`). Frontend: `web/model.js` (solo `api`), `web/view.js` (puro, componentes de `/js/components/index.js`), `web/controller.js` (`export const routes = [{path, perm, section, action}]`, `listPage`/`editPage`/`bindToggle`/`bindForm`/`onAction`/`confirmAction`). Nada de HTML/CSS ad hoc, mapas de etiquetas propios ni tablas/formularios propios; etiquetas con `statusBadge/label/labelItems` (5.1). El nombre del módulo debe estar en `MODULES` de `main.js` (ya están todos) y su `section` = clave de menú del NAV.

### 5.3 Permisos y matriz rol-permiso (semilla P0, ya aplicada)

Permisos (15): `inicio usuarios perfiles catalogo compras reportes buscar design guia funciones prestamos espera adeudos asistente notificaciones`. Nombre de permiso = clave de menú = `section` de las rutas.

| Rol | Permisos |
|---|---|
| admin | todos (15) |
| bibliotecario | inicio, catalogo, reportes, buscar, prestamos, espera, adeudos, asistente, notificaciones, design, guia, funciones (12) |
| catalogo | inicio, catalogo, reportes, buscar, asistente, design, guia, funciones |
| comprador | inicio, compras, buscar, asistente, design, guia, funciones |
| colaborador | inicio, catalogo, compras, reportes, buscar, asistente, design, guia, funciones (9) |
| alumno, docente, visitante | inicio, buscar, asistente, design, guia, funciones |

Nota: los endpoints `asistente/*` exigen permiso `asistente`; el visitante lo tiene pero sin consultas de estado propio (D-26). El tablero del bibliotecario usa `prestamos`; la lista de consultas para el bibliotecario usa `prestamos`.

Semilla de políticas: alumno `dias_prestamo=5, max_libros=2, max_renovaciones=2, multa_diaria=10.00`; docente `10, 3, 3, 10.00`; `admin/catalogo/bibliotecario/comprador/colaborador` con fila `activa=false` (valores de referencia 5/2/2/$10; sin política activa → `SIN_POLITICA`). Intenciones sembradas: `saludo buscar_libro horarios prestamo renovacion multas recuperar_contrasena solicitar_compra despedida ayuda reglas ubicacion estatus_prestamos estatus_multas pasar_a_bibliotecario no_entendido`.

### 5.4 Shell frontend (ya aplicado)

Ver 5.1. Contrato para los módulos: exportar `routes` desde `/m/<m>/controller.js`; si el módulo falla al importarse se omite sin romper la app. La entrada de menú aparece cuando existe permiso y alguna ruta con ese `path` exacto (p. ej. `prestamos`, `espera`, `adeudos`, `asistente`, `notificaciones`, `reportes`, `compras`, `catalogo`, `usuarios`, `perfiles`). Rutas móviles/bare (`bare: true`) no pasan por el menú.

Criterio de aceptación de P0 (verificado): `docker compose exec -T web pytest` → 101 pruebas pasaban en P0 (hoy 219); `scripts/recrear_db.py -y` aplica todos los `db/*.sql` + semilla; `/api/me` del administrador devuelve 15 permisos; `node --check` OK en todos los `.js`.

---

## 6. Paquetes de trabajo (paralelizables tras P0) — **EJECUTADOS**

Plan original conservado como referencia; ver el estado de ejecución en la sección 5.

Cada paquete **solo** crea/edita los archivos listados (los módulos existentes —compras, catalogo, usuarios, reportes, inicio— son propiedad exclusiva de su paquete, incluidos sus `view.js`). Las pruebas viven en `tests/` del módulo (nombres únicos `test_<módulo>*.py`; pueden agregar `tests/conftest.py` propio; fixtures disponibles en 5.1/`app/core/README.md`). **Reglas para todos:** (1) plantilla de módulo de 5.2 y reutilización obligatoria de `app/core/*` y `/js/components/*` (sin SQL dinámico propio donde exista `repo`, sin validación a mano donde exista `validate`, sin HTML de tablas/formularios/badges propios); (2) reglas de circulación solo vía `core.circulacion` (5.2); (3) etiquetas nuevas **no** se agregan: ya están en `labels.js` (si falta una, se reporta); (4) no editar archivos compartidos (5); (5) cada paquete entrega pruebas propias y un fragmento de documentación en su informe; (6) módulos nuevos se prueban con `docker compose exec -T web pytest app/modules/<m>` tras `python3 scripts/levantar.py`.

### Paquete A — `prestamos` (circulación núcleo) · cubre RN-01, RN-02, RN-03 (retraso), RN-05, RN-06, RF-17..21, RF-23..25 (retraso), RNF-08/09/10/11, PS-S2-01..04, 07..09, 13, PS-MET-01

**Archivos (módulo nuevo):** `app/modules/prestamos/{__init__.py, model.py, service.py, controller.py}`, `app/modules/prestamos/web/{model.js, view.js, controller.js}`, `app/modules/prestamos/tests/test_prestamos.py` (y tests auxiliares). No toca ningún otro archivo.

**Blueprint:** `bp = make_blueprint(__name__)` (3 líneas, como `catalogo/__init__.py`; se registra solo).

**Núcleo obligatorio:** `circulacion.autorizar_prestamo` (validar/crear), `autorizar_renovacion` + `fecha_renovacion` (renovar), `dias_retraso` + `multa_retraso` (devolver), `fecha_vencimiento` (vencimiento al prestar con `politica.dias_prestamo`), `limite_reserva()` (espera), `exigir(motivos)` (422), `notificaciones.validar_canales/enviar_a_usuario` (recibo y aviso a espera). Listados: `repo.select` con `build_where`/`search`. `PUT /api/politicas/<id>`: `validate` con `Int/Dec`. Sin duplicar la fórmula de vencido: SQL `fecha_devolucion IS NULL AND fecha_vencimiento < CURRENT_DATE`.

**BD:** sin cambios de esquema propios (usa P0: índice único de préstamo activo por ejemplar). Escrituras en `prestamo`, `renovacion`, `ejemplar.estado`, `adeudo` (solo tipo `retraso`), `lista_espera` (solo transición `notificado` al devolver y `recogido` al prestar).

**API** (permiso `prestamos`, salvo indicado):

| Método y ruta | Payload | Respuesta |
|---|---|---|
| `GET /api/prestamos` `?estado=activo\|devuelto\|vencido&q=&matricula=` | — | `[{id_prestamo, folio, usuario:{id_usuario, matricula, nombre_completo, rol}, libro:{id_libro, clave, titulo}, id_ejemplar, numero_copia, fecha_prestamo, fecha_vencimiento, fecha_devolucion, estado, num_renovaciones, max_renovaciones, dias_retraso, multa_estimada}]` (`estado` según D-24) |
| `GET /api/prestamos/<id>` | — | Un elemento anterior + `renovaciones:[{fecha, nueva_fecha_vencimiento}]`, `adeudos:[{id_adeudo, tipo, monto, estado}]` |
| `POST /api/prestamos/validar` | `{matricula, clave \| id_libro}` | `{autorizado, motivos:[{codigo, mensaje}], usuario:{id_usuario, matricula, nombre_completo, rol, prestamos_activos, max_libros, adeudos_pendientes, vencidos}, libro:{id_libro, clave, titulo, tipo_uso, disponibles}, dias_prestamo, fecha_vencimiento_estimada}`. Códigos: `USUARIO_NO_ENCONTRADO`, `USUARIO_INACTIVO`, `SIN_POLITICA`, `MULTAS_PENDIENTES`, `LIMITE_EJEMPLARES`, `PRESTAMOS_VENCIDOS`, `LIBRO_INACTIVO`, `LIBRO_NO_PRESTABLE`, `LIBRO_NO_DISPONIBLE`, `LIBRO_RESERVADO_OTRO_USUARIO` |
| `POST /api/prestamos` | `{matricula, clave \| id_libro, canales?:["email","whatsapp"]}` | 201 `{prestamo:<detalle>, recibo:<recibo>}`; 422 con `motivos` si no autorizado. Selecciona ejemplar con `SELECT ... FOR UPDATE SKIP LOCKED`; marca `prestado`; si el usuario tenía entrada `notificado` en `lista_espera` del libro, la pasa a `recogido`; envía recibo por los canales indicados (`core.notificaciones`, canal `email` por omisión) |
| `POST /api/prestamos/<id>/renovar` | `{}` | `{prestamo, renovacion:{nueva_fecha_vencimiento}}`; 422 con códigos `PRESTAMO_CERRADO`, `PRESTAMO_VENCIDO`, `MAX_RENOVACIONES`, `MULTAS_PENDIENTES`, `LISTA_ESPERA` (D-05) |
| `POST /api/prestamos/<id>/devolver` | `{}` | `{prestamo, dias_retraso, adeudo:{id_adeudo, monto, dias_retraso}\|null, espera_notificada:{id_espera, id_usuario}\|null}`; ejemplar `disponible`; adeudo `retraso` = `habiles_entre(vencimiento, hoy) × multa_diaria`; si hay `en_espera`, el primero pasa a `notificado` con `fecha_notificacion=now()` y `fecha_limite_recoger = sumar_habiles(hoy, dias_reserva_espera())` y se le envía correo |
| `GET /api/prestamos/<id>/recibo` | — | `{folio:"REC-000123", fecha_prestamo, fecha_vencimiento, usuario, libro:{..., ubicacion}, dias_prestamo, politica:{max_renovaciones, multa_diaria}, notificaciones:[{canal, fecha, asunto}]}` |
| `POST /api/prestamos/<id>/recibo/enviar` | `{canales:["email","whatsapp"]}` | `{enviados:[canal,...]}` |
| `GET /api/politicas` | — | `[{id_politica, rol, dias_prestamo, max_libros, max_renovaciones, multa_diaria, activa}]` |
| `PUT /api/politicas/<id>` (permiso `perfiles`) | `{dias_prestamo, max_libros, max_renovaciones, multa_diaria}` | política actualizada; valida enteros > 0 / multa ≥ 0; bitácora `politica_cambio`. Un préstamo ya creado conserva su `id_politica` |

**UI** (rutas con `section: 'prestamos'`, `perm: 'prestamos'`; componentes: `listPage`+`toolbar`+`dataTable`+`statusBadge('prestamo')`, `formView`/`bindForm`, `detailView`, `receiptBlock`, `notice` para los motivos, `confirmAction` en devolver/renovar): `prestamos` (lista con filtros estado/búsqueda, acciones renovar/devolver en fila); `prestamos/nuevo` (formulario matrícula + clave → validación en vivo con `validar`, confirmar → recibo); `prestamos/:id` (detalle + renovar/devolver + recibo imprimible/PDF con `printHtml` y `downloadPdf` + botón "Enviar recibo por correo/WhatsApp" + enlaces a `#/adeudos/perdida/:id` y `#/adeudos/danio/:id`); `politicas` (`section: 'perfiles'`, `perm: 'perfiles'`, tabla editable con `formView`). Máximo 3 clics para prestar, devolver y renovar (D-17).

**Pruebas** (helpers: `make_user`, `make_book`, `make_loan`; demo sembrada: Carlos vencido, Laura con adeudo, DOC001 con 3 préstamos): reglas a–e de RN-01 una por una (alumno con 2 préstamos rechazado, docente con 3 rechazado, con multa, con vencido, libro `consulta_interna`/`reservado`/sin copias/inactivo); vigencia 5 y 10 hábiles incluyendo préstamo en viernes y sábado; renovaciones 2/3 y rechazos de D-05; devolución a tiempo (sin adeudo), 1 día hábil tarde (monto 10), cruzando fin de semana (retraso 1 el lunes si vence viernes), notificación de espera; concurrencia (dos préstamos simultáneos del último ejemplar: solo uno); permisos (alumno 403, anónimo 401); bitácora `prestamo_crear/renovar/devolver`.

**Aceptación:** todas las condiciones RN-01 producen su código; fechas de vencimiento correctas con D-03; un préstamo y su recibo en ≤ 1 s de servidor; disponibilidad del catálogo cambia al prestar/devolver sin recargar la caché (no existe); ningún otro módulo modificado.

**Entregable de documentación:** fragmento de `README.md` (endpoints, pantallas, reglas D-01..D-06) en el informe final del paquete.

### Paquete B — `espera` (lista de espera) · RF-22, PS-S2-05, D-19

**Archivos:** `app/modules/espera/{__init__.py, model.py, service.py, controller.py}`, `app/modules/espera/web/{model.js, view.js, controller.js}`, `app/modules/espera/tests/test_espera.py`.

**BD:** sin cambios de esquema (índice único parcial `uq_espera_usuario_libro_activa`, de P0; un duplicado concurrente debe responder 422 `YA_EN_ESPERA`, no 500). **Núcleo:** `circulacion.contexto_libro` (disponibles), `limite_reserva()`/`parametros.dias_reserva_espera()` (plazo, mismo cálculo que A), `exigir`, `notificaciones.enviar_a_usuario('email', ...)`.

**Demo sembrada:** María en espera de LIB005 (sin ejemplares).

**Contrato `lista_espera` compartido con A:** A pasa a `notificado` al devolver y a `recogido` al prestar; **B** gestiona alta, cancelación, renumeración de `posicion` y **expiración** (`notificado` con `fecha_limite_recoger < now()` → `cancelado` y notifica al siguiente, con el mismo cálculo de plazo de A), ejecutada de forma perezosa en cada `GET /api/espera`.

**API** (permiso `espera`):

| Método y ruta | Payload | Respuesta |
|---|---|---|
| `GET /api/espera` `?estado=&id_libro=&q=` | — | `[{id_espera, usuario:{id_usuario, matricula, nombre_completo}, libro:{id_libro, clave, titulo, disponibles}, posicion, estado, fecha_solicitud, fecha_notificacion, fecha_limite_recoger}]` |
| `POST /api/espera` | `{matricula, id_libro}` | 201 elemento; 422 con códigos `HAY_DISPONIBLES`, `YA_EN_ESPERA`, `YA_TIENE_PRESTAMO`, `LIBRO_NO_PRESTABLE`, `USUARIO_INACTIVO`; `posicion` = activos + 1 |
| `DELETE /api/espera/<id>` | — | elemento con `estado='cancelado'`; renumera posiciones |

**UI:** `espera` (`section: 'espera'`, `perm: 'espera'`; `listPage`+`toolbar`+`dataTable`+`statusBadge('listaEspera')`, alta con `formView`/`bindForm`, cancelar con `confirmAction`). También un botón "Añadir a lista de espera" en el rechazo `LIBRO_NO_DISPONIBLE` de `prestamos/nuevo`: **lo agrega A como enlace** a `#/espera?matricula=..&id_libro=..` (B lee esos parámetros de la query del hash para prellenar).

**Pruebas:** FIFO y renumeración al cancelar; duplicados; rechazo con ejemplares disponibles; expiración y paso al siguiente; permisos.

**Aceptación:** posiciones consecutivas sin huecos; un usuario no puede acumular dos entradas activas del mismo libro; expiración respeta días hábiles.

### Paquete C — `adeudos` (multas, pagos, pérdida y daño) · RN-03/RN-04, RF-25 (daño/pérdida), RF-26, RF-27, PS-S2-09..12 (parte), PS-MET-04

**Archivos:** `app/modules/adeudos/{__init__.py, model.py, service.py, controller.py}`, `app/modules/adeudos/web/{model.js, view.js, controller.js}`, `app/modules/adeudos/tests/test_adeudos.py`.

**BD:** sin cambios propios; escribe `adeudo`, `ejemplar` (`estado='baja'`, `motivo_baja`), `prestamo` (cierre por pérdida: `estado='devuelto'`, `fecha_devolucion=now()`).

**Núcleo obligatorio:** `circulacion.valor_reposicion` (RN-04, ya implementa el contrato siguiente), `monto_danio` (D-08, valida 10–100), `dias_retraso`/`multa_retraso` (retraso al reportar pérdida o daño), `parametros.tipo_cambio()`, `notificaciones.enviar(...)` canales `servicios_escolares`/`tesoreria`/`email`, `toggle`-style guardas con `ApiError(409)`, `validate` (`Str` referencia 3–40, `Int` porcentaje), `@audit` (`adeudo_pago`, `adeudo_cancelar`, `adeudo_perdida`, `adeudo_danio`). Cancelar: `require_permission`/rol `admin` (`current_user()['rol']`).

**Contrato de reposición** (implementado en `core.circulacion.valor_reposicion`; también lo usa D para explicar): `valor_usd = última detalle_solicitud.precio_unitario del libro en solicitud con estado 'recibida'` (orden `fecha_recepcion DESC, id_detalle DESC`), o `libro.precio_referencia` si no hay compras; `monto_mxn = round(valor_usd × tipo_cambio(), 2)`.

**API** (permiso `adeudos`):

| Método y ruta | Payload | Respuesta |
|---|---|---|
| `GET /api/adeudos` `?estado=pendiente\|pagado\|cancelado&tipo=&q=&matricula=` | — | `[{id_adeudo, tipo, monto, estado, dias_retraso, fecha_pago, usuario:{id_usuario, matricula, nombre_completo, rol}, libro:{id_libro, clave, titulo}, id_prestamo}]` |
| `POST /api/adeudos/<id>/pago` | `{referencia_tesoreria (3-40), fecha_pago?}` | adeudo `pagado`, `fecha_pago`; bitácora `adeudo_pago` con la referencia; correo simulado al usuario; 409 si ya pagado/cancelado |
| `POST /api/adeudos/<id>/cancelar` (solo rol `admin`) | `{motivo (3-120)}` | adeudo `cancelado`; bitácora `adeudo_cancelar` |
| `GET /api/adeudos/reposicion` `?id_libro=` | — | `{id_libro, valor_usd, fuente:"ultima_compra"\|"precio_referencia", tipo_cambio, monto_mxn}` |
| `GET /api/tipo-cambio` | — | `{usd_mxn, fuente:"simulado", nota}` |
| `POST /api/adeudos/perdida` | `{id_prestamo, tipo_cambio?, observacion?}` | 201 `{adeudos:[...], valor_usd, tipo_cambio, monto_mxn}`; crea adeudo `retraso` hasta hoy si hay retraso (D-07), adeudo `perdida`, ejemplar `baja/perdido`, cierra el préstamo, avisos `servicios_escolares` y `tesoreria` (`core.notificaciones`); 409 si el préstamo ya está cerrado |
| `POST /api/adeudos/danio` | `{id_prestamo, porcentaje?:10-100 (50), observacion?, dar_baja?:false}` | 201 `{adeudo, devolucion}`: registra devolución (misma regla de retraso que A, vía `core.circulacion`), adeudo `danio`, ejemplar `disponible` o `baja/danado` |

**UI** (`section: 'adeudos'`, `perm: 'adeudos'`; `listPage`, `formView`, `detailView`, `statusBadge('adeudo')`, `label('adeudoTipo')`, `money`, `confirmAction`, `receiptBlock` para el comprobante de pago): `adeudos` (lista con filtros, "Registrar pago" con referencia, "Cancelar" para admin); `adeudos/perdida/:id_prestamo` (previsualiza reposición con `GET reposicion`, confirma); `adeudos/danio/:id_prestamo`. Enlaces de entrada desde `prestamos/:id` (los agrega A como enlaces a `#/adeudos/perdida/:id` y `#/adeudos/danio/:id`).

**Pruebas:** pago exitoso/duplicado/sin referencia; cancelar solo admin; reposición con y sin compra, con tipo de cambio sobrescrito, redondeo; pérdida deja ejemplar `baja` y aviso en bitácora (2 notificaciones); daño 50 %/100 %; que un adeudo pendiente bloquea `circulacion.autorizar_prestamo` (prueba cruzada con el núcleo, no con A).

**Aceptación:** monto de pérdida = valor_usd × tipo_cambio exacto a 2 decimales; tras pagar todos los adeudos el usuario vuelve a ser autorizable.

### Paquete D — `asistente` (chatbot) · RF-29..33, RNF-12/13/14, PS-S3-01..09, PS-TEC-09, PS-MET-03

**Archivos:** `app/modules/asistente/{__init__.py, model.py, service.py, controller.py}`, `app/modules/asistente/web/{model.js, view.js, controller.js}`, `app/modules/asistente/tests/test_asistente.py`.

**BD:** usa `intencion`, `pregunta_frecuente`, `conversacion`, `mensaje` (sin cambios; intenciones y FAQ ya sembradas, 5.3). **Núcleo obligatorio:** `circulacion.politica_vigente(id_rol)` (reglas con números reales), `contexto_usuario` (estatus de préstamos/multas, `suspendido`), `valor_reposicion` (explicar pérdida), `repo.select`/`build_where(search=...)` (búsqueda de libros con unaccent), `validate`, `@audit(asistente_resolver)`. Tests con `conversacion`/`mensaje` se limpian solos (`conftest.py`). Paso a bibliotecario = mensaje con la intención `pasar_a_bibliotecario` en una conversación con `resuelta=false`. Datos de políticas leídos de `politica_prestamo` (no hardcodear números).

**API:**

| Método y ruta | Permiso | Payload | Respuesta |
|---|---|---|---|
| `POST /api/asistente/mensajes` | `asistente` | `{texto (1-500), id_conversacion?, canal?:"web"\|"movil"}` | `{id_conversacion, respuesta:{texto, intencion, con_bibliotecario:bool, libros?:[{id_libro, clave, titulo, disponibles, ubicacion}], enlaces?:[{texto, ruta}]}}`. Guarda mensaje del usuario y de la respuesta con `id_intencion` |
| `GET /api/asistente/conversaciones/<id>` | `asistente` | — | `{id_conversacion, resuelta, mensajes:[{emisor, texto, fecha}]}` (solo el dueño; las del visitante por `session`) |
| `POST /api/asistente/conversaciones/<id>/opinion` | `asistente` | `{calificacion:1-5, resuelta?:bool}` | conversación actualizada |
| `GET /api/asistente/consultas` `?estado=pendiente\|resuelta` | `prestamos` | — | `[{id_conversacion, usuario:{matricula, nombre_completo}\|null, fecha_inicio, ultimo_mensaje, resuelta}]` |
| `POST /api/asistente/consultas/<id>/resolver` | `prestamos` | `{respuesta (1-500)}` | conversación con `resuelta=true` y mensaje `emisor='asistente'` con prefijo "[Bibliotecario]"; bitácora `asistente_resolver` |

**Intenciones y fuentes:** saludo/despedida/ayuda (plantillas); `horarios`, `ubicacion`, `prestamo`/`reglas`, `renovacion`, `multas` (FAQ + `politica_prestamo`); `buscar_libro` (título/autor/tema/clave/editorial con la misma normalización sin acentos que `core/validators.py::search_clause`, máx. 5 resultados, con disponibilidad y ubicación); `estatus_prestamos` y `estatus_multas` (SQL sobre `prestamo`, `renovacion`, `adeudo` del usuario de la sesión; visitante → respuesta que pide iniciar sesión); `no_entendido` → ofrece pasar a bibliotecario; segunda consecutiva o petición explícita ("hablar con bibliotecario") → con_bibliotecario. Latencia ≤ 3 s (sin llamadas externas).

**UI** (componentes `chatPanel`, `chatBubble`, `appendChat`, `bindChat`, `statusBadge('consulta')`, `dataTable`; el `aria-live` y el foco ya vienen en `chatPanel`): ruta `asistente` (`section: 'asistente'`, `perm: 'asistente'`), ruta móvil `movil/asistente` (`bare: true`, patrón de `catalogo/web/controller.js:95-96`) y pantalla `asistente/consultas` para quien tenga `prestamos` (enlace dentro de la pantalla del asistente). Tecla Enter envía; historial de la conversación activa en memoria y recarga por `GET`.

**Pruebas:** una prueba por intención (horario, reglas con valores de la política, búsqueda con y sin resultados, estatus propio con préstamo/multa sembrados, visitante bloqueado de estatus, paso a bibliotecario y resolución por bibliotecario, calificación); texto sin acentos y en mayúsculas; aislamiento (un alumno no ve conversaciones de otro); 3 s.

**Aceptación:** respuestas reflejan cambios de `politica_prestamo`; cada mensaje queda en `mensaje`; paso a bibliotecario visible al bibliotecario.

### Paquete E1 — `compras` (recepción, factura, presupuesto) · RF-05, RF-06, RO-02, PS-S1-01, D-22, D-25

**Archivos (módulo existente, dueño exclusivo):** `app/modules/compras/{model.py, service.py, controller.py}`, `app/modules/compras/web/{model.js, view.js, controller.js}`, `app/modules/compras/tests/*`. (`__init__.py` no cambia.) **Núcleo/componentes:** `parametros.presupuesto_mensual()`, `exigir`/`ApiError.reglas` (`PRESUPUESTO_EXCEDIDO`), `validate` (`List`, `Dec`, `Int`), `notificaciones.enviar('tesoreria', ...)`, `catalogo.model.add_ejemplares`; UI: `meter` (barra de presupuesto), `formView`, `statusBadge('solicitud')` (ya incluye `recibida`), `money`.

**BD:** columnas aditivas de P0: `solicitud_compra.factura_folio`, `factura_total`, `fecha_recepcion`, estado `recibida`; `detalle_solicitud.cantidad_recibida`. Precios en USD (D-07, D-28): etiquetar "USD" en la UI.

**API** (permiso `compras`):

| Método y ruta | Payload | Respuesta |
|---|---|---|
| `GET /api/compras/presupuesto` `?mes=YYYY-MM` | — | `{mes, presupuesto_usd, usado_usd, disponible_usd}` |
| `POST /api/compras` (existente) | igual | Nueva validación: 422 `PRESUPUESTO_EXCEDIDO` si `total > disponible` del mes |
| `POST /api/compras/<id>/cancelar` | `{}` | estado `cancelada` (solo `pendiente`/`enviada` sin recepción) |
| `POST /api/compras/<id>/recibir` | `{factura_folio (3-30), factura_total, fecha_recepcion?, lineas:[{id_detalle, cantidad_recibida}]}` | solicitud + `detalles` con `cantidad_recibida` + `pendientes_catalogar:[{id_detalle, descripcion, cantidad_recibida}]`. Solo desde `enviada`; no excede la cantidad pedida; suma acumulativa; al completar todas las líneas estado `recibida` y `fecha_recepcion`; líneas con `id_libro` suman ejemplares con `catalogo.model.add_ejemplares`; aviso `tesoreria` con folio y total (`core.notificaciones`); bitácora `compra_recibir` |

El detalle (`GET /api/compras/<id>`) incluye `id_detalle` y `cantidad_recibida` (cambio compatible con `compras/model.py:12-15`).

**UI:** en `compras` y `compras/:id`: barra de presupuesto del mes; botón "Recibir pedido" (formulario de factura y cantidades por línea); estado "Recibida" con `statusBadge('solicitud', 'recibida')` (etiqueta ya existe); "Cancelar" con `confirmAction`.

**Pruebas:** presupuesto excedido/dentro; recepción parcial y total; no se puede recibir una solicitud `pendiente`/`cancelada`; ejemplares agregados solo en líneas ligadas; aviso a Tesorería; `core.circulacion.valor_reposicion` devuelve el precio de la recepción nueva.

**Aceptación:** tras recepción total la solicitud es `recibida` y los ejemplares aumentan; el precio queda disponible para la reposición (`core.circulacion.valor_reposicion`, que lee `solicitud_compra.estado='recibida'`, `fecha_recepcion` y `detalle_solicitud.precio_unitario`). La semilla `SOL000` ya sirve de ejemplo; `SOL001` (pendiente) se conserva para las pruebas existentes.

### Paquete E2 — `catalogo` (ficha/etiqueta, reservado, bajas por ejemplar, existencia) · RF-07, RF-09, RF-10, RF-11, PS-S1-02/04/05, PS-S1-12

**Archivos (módulo existente, dueño exclusivo):** `app/modules/catalogo/{model.py, service.py, controller.py}`, `app/modules/catalogo/web/{model.js, view.js, controller.js}`, `app/modules/catalogo/tests/*`. **Núcleo/componentes:** `validate` (`Enum` de `tipo_uso` ya acepta lo que defina el esquema: agregar `reservado`), `repo.update/insert`, `@audit(ejemplar_baja)`, `ApiError(409)`; UI: `statusBadge('disponibilidad')`, `label('motivoBaja')`, `labelItems('motivoBaja')` y `labelItems('tipoUso')` (ya incluyen `reservado`), `printHtml`/`downloadPdf`, `disclosure`, `confirmAction`.

**BD:** `ejemplar.motivo_baja` y valor `reservado` de `tipo_uso` (P0; demo: `LIB007` reservado). Para "reservado no prestable" la prueba usa `circulacion.autorizar_prestamo` (`LIBRO_NO_PRESTABLE`).

**API:**

| Método y ruta | Permiso | Payload | Respuesta |
|---|---|---|---|
| `GET /api/libros/<id>/ejemplares` | `catalogo` | — | `[{id_ejemplar, numero_copia, estado, motivo_baja, fecha_alta, prestamo_activo:{id_prestamo, matricula, fecha_vencimiento}\|null}]` |
| `POST /api/ejemplares/<id>/baja` | `catalogo` | `{motivo:"perdido"\|"robado"\|"danado"\|"obsoleto", observacion?}` | ejemplar con `estado='baja'`; 409 si está `prestado` (mensaje: "usa Multas y pagos para registrar la pérdida") ; bitácora `ejemplar_baja` |
| `POST /api/ejemplares/<id>/reactivar` | `catalogo` | `{}` | ejemplar `disponible`, `motivo_baja=null` (solo desde `baja` y libro activo) |
| `POST /api/libros` / `PUT` (existentes) | `catalogo` | `tipo_uso` acepta `reservado`; nuevo opcional `id_detalle` | Con `id_detalle` enlaza `detalle_solicitud.id_libro` (libro nuevo recibido por compras) |
| `GET /api/libros/<id>/etiqueta` | sesión con `catalogo` | — | `{clave, titulo, autor, clasificacion, ubicacion, codigo_ejemplares:[{numero_copia, etiqueta:"LIB001-01"}]}` |
| `GET /api/libros/pendientes` | `catalogo` | — | `[{id_detalle, descripcion, cantidad_recibida, folio}]` (recibidos sin `id_libro`) |
| `POST /api/libros/importar` (opcional, PS-S1-12) | `catalogo` | `{csv}` | `{creados, errores:[{linea, motivo}]}` |

Se mantiene el filtro de visibilidad existente (no-personal solo ve activos, `catalogo/service.py:16-21`). Los libros `reservado` aparecen en la búsqueda con su etiqueta y sin botón de préstamo.

**UI:** ficha con pestaña/sección "Ejemplares" (tabla, "Dar de baja" con motivo, "Reactivar"); botón "Imprimir ficha y etiquetas" (`printHtml` + PDF); lista "Pendientes de catalogar" con enlace a `libros/nuevo?id_detalle=..` (el formulario lee el parámetro del hash); selector `tipo_uso` con `labelItems('tipoUso')` (ya incluye `Reservado`).

**Pruebas:** baja con cada motivo; baja de prestado rechazada; reactivar; `reservado` no prestable (verificado con `core.circulacion.autorizar_prestamo`, `LIBRO_NO_PRESTABLE`); etiqueta; enlace de `id_detalle`; permisos (bibliotecario con `catalogo` puede, alumno 403); regresión de las pruebas existentes (`test_catalogo.py`).

**Aceptación:** conteos `ejemplares/disponibles` excluyen `baja`; todo ejemplar dado de baja conserva motivo.

### Paquete F — `usuarios` (historial, actualización, importación) · RF-03, RF-04, PS-S0-04, PS-S0-11, D-23

**Archivos (módulo existente, dueño exclusivo):** `app/modules/usuarios/{model.py, service.py, controller.py}`, `app/modules/usuarios/web/{model.js, view.js, controller.js}`, `app/modules/usuarios/simulado/servicios_escolares.json` (nuevo), `app/modules/usuarios/tests/*`.

**BD:** sin cambios. **Núcleo/componentes:** `validate`, `repo.exists/insert/update`, `toggle_estado` (guardas de baja existentes), `circulacion.contexto_usuario` (conteos de préstamos y adeudos para `adeudos_pendientes`/`_n` y guarda de baja por préstamos abiertos), `@audit`; UI: `detailView`, `dataTable`, `formView`, `statusBadge`, `label('adeudoTipo')`, `label('listaEspera')`.

**API** (permiso `usuarios`):

| Método y ruta | Payload | Respuesta |
|---|---|---|
| `GET /api/usuarios/<id>/historial` | — | `{prestamos:[{id_prestamo, libro:{clave, titulo}, fecha_prestamo, fecha_vencimiento, fecha_devolucion, estado, num_renovaciones}], renovaciones:[{id_prestamo, fecha, nueva_fecha_vencimiento}], adeudos:[{id_adeudo, tipo, monto, estado, fecha_pago, id_prestamo}], espera:[{id_espera, libro, estado, posicion}], bitacora:[{accion, detalle, fecha}]}` (SQL de solo lectura sobre las tablas S2; devuelve listas vacías si no hay datos) |
| `GET /api/usuarios/actualizar` | — | `{origen:"servicios_escolares", registros:[...], resumen:{nuevos, cambios, bajas}}` (vista previa del archivo simulado contra la BD) |
| `POST /api/usuarios/actualizar` | `{}` | `{creados, actualizados, bajas, omitidos:[{matricula, motivo}]}`; respeta guardas de baja (`usuarios/service.py:56-62`); `fuente_validacion='servicios_escolares'` |
| `POST /api/usuarios/importar` | `{csv:"matricula,nombre_completo,correo,rol,estado\n..."}` | `{creados, actualizados, errores:[{linea, motivo}], credenciales_iniciales:[{matricula, password}]}` (contraseña aleatoria mostrada una sola vez; reutiliza `_clean`) |

Corregir el defecto de `usuarios/model.py:9-10` / `view.js:57`: exponer `adeudos_pendientes` (monto) y `adeudos_pendientes_n` (conteo) y etiquetar correctamente.

**UI:** en `usuarios/:id`, sección "Historial" (tablas de préstamos, renovaciones, adeudos, espera, actividad); pantalla `usuarios/actualizar` (vista previa + aplicar) y `usuarios/importar` (carga de CSV pegado/archivo leído con `FileReader`). Enlaces desde la lista de usuarios.

**Pruebas:** historial con préstamos/adeudos sembrados por SQL; actualización idempotente; importación con errores por línea y duplicados; baja bloqueada por préstamos; permiso `usuarios` requerido.

**Aceptación:** administrador consulta el historial completo de un usuario en ≤ 2 clics desde la lista; la actualización puede repetirse sin duplicar.

### Paquete G — `reportes` + `inicio` (alumnos con adeudos, inventario, circulación, tablero) · RF-16, RF-28, CTX-04, PS-S1-07, PS-S2-10

**Archivos (módulos existentes, dueño exclusivo):** `app/modules/reportes/{model.py, service.py, controller.py}`, `app/modules/reportes/web/{model.js, view.js, controller.js}`, `app/modules/reportes/tests/*`, `app/modules/inicio/{model.py, service.py}` y `app/modules/inicio/web/{model.js, view.js}`, `app/modules/inicio/tests/*`.

**BD:** `reporte_generado.tipo` ampliado por P0 (`con_adeudos`, `inventario_estante`, `prestamos_vencidos`, `prestamos`). **Núcleo/componentes:** `reportes/service.py` ya usa `validate(Enum)` y `model.registrar`: ampliar `TIPOS`; `circulacion.dias_retraso`/`multa_retraso`/`esta_vencido` para las columnas calculadas; definición de deudor idéntica a `contexto_usuario` (`vencidos>0 or adeudos_pendientes>0`) con una prueba que las compare; `notificaciones.enviar('servicios_escolares', ...)`; UI: `core/pdf.js`, `printHtml`, `statCard`, `grid`, `dataTable`.

**API** (mantiene el formato `{tipo, generado, generado_por, columnas, filas, total}` de `reportes/service.py:27-28`; permiso `reportes`; las rutas de `GET /api/reportes/<tipo>` aceptan los tipos nuevos y filtros por query):

| Método y ruta | Respuesta / efecto |
|---|---|
| `GET /api/reportes/con_adeudos` `?incluir_docentes=0&formato=` | Alumno con adeudos = usuario (alumno; docente opcional) con préstamo vencido (D-24) o adeudo pendiente. Columnas: Matrícula, Nombre, Correo, Libros vencidos, Días de retraso, Adeudo pendiente (MXN), Suspendido (sí) |
| `POST /api/reportes/con_adeudos/aviso` (permiso `reportes`, además `prestamos`) | Envía **un** aviso `servicios_escolares` con las matrículas y registra bitácora `reporte_con_adeudos_aviso`; `{enviados:n, matriculas:[...]}`. 422 si no hay alumnos con adeudos |
| `GET /api/reportes/inventario_estante` `?planta=&pasillo=&librero=&tema=` | Clave, Título, Ubicación, Ejemplares (sin bajas), Disponibles, Prestados, Bajas, "Conteo físico" (vacío para imprimir) |
| `GET /api/reportes/prestamos_vencidos` | Préstamos vencidos con usuario, días de retraso y multa estimada |
| `GET /api/reportes/prestamos` `?desde=&hasta=` | Préstamos por periodo (con devoluciones y renovaciones) |

`GET /api/stats` (`inicio`) agrega `prestamos_vencidos`, `adeudos_pendientes` (monto), `espera_activa`, `consultas_pendientes` (conteos por SQL; si una tabla no tiene datos devuelve 0). Las consultas usan SQL directo sobre tablas (D-24), no dependen de módulos A–D.

**UI:** nuevos tipos en el selector de `reportes`, con filtros (planta/pasillo/librero/tema, periodo), PDF e impresión reutilizando `core/pdf.js`; botón "Enviar aviso a Servicios Escolares" en el reporte `con_adeudos` (solo con `prestamos`); tarjetas nuevas en el tablero de inicio para personal.

**Pruebas:** alumnos con adeudos con vencido, con adeudo, ambos y sin; aviso genera una notificación y falla sin alumnos con adeudos; inventario por estante con filtros y excluye bajas; stats; registros en `reporte_generado`; permisos.

**Aceptación:** la lista de alumnos con adeudos coincide con el cálculo de D-09/D-24; el aviso queda visible en la lista de avisos.

### Paquete H — `notificaciones` + infraestructura/NFR · RNF-02, RNF-03/05/11/13 (medición), RNF-06 (checklist), RNF-10/PS-S2-06 (visibilidad), RNF-12, PS-S0-06, PS-S4-04

**Archivos:** módulo nuevo `app/modules/notificaciones/{__init__.py, model.py, service.py, controller.py}`, `app/modules/notificaciones/web/{model.js, view.js, controller.js}`, `app/modules/notificaciones/tests/test_notificaciones.py`; `scripts/respaldo.py`, `scripts/restaurar.py`, `scripts/medir_rendimiento.py`; `docker-compose.yml`, `Dockerfile`; `docs/operacion.md` (procedimiento de respaldo/restauración y checklist de accesibilidad D-16, nuevo archivo).

**BD:** ninguna (lee `bitacora`). **Núcleo/componentes:** `notificaciones.parsear` (formato único del detalle) y `CANALES`; `repo.select` con SQL base `... WHERE b.accion LIKE 'notif_%'` + `build_where` (filtros `canal`, `search` sobre `detalle`/`matricula`); `query_args`; UI: `listPage`, `toolbar`, `dataTable`, `badge`, `label('canal')`.

**API:**

| Método y ruta | Permiso | Respuesta |
|---|---|---|
| `GET /api/notificaciones` `?canal=&q=&desde=&limite=100` | `notificaciones` | `[{id_bitacora, canal, destino, asunto, cuerpo, fecha, usuario:{matricula, nombre_completo}}]` (filas `accion LIKE 'notif_%'`, más recientes primero) |
| `GET /api/notificaciones/mias` | sesión | Lo mismo, filtrado por el usuario de la sesión |

**UI:** `notificaciones` (tabla con filtros de canal y texto; etiqueta "Simulado" en cada fila).

**Scripts:** `respaldo.py [--salida backups/]` genera `backups/librigest_YYYYmmdd_HHMMSS.dump` con `docker compose exec -T db pg_dump -Fc`; `restaurar.py <archivo> [--verificar]` restaura con `pg_restore --clean --if-exists` (con `--verificar`, en una BD temporal, y compara conteos por tabla); `medir_rendimiento.py` mide p50/p95 de los endpoints críticos con `urllib` (login, `libros`, `usuarios`, `prestamos`, `asistente/mensajes`, `reportes/*`) y falla si p95 > 3 s (D-15). Compose: `restart: unless-stopped` en `db` y `web` y volumen `./backups:/backups` para el servicio `db`.

**Pruebas:** listado y filtro de notificaciones (creadas con `core.notificaciones.enviar` dentro de `app.app_context()` + commit, o con SQL en `bitacora`), `mias` solo propias, permisos; los scripts se validan manualmente y se documentan (no pytest, requieren Docker).

**Aceptación:** respaldo y restauración verificada documentadas con salida real; `medir_rendimiento.py` ejecutable contra el contenedor; el documento `docs/operacion.md` incluye checklist D-16 para que el agente de estilos lo aplique (los paquetes no editan CSS).

---

## 7. Orden de integración — **EJECUTADO** (excepto la integración final parcial)

1. **P0** (fundación) — **hecho** (sección 5.1).
2. **A, B, C, D, E1, E2, F, G, H en paralelo** (archivos disjuntos). Dependencias solo por contrato: A/B/C/D comparten `core.circulacion` (5.2) y no se importan entre sí; G y F leen tablas con SQL tolerante a vacío; D consulta tablas S2 directamente; E1 aporta el precio de reposición que lee C.
3. **Integración (I):** fusionar fragmentos de `README.md` (tabla de módulos, endpoints, pantallas, reglas, variables de entorno nuevas, scripts), actualizar `info/web/view.js` (guía/funciones), ejecutar `scripts/recrear_db.py -y`, `docker compose exec -T web pytest`, `scripts/medir_rendimiento.py`, y el checklist de accesibilidad y de 3 clics; que el agente de estilos revise las vistas nuevas (U6).
4. Validación de las decisiones D-01..D-29 por el Product Owner; cualquier cambio de parámetro se hace en `politica_prestamo` o en variables de entorno, sin tocar código.

Orden mínimo para una demo útil: P0 → A → C → G (ciclo de préstamo-devolución-multa-alumnos con adeudos); luego B, D, E1, E2, F, H.

---

## 8. Apéndice: cambios aditivos al esquema oficial (documentados en la cabecera de `db/01_schema.sql:3-13`)

| # | Cambio | Requisito que lo exige | Alternativa descartada |
|---|---|---|---|
| S-1 | `ejemplar.motivo_baja VARCHAR(20) NULL CHECK (motivo_baja IN ('perdido','robado','danado','obsoleto'))` | RF-11 (motivo de baja); RN-04 | Guardar el motivo en `bitacora` (no consultable por ejemplar) |
| S-2 | `libro.tipo_uso` CHECK ampliado con `'reservado'` | RF-10, D-20 | Reutilizar `consulta_interna` (confunde "reservado" con "solo sala") |
| S-3 | `solicitud_compra`: estado `'recibida'` en el CHECK y columnas `factura_folio VARCHAR(30) NULL`, `factura_total DECIMAL(12,2) NULL`, `fecha_recepcion DATE NULL`; `detalle_solicitud.cantidad_recibida SMALLINT NOT NULL DEFAULT 0 CHECK (cantidad_recibida >= 0)` | RF-06 (recepción y factura), RN-04 (precio de última compra recibida) | Tabla nueva de recepción (agrega entidad fuera del diseño) |
| S-4 | `reporte_generado.tipo` CHECK ampliado: `'alumnos con adeudos','inventario_estante','prestamos_vencidos','prestamos'` y después `'indicadores'`, `'errores'` | RF-16, RF-28, PS-MET-02/03, PS-S3-06 | No registrar los reportes (rompe la trazabilidad existente `reportes/service.py:25`) |
| S-5 | Índices únicos parciales: `uq_prestamo_ejemplar_abierto` = `prestamo(id_ejemplar) WHERE estado IN ('activo','vencido')` y `uq_espera_usuario_libro_activa` = `lista_espera(id_usuario, id_libro) WHERE estado IN ('en_espera','notificado')` | RNF-08/PS-NFR-07 (consistencia concurrente), D-19 | Solo bloqueo a nivel aplicación (permite carreras) |
| S-6 | `bitacora.id_usuario` admite `NULL` (antes `NOT NULL`) | PS-S3-06: un error del servidor o del navegador puede ocurrir sin sesión | Atribuirlo a un usuario administrador ficticio (falsea la auditoría) |

No se agregan tablas. Tipo de cambio, presupuesto mensual, referencia de pago, lista de avisos, paso a bibliotecario del chatbot y "suspendido" se resuelven con variables de entorno, `bitacora`, `conversacion/mensaje` y consultas calculadas (D-04, D-07, D-09, D-10, D-11, D-13, D-22).

---

## 9. Verificación

### Resultados de pruebas E2E

**Resumen:** el 2026-10-27 pasaron los **15 flujos** en Chrome contra el stack Docker (`python3 scripts/levantar.py`, BD demo), sin errores de consola. Pruebas automáticas: **236 pasan** (`docker compose exec -T web pytest`); `node --check` sin errores en todo el JavaScript.

**Flujos ejecutados:** préstamos (prestar, renovar, devolver), adeudos (pago, pérdida, daño, cancelar), lista de espera, asistente, compras, catálogo, usuarios y perfiles, reportes, inicio, notificaciones, roles (menú y permisos por perfil), responsive 390 px, accesibilidad, 3 clics, estilos uniformes.

**Menú por rol** (secciones visibles en la barra lateral):

| Perfil | Secciones |
|---|---|
| Visitante | Buscar, Asistente |
| Alumno / Docente | Buscar, Lista de espera, Asistente, Notificaciones (propias), Inicio |
| Bibliotecario | Inicio, Buscar, Catálogo, Préstamos, Espera, Multas y pagos, Asistente (consultas para el bibliotecario), Reportes, Notificaciones |
| Catálogo | Inicio, Buscar, Catálogo, Reportes, Asistente |
| Compras | Inicio, Buscar, Compras, Asistente |
| Colaborador | Inicio, Buscar, Catálogo, Compras, Reportes, Asistente (sin Préstamos) |
| Administrador | Todas, incluidos Usuarios, Perfiles y cancelar adeudos |

(Resumen por perfil; la matriz exacta es `db/02_seed.sql` y la pantalla Perfiles.)

**Resultados por tema**

| Tema | Resultado |
|---|---|
| Responsive | 29 rutas a 390 px sin desbordamiento horizontal |
| Accesibilidad | `lang="es"`, etiquetas y nombres accesibles, `alt`, trampa de foco en diálogos, regiones `aria-live`; contraste ≥ 4.5:1 tras ajustar `--good #256b29` y `--warn #9a5700` |
| 3 clics | Los 7 procesos de D-17 ≤ 3 clics (compras necesitaba 4; corregido, ver abajo) |
| Estilos | Uniformes en 41 rutas |

**Defectos corregidos durante el E2E:** botones renovar/devolver sin `data-id`; cancelar sin restricción de rol en la UI; un 403 mostraba "no encontrado"; el asistente no entendía "busco un libro"; compras requería 4 clics; fecha del comprobante desfasada; mensaje de presupuesto inconsistente; zona horaria (`TZ America/Mexico_City` en compose); tabla de actualización obsoleta; matriz de perfiles con casillas del administrador; contraste de color.

**Pendientes del E2E, corregidos y re-verificados en Chrome el mismo día (tras reconstruir)**

| Pendiente | Corrección | Evidencia (Chrome) | Resultado |
|---|---|---|---|
| `#toast` se ocultaba con `hidden` (no se anunciaba) | Región `role="status" aria-live="polite"` persistente; se alterna la clase `show` (`index.html:19`, `core/ui.js:49-55`, `css/components.css:473-495`) | `hidden=false` siempre; al llamar `toast()` clase `show`, opacidad 1; a los 4.5 s texto vacío y opacidad 0 | Pasa |
| Reportes: todos los filtros siempre visibles; tipos sin acceso | Filtros por tipo (`reportes/web/model.js` `FILTERS`, `reportes/web/controller.js:15-26`); el selector ya omite los tipos sin permiso | Bibliotecario: sin "Listado de usuarios"; existencia → planta/pasillo/librero/tema; préstamos y indicadores → desde/hasta; alumnos con adeudos → incluir docentes; catálogo → ninguno | Pasa |
| Baja de ejemplar sin placeholder | `<option value="">Selecciona motivo</option>`, `required` + aviso (`catalogo/web/view.js:86`, `catalogo/web/controller.js`) | Sin motivo: "Selecciona el motivo de baja del ejemplar." y no abre el diálogo | Pasa |
| Catalogar pendiente sin precio | `GET /api/libros/pendientes` incluye `precio_unitario` (`catalogo/model.py`); el formulario lo precarga (`catalogo/web/controller.js:30`) | Línea de 42.50 USD: el formulario trae `precio_referencia` 42.5, 2 ejemplares y el título | Pasa |
| Compras: enviar en 4 clics | "Guardar y enviar" (`compras/web/controller.js:44-57`, `view.js:53`); `docs/operacion.md` D-17 actualizado | Compras -> Nueva solicitud -> Guardar y enviar: queda "enviada" (3 clics) | Pasa |
| Re-verificación de la reconstrucción | — | "Guardar solicitud" crea la solicitud (comprobante, mensaje de guardado); presupuesto excedido: "La solicitud excede el presupuesto mensual. El total (USD 999,999.00) excede el presupuesto disponible del mes (USD 2,490.00)."; `#/usuarios` con BIB001 muestra "Acceso restringido" (403, no "no encontrado"); `#/adeudos/1/cancelar` con BIB001 restringido y sin botón Cancelar | Pasa |

**Medición con el dataset de volumen (D-15; `docs/operacion.md` sección 3)**

| | Una a la vez (p95 máx.) | 20 concurrentes (p95 máx.) | Escrituras (p95 máx.) |
|---|---|---|---|
| Demo | 0.046 s | 0.226 s | 0.066 s |
| Volumen (5 000 usuarios, 10 002 ejemplares, 20 664 préstamos) | 0.281 s | 2.430 s (`reportes/prestamos` de 20 664 filas) | 0.064 s |

La primera medición con volumen falló (p95 4.5 s usuarios, 9.3 s préstamos, 30 s lista de espera con 20 concurrentes). Correcciones: mantenimiento de la lista de espera solo de los libros que lo requieren (`espera/model.py:87`), tope `?limite=` en usuarios/préstamos/multas (`core/repo.py:154-170`) y 4 procesos de gunicorn (`Dockerfile:3`). Segunda medición: todo ≤ 3 s. Datos de la prueba: BD `librigest_volumen`, eliminada al terminar.

**Cierre de requisitos de código (esta ronda):** PS-MET-02/03 (reporte `indicadores`), PS-S3-06 (bitácora de errores), PS-S1-12 y RNF-03/05/11/13 (dataset y medición), RNF-06/07 (auditoría y clics), PS-S4-02 (guion UAT, solo parcial), PS-S4-03 (token configurable, cookie `Secure`, TLS documentado, parcial), PS-S0-08/PS-S2-15 (hoja de firma; siguen 🟡).

**Pendiente de personas:** firma del PO (`decisiones_para_validacion.md`), ejecución del UAT con usuarios (`docs/uat.md`), cronometraje en mostrador (PS-MET-01), despliegue de TLS y servicios externos reales (⛔).
