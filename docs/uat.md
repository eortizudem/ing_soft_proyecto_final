# LibriGest - Guion de pruebas de aceptación de usuario (UAT, PS-S4-02)

Guion formal por rol para que el Product Owner y los usuarios de la biblioteca acepten el sistema. Cada caso tiene
precondiciones, pasos, resultado esperado y requisitos que cubre. La columna **Resultado** se llenó con la ejecución E2E en
Chrome del **2026-10-27** (ejecutor: equipo de desarrollo, no usuarios finales). La **firma de aceptación** de los usuarios
sigue pendiente, por eso PS-S4-02 permanece en 🟡 (ver `docs/requisitos/matriz_trazabilidad.md`).

Nota: el E2E de 2026-10-27 se registró por flujo (15 flujos pasaron), no caso por caso; **Pasa** en un caso significa que el flujo que lo contiene pasó y el comportamiento está cubierto por pruebas `pytest`. Los usuarios deben repetir los casos para firmar.

Leyenda: **Pasa** = ejecutado y cumplido; **Pasa (pytest)** = verificado con prueba automática y revisión de la pantalla, sin
recorrido completo en Chrome; **No ejecutado** = pendiente de ejecución por el usuario.

**Preparación común:** `python3 scripts/recrear_db.py -y` y `python3 scripts/levantar.py`; abrir http://localhost:8000.
Cuentas (contraseñas en `README.md`): ADM001 (Administrador), BIB001 (Bibliotecario), CAT001 (Catálogo), COM001 (Compras),
COL001 (Colaborador), DOC001 (Docente), A0512345 María, A0512980 Carlos (préstamo vencido), A0513001 Laura (adeudo pendiente).
Los pasos van desde la pantalla de inicio y cuentan los clics de la barra lateral.

## 1. Visitante (sin cuenta)

| # | Caso | Precondición | Pasos | Resultado esperado | Requisitos | Resultado |
|---|---|---|---|---|---|---|
| V-01 | Buscar y ubicar un libro | Pantalla de acceso | "Entrar como visitante" -> Buscar -> escribir "algoritmos" -> Ver | Lista con disponibilidad; la ficha muestra planta, pasillo, librero y nivel | RF-14, RF-15, RF-09, RN-01 | Pasa |
| V-02 | Visitante sin accesos de personal | Sesión de visitante | Abrir `#/usuarios` y `#/prestamos` | Pantalla "Acceso restringido" (no "no encontrado") | RF-01, RF-02, D-26 | Pasa |
| V-03 | Asistente sin datos personales | Sesión de visitante | Asistente -> "¿qué libros tengo prestados?" | Pide iniciar sesión; no muestra datos | RF-29, D-13, D-26 | Pasa |
| V-04 | Recuperar contraseña (demo) | `DEMO_MOSTRAR_TOKEN=true` | Acceso -> "Olvidé mi contraseña" -> correo `maria@ducky.edu.mx` -> copiar código -> nueva contraseña | Contraseña cambiada; con `DEMO_MOSTRAR_TOKEN=false` no se muestra el código y queda en Notificaciones | RNF-01, PS-S4-03 | Pasa (pytest) |

## 2. Alumno y docente (consulta y autoservicio)

| # | Caso | Precondición | Pasos | Resultado esperado | Requisitos | Resultado |
|---|---|---|---|---|---|---|
| A-01 | Consultar disponibilidad | A0512345 | Buscar -> filtro disponibilidad "agotado" | Solo libros sin ejemplares; botón de lista de espera | RF-14, RF-15, RF-22 | Pasa |
| A-02 | Unirse a la lista de espera | Libro agotado | Ver libro -> "Unirme a la lista" | Posición 1 (FIFO); no se puede repetir (409/422) | RF-22, D-19 | Pasa |
| A-03 | Consultar mi estado con el asistente | A0512980 | Asistente -> "tengo libros vencidos?" | Responde con el préstamo vencido y la multa estimada | RF-30, RF-31, RN-03 | Pasa |
| A-04 | Pedir un libro ("busco un libro") | Cualquier sesión | Asistente -> "busco un libro de cálculo" | Sugiere libros con ubicación | RF-29, RF-32 | Pasa |
| A-05 | Pasar a un bibliotecario | A0512345 | Asistente -> "quiero hablar con un bibliotecario" | Mensaje de registro; aparece en la lista de consultas para el bibliotecario del personal | RF-33, D-13, PS-MET-03 | Pasa |
| A-06 | Ver mis notificaciones | Un aviso previo (p. ej. recibo) | Notificaciones -> Mis notificaciones | Solo los avisos propios, marcados "Simulado" | RNF-10, D-11, D-27 | Pasa |
| A-07 | Alumno sin permisos de personal | A0512345 | Abrir `#/prestamos`, `#/reportes` | "Acceso restringido" | RF-02, D-27 | Pasa |

## 3. Bibliotecario (BIB001)

| # | Caso | Precondición | Pasos | Resultado esperado | Requisitos | Resultado |
|---|---|---|---|---|---|---|
| B-01 | Prestar un libro (3 clics) | A0512345 sin adeudos; LIB002 disponible | Préstamos y devoluciones -> Nuevo préstamo -> matrícula + clave -> Confirmar | Recibo con folio y vencimiento a 5 días hábiles; ejemplar "prestado"; aviso simulado | RN-01, RN-05, RF-17..20, RNF-10 | Pasa |
| B-02 | Rechazo por multa pendiente | A0513001 (Laura) | Nuevo préstamo con su matrícula | Rechazo con motivo "adeudos pendientes"; sin préstamo | RN-01, RN-03, RF-18 | Pasa |
| B-03 | Rechazo por préstamo vencido | A0512980 (Carlos) | Nuevo préstamo con su matrícula | Rechazo con motivo "préstamos vencidos" | RN-01, D-24 | Pasa |
| B-04 | Límite de ejemplares | María con 2 préstamos | Un tercer préstamo | Rechazo por límite (alumno 2) | RN-01, D-01 | Pasa |
| B-05 | Renovar (3 clics) | Préstamo activo de alumno | Préstamos -> Renovar (fila) -> Confirmar | Vencimiento + 5 días hábiles; contador 1/2; tras 2 renovaciones se rechaza | RN-02, RN-06, RF-21, D-05 | Pasa |
| B-06 | Devolver (3 clics) | Préstamo activo | Préstamos -> Devolver (fila) -> Confirmar | Ejemplar "disponible"; si hay retraso, adeudo de $10 por día hábil; aviso al primero de la espera | RF-23, RF-24, RN-03, D-19 | Pasa |
| B-07 | Lista de espera avanza | Libro agotado con espera | Devolver un ejemplar de ese libro | El primero queda "notificado" con reservado de 2 días hábiles | RF-22, D-19 | Pasa |
| B-08 | Registrar pago (3 clics) | Adeudo pendiente | Multas y pagos -> Registrar pago (fila) -> referencia -> Confirmar | Adeudo "pagado" con referencia de Tesorería | RF-26, RF-27, D-10, PS-MET-04 | Pasa |
| B-09 | Reportar pérdida / daño | Préstamo activo | Multas y pagos -> Pérdida (o Daño) -> Confirmar | Adeudo = valor de reposición (USD x tipo de cambio) o % de daño; ejemplar "baja" | RN-04, RF-25, D-07, D-08 | Pasa |
| B-10 | Cancelar no disponible | BIB001 | Abrir `#/adeudos/1/cancelar` | "Acceso restringido"; no hay botón Cancelar | RF-02, D-04 | Pasa |
| B-11 | Reporte de alumnos con adeudos y aviso | Carlos y Laura con deuda | Reportes -> Alumnos con adeudos -> Generar -> "Enviar aviso" | Lista correcta (D-09); aviso a Servicios Escolares en Notificaciones | RF-28, D-09 | Pasa |
| B-12 | Filtros por tipo de reporte | BIB001 | Reportes -> cambiar el tipo | Inventario por estante muestra planta/pasillo/librero/tema; Préstamos y Indicadores, desde/hasta; Alumnos con adeudos, "incluir docentes"; Catálogo, ninguno; no aparece "Listado de usuarios" | RF-16, RNF-06 | Pasa |
| B-13 | Indicadores | Datos demo | Reportes -> Indicadores -> Generar | % de conversaciones sin pasar a bibliotecario, consultas para el bibliotecario pendientes, discrepancias de inventario y préstamos por mes; el tiempo de atención figura "No disponible" | PS-MET-02, PS-MET-03, CTX-03 | Pasa (pytest) |
| B-14 | Errores | Un error registrado | Reportes -> Errores -> Generar | Tabla con fecha, origen (servidor/cliente), usuario y detalle | PS-S3-06 | Pasa (pytest) |
| B-15 | Resolver una consulta | B-A-05 hecho | Asistente -> Consultas para el bibliotecario -> Resolver | La conversación pasa a resuelta | RF-33 | Pasa |
| B-16 | Inventario por estante | Catálogo demo | Reportes -> Inventario por estante -> planta "Planta baja" | Listado con columna "Conteo físico" en blanco | RF-16, CTX-04, D-21 | Pasa |

## 4. Catálogo (CAT001)

| # | Caso | Precondición | Pasos | Resultado esperado | Requisitos | Resultado |
|---|---|---|---|---|---|---|
| C-01 | Registrar libro (3 clics) | CAT001 | Catálogo -> Registrar libro -> llenar -> Guardar | Ficha creada con N ejemplares y etiqueta imprimible | RF-07, RF-09, RF-11 | Pasa |
| C-02 | Baja de ejemplar con motivo | Libro con ejemplares disponibles | Ficha -> "Dar de baja" sin elegir motivo | Mensaje "Selecciona el motivo de baja"; con motivo, confirma y registra la baja | RF-11, RN-04 | Pasa |
| C-03 | Catalogar un título recibido | Compra recibida con título nuevo | Catálogo -> Pendientes de catalogar -> Catalogar | El formulario trae título, ejemplares y **precio de referencia** de la línea comprada | RF-06, RF-07, D-25 | Pasa |
| C-04 | Libro "reservado" | CAT001 | Editar libro -> tipo de uso "reservado" | No se presta (rechazo por no prestable); se consulta en mostrador | RF-10, D-20 | Pasa |
| C-05 | Importar CSV | Archivo con cabecera válida | Catálogo -> Importar CSV -> Importar | Resumen de altas y errores por fila | PS-S1-12 | Pasa |
| C-06 | Sin acceso a préstamos | CAT001 | Abrir `#/prestamos` | "Acceso restringido" | RF-02 | Pasa |

## 5. Compras (COM001) y Colaborador (COL001)

| # | Caso | Precondición | Pasos | Resultado esperado | Requisitos | Resultado |
|---|---|---|---|---|---|---|
| P-01 | Guardar solicitud (3 clics) | Presupuesto disponible | Compras -> Nueva solicitud -> Guardar solicitud | Solicitud "pendiente" con comprobante; mensaje de guardado | RF-05, RNF-07, D-17 | Pasa |
| P-02 | Guardar y enviar (3 clics) | Ídem | Compras -> Nueva solicitud -> Guardar y enviar | Solicitud "enviada" a Tesorería | RF-05, D-17 | Pasa |
| P-03 | Revisar y enviar | Ídem | Nueva solicitud -> Revisar y enviar -> Confirmar y enviar | Solicitud "enviada" (4 clics, con pantalla de revisión) | RF-05 | Pasa |
| P-04 | Presupuesto excedido | Total > disponible del mes | Guardar y enviar con USD 999,999 | "La solicitud excede el presupuesto mensual" con total y disponible; no se crea | RO-02, D-22 | Pasa |
| P-05 | Recibido por partes con factura | Solicitud enviada | Ver comprobante -> Recibir pedido -> folio, monto, cantidades | Estado "recibida"/parcial; ejemplares agregados; aviso a Tesorería; títulos nuevos pendientes de catalogar | RF-06, D-25 | Pasa |
| P-06 | Cancelar solicitud | Solicitud pendiente/enviada sin pedidos recibidos | Comprobante -> Cancelar | Estado "cancelada"; se libera el presupuesto | D-22 | Pasa |
| P-07 | Colaborador sin préstamos | COL001 | Abrir `#/prestamos` | "Acceso restringido"; sí ve Catálogo y Compras | D-12 | Pasa |

## 6. Administrador (ADM001)

| # | Caso | Precondición | Pasos | Resultado esperado | Requisitos | Resultado |
|---|---|---|---|---|---|---|
| M-01 | Alta de usuario | ADM001 | Usuarios -> Nuevo -> llenar -> Guardar | Usuario creado con credenciales iniciales visibles una vez | RF-03 | Pasa |
| M-02 | Baja y reactivación | Usuario sin préstamos | Usuarios -> ficha -> Baja / Reactivar | Estado cambia; no se puede dar de baja con préstamos abiertos ni al último administrador | RF-03, RF-04 | Pasa |
| M-03 | Historial del usuario | Usuario con actividad | Usuarios -> ficha | Préstamos, renovaciones, adeudos, espera y bitácora | RF-04 | Pasa |
| M-04 | Perfiles y permisos | ADM001 | Perfiles -> cambiar una casilla -> Guardar | La matriz persiste; el administrador conserva sus permisos | RF-01, RF-02 | Pasa |
| M-05 | Políticas de préstamo | ADM001 | Perfiles -> editar política del alumno | Los nuevos valores aplican al siguiente préstamo | D-01, D-04 | Pasa |
| M-06 | Cancelar un adeudo | Adeudo pendiente | Multas y pagos -> ficha -> Cancelar -> motivo | Adeudo "cancelado" con motivo; solo el administrador | RF-26, D-04 | Pasa |
| M-07 | Importar lista de alumnos / actualizar la lista | CSV o archivo simulado | Usuarios -> Actualizar lista o Importar lista | Altas, cambios y bajas con fuente `servicios_escolares` | RF-03, D-23 | Pasa |
| M-08 | Todos los reportes | ADM001 | Reportes -> cada tipo -> PDF e Imprimir | Se genera y se registra en `reporte_generado` | RF-16, RF-28 | Pasa |
| M-09 | lista de avisos | Avisos previos | Notificaciones -> filtrar canal | Avisos simulados con canal, destino y asunto | RNF-10, D-11 | Pasa |
| M-10 | Inicio y tableros | ADM001 | Inicio | Tarjetas de resumen y accesos según rol | CTX-04 | Pasa |

## 7. Transversales (todos los roles)

| # | Caso | Pasos | Resultado esperado | Requisitos | Resultado |
|---|---|---|---|---|---|
| T-01 | Menú por rol | Entrar con cada cuenta | Solo aparecen las secciones del rol (tabla en matriz, sección 9) | RF-01, RF-02 | Pasa |
| T-02 | Móvil 390 px | Recorrer 29 rutas | Sin desbordamiento horizontal; asistente en `#/movil/asistente` | RNF-06, RNF-14 | Pasa |
| T-03 | Accesibilidad | Teclado, lector de pantalla, contraste | `lang="es"`, etiquetas, foco atrapado en diálogos, regiones `aria-live` (el aviso `#toast` es persistente), contraste >= 4.5:1 | RNF-06, D-16 | Pasa |
| T-04 | 3 clics | Los 7 procesos de D-17 | Máximo 3 clics cada uno | RNF-07, D-17 | Pasa |
| T-05 | Estilos uniformes | Revisar 41 rutas | Mismos márgenes, filtros y campos | U6 | Pasa |
| T-06 | Rendimiento | `medir_rendimiento.py --escritura` con el dataset de volumen | p95 <= 3 s (máx. 2.43 s con 20 concurrentes) | RNF-03/05/11/13, D-15 | Pasa |
| T-07 | Respaldo y restauración | `respaldo.py` y `restaurar.py --verificar` | Conteos coinciden | RNF-02, D-14 | Pasa (documentado en `docs/operacion.md`) |
| T-08 | Error del servidor visible en bitácora | Provocar un 500 (prueba automática) | Fila `error_sistema` con origen servidor | PS-S3-06 | Pasa (pytest) |

## 8. Aceptación

| Rol | Nombre | Casos ejecutados por el usuario | Aceptado (sí/no) | Firma y fecha |
|---|---|---|---|---|
| Product Owner | Pendiente | 0 de 58 | Pendiente | Pendiente |
| Bibliotecario | Pendiente | 0 de 16 | Pendiente | Pendiente |
| Administrador | Pendiente | 0 de 10 | Pendiente | Pendiente |

Las decisiones que condicionan varios casos están en `docs/requisitos/decisiones_para_validacion.md`.
