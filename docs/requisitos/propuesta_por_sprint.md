# LibriGest (Biblioteca Ducky) - Checklist de requisitos de la Propuesta de Negocio por Sprint

Fuente: `Propuesta_de_Negocio_Proyecto_por_Sprint.docx.pdf` (16 páginas, fechada 11 de septiembre de 2026, San Pedro Garza García, N.L.). Equipo/empresa: SprintForge. Maestro: Felipe de Jesús Rodríguez García.

Convenciones:
- El documento NO define IDs propios ni historias de usuario formales (el documento dice que cada requerimiento se convertirá en épicas/historias en el Product Backlog, sección 4). Se usan IDs `PS-<sprint>-NN` para requisitos por sprint, y `PS-GEN-NN`, `PS-NFR-NN`, `PS-TEC-NN`, `PS-DOD-NN`, `PS-ALC-NN`, `PS-RIE-NN`, `PS-SUP-NN`, `PS-PRC-NN`, `PS-TYC-NN` para transversales.
- Texto entre comillas = verbatim; sin comillas = casi verbatim.
- `[AMBIGUO]` = ambigüedad o hueco; ver sección 14.
- Pág. = página del PDF.
- Casilla `[ ]` = pendiente de implementar/verificar.

---

## 0. Metadatos y stakeholders

| ID | Elemento | Detalle |
|---|---|---|
| PS-META-01 | Nombre del sistema | LibriGest ("sistema integral de gestión bibliotecaria organizado por sprints", "integral en la nube"). El nombre "Biblioteca Ducky" no aparece en el PDF (viene del encargo). |
| PS-META-02 | Equipo | Elihu Orlando Osuna Maltos (653447), Enrique Ortiz Davila (630757), Manuel Bonavena (625440), Santiago Ponguta Rubio (584354), Edmundo Mendoza (626995). Estudiantes de Ingeniería en Tecnologías Computacionales, Universidad de Monterrey, materia Ingeniería de Software. |
| PS-META-03 | Maestro | Felipe de Jesús Rodríguez García |
| PS-META-04 | Destinatarios | "Product Owner y representantes de la Biblioteca" |
| PS-META-05 | Declaración académica | "Doy mi palabra de que he realizado esta actividad con integridad académica." |
| PS-META-06 | Base de la propuesta | "estructurada a partir de la matriz de requerimientos del proyecto" (la matriz NO está incluida en el PDF; la sección "Fuentes base de la propuesta", pág. 16 según el índice, no aparece en el PDF entregado). |
| PS-META-07 | Compromiso del equipo | "comunicación constante, trazabilidad de requerimientos y validación al cierre de cada sprint". |

### Roles / actores del sistema (sección 2 y tabla de alcance)
- Perfiles diferenciados: alumno, profesor, colaborador, bibliotecario, administrador.
- Canal/usuarios por módulo (ver cada sprint): Administrador; Bibliotecario; Colaborador; "Todos los perfiles".
- Sistemas externos: Servicios Escolares, Tesorería, correo electrónico, WhatsApp. (RRHH NO se menciona en el PDF.) [AMBIGUO]

### Roles de proyecto (sección 5)
| Rol | Persona | Responsabilidades |
|---|---|---|
| Product Owner | Representante de la Biblioteca (no es parte del equipo de desarrollo; nombre sin definir) | Priorizar backlog, aclarar necesidades, definir valor y aceptar/rechazar entregables. |
| Scrum Master / Arquitectura | Elihu Orlando Osuna Maltos | Facilitar Scrum, remover bloqueos, coordinar arquitectura, riesgos e integración general. |
| Backend / APIs | Enrique Ortiz Davila | Servicios REST, autenticación, integraciones externas y notificaciones. |
| Base de datos / Reglas de negocio | Manuel Bonavena | Modelo de datos, transacciones, reglas de préstamos, renovaciones, multas y respaldo. |
| Frontend / UX-UI | Santiago Ponguta Rubio | Portal web, componentes reutilizables, accesibilidad y experiencia de usuario. |
| QA / Chatbot / Documentación | Edmundo Mendoza | Plan de pruebas, criterios de aceptación, módulo de chatbot, manuales y evidencias de calidad. |

Otros stakeholders: "responsable técnico por sistema" designado por el cliente (Servicios Escolares, Tesorería) (PS-RIE-02); el equipo "se organiza por especialidad, manteniendo colaboración cruzada para evitar dependencias de una sola persona".

---

## 1. Resumen ejecutivo y metas globales (pág. 3)

- [ ] **PS-GEN-01** "LibriGest se propone como una plataforma integral para centralizar los procesos principales de la Biblioteca." Componentes: portal web, acceso móvil "para las funciones definidas en alcance" y "servicios de integración con entidades institucionales".
- [ ] **PS-GEN-02** Desarrollo por sprints, "con revisiones y criterios de aceptación al cierre de cada incremento".
- [ ] **PS-GEN-03** Alcance funcional: "Usuarios, catálogo, búsqueda, préstamos, devoluciones, multas, notificaciones y chatbot."
- [ ] **PS-GEN-04** Duración: "10 semanas, distribuidas en 5 sprints (Sprint 0 a Sprint 4) incluyendo integración, QA y despliegue."
- [ ] **PS-GEN-05** Capacidad: 37.5 horas-equipo/semana (5 integrantes x 1.5 h diarias x 5 días). Esfuerzo total 375 horas-equipo. Inversión $93,750 MXN cotizada por sprint.
- [ ] **PS-GEN-06** Metas clave: "Respuesta ≤ 3 s; catálogo en tiempo real; navegación ≤ 3 clics; chatbot 24/7; validación automática de reglas."
- [ ] **PS-GEN-07** Objetivo del proyecto: "Diseñar e implementar una solución modular que centralice la operación bibliotecaria definida en la matriz de requerimientos, automatice las reglas de negocio, mantenga trazabilidad de las operaciones y permita integrar de manera segura los procesos con sistemas institucionales."
- [ ] **PS-GEN-08** Objetivos transversales (carta): seguridad, desempeño y facilidad de uso.
- [ ] **PS-GEN-09** Solución "en la nube", arquitectura "modular y APIs bien definidas para facilitar el mantenimiento, integración y crecimiento".

### 1.1 Problema y desafíos (pág. 4)
| Desafío | Necesidad | Impacto |
|---|---|---|
| Gestión de usuarios y permisos | Altas, bajas, cambios, roles e historial consistentes y con acceso controlado. | Información duplicada, accesos incorrectos, consultas lentas. |
| Catálogo y disponibilidad | Existencia física e información del catálogo actualizadas en tiempo real. | Inconsistencias entre sistema y realidad. |
| Préstamos y devoluciones | Reglas específicas por tipo de usuario, renovaciones, vencimientos, multas y lista de espera. | Errores operativos, cálculos manuales, dificultad de aplicar reglas uniformes. |
| Integraciones institucionales | "Pérdidas, pagos y datos de alumnos/profesores requieren comunicación con sistemas externos." | Retrabajo y demoras si se transfiere manualmente. |
| Atención al usuario | Horarios, políticas, disponibilidad y estatus generan consultas recurrentes. | Carga de trabajo del personal y respuestas fuera de horario. |

### 1.2 Línea base y metas medibles (pág. 4-5)
Las cifras son "estimaciones construidas a partir de la matriz de requerimientos y de la operación descrita por el cliente; se validarán durante el levantamiento del Sprint 0 y se adoptarán como métricas de éxito del proyecto."

- [ ] **PS-MET-01** Tiempo de registro de préstamo/devolución: actual 4-6 min por operación (captura y validación manual). Meta: "Menos de 1 minuto, con validación automática y recibo generado."
- [ ] **PS-MET-02** Consistencia catálogo vs existencia física: actual 5%-10% de discrepancias en inventarios parciales. Meta: "Menos del 1%, con actualización en tiempo real y trazabilidad por ejemplar."
- [ ] **PS-MET-03** Consultas repetitivas atendidas por el personal: actual ~40% (horarios, políticas, disponibilidad, estatus). Meta: atendidas por chatbot 24/7, "con escalamiento sólo cuando se requiere."
- [ ] **PS-MET-04** Conciliación de multas y pagos con Tesorería: actual 2-3 días hábiles por envío y cotejo manual. Meta: "Mismo día, mediante integración y registro automático del pago."
- [ ] **PS-MET-05** Disponibilidad del servicio de consulta: actual limitada al horario presencial. Meta: consulta de catálogo y estatus disponible "de forma continua en Web y App."

---

## 2. Solución propuesta (pág. 5): qué incluye (transversal)

- [ ] **PS-GEN-10** Módulo de gestión de usuarios: perfiles diferenciados (alumno, profesor, colaborador, bibliotecario y administrador), altas, roles y permisos, historial por usuario, autenticación y respaldo/restauración de información.
- [ ] **PS-GEN-11** Catálogo y mantenimiento del acervo: solicitud y recepción de material, ficha bibliográfica completa, alta y ubicación física del ejemplar, control de estados, bajas y actualizaciones, e inventarios parciales.
- [ ] **PS-GEN-12** Búsqueda multiplataforma: por autor, tema, título, clave o editorial, con existencia, ubicación y disponibilidad real del ejemplar, desde Web y App.
- [ ] **PS-GEN-13** Préstamos y devoluciones: validación automática de reglas por tipo de usuario, generación de recibos, control de vigencias y renovaciones, lista de espera, cálculo de multas por vencimiento y registro de pagos.
- [ ] **PS-GEN-14** Integraciones institucionales: Servicios Escolares y Tesorería para datos de alumnos y profesores, pérdidas y pagos; notificaciones por correo electrónico y WhatsApp.
- [ ] **PS-GEN-15** Chatbot 24/7: preguntas frecuentes, búsqueda de material, consulta del estatus propio, explicación de reglas de préstamo y escalamiento al bibliotecario cuando la consulta lo requiera.
- [ ] **PS-GEN-16** Acceso multiplataforma: portal web para la operación completa; app móvil solo para búsqueda y chatbot; roles diferenciados y control de acceso por permisos.

### Beneficios tangibles / criterios de valor (pág. 6)
- [ ] **PS-GEN-17** Catálogo y disponibilidad sincronizados en tiempo real.
- [ ] **PS-GEN-18** Validación automática de reglas de préstamo y renovación, aplicadas de forma uniforme.
- [ ] **PS-GEN-19** Tiempo de respuesta objetivo no mayor a 3 s "en las operaciones incluidas en los requerimientos".
- [ ] **PS-GEN-20** Navegación "orientada a completar procesos en un máximo de 3 clics cuando aplique."
- [ ] **PS-GEN-21** Notificaciones por email/WhatsApp para recibos y estatus de préstamos, "sujetas a disponibilidad de las APIs contratadas."
- [ ] **PS-GEN-22** Atención 24/7 mediante chatbot para consultas frecuentes y escalamiento a Bibliotecario.
- [ ] **PS-GEN-23** Trazabilidad de operaciones, historial por usuario y evidencia de aceptación por sprint.

---

## 3. Alcance funcional y plan por sprint

Tabla de alcance (págs. 5-6) y plan (pág. 11) combinados.

| Sprint | Calendario | Esfuerzo | Inversión | Entregable principal | Hito de aceptación |
|---|---|---|---|---|---|
| S0 | Sem. 1-2 | 75 h | $18,750 MXN | Gestión de usuarios, roles, autenticación, historial, backup/restore | Base segura y operativa para los siguientes módulos |
| S1 | Sem. 3-4 | 75 h | $18,750 MXN | Mantenimiento y búsqueda de libros, catálogo en tiempo real, accesibilidad | Catálogo utilizable y consulta de disponibilidad |
| S2 | Sem. 5-7 | 112.5 h | $28,125 MXN | Préstamos, renovaciones, devoluciones, multas, lista de espera y notificaciones | Ciclo bibliotecario completo con reglas automatizadas |
| S3 | Sem. 8-9 | 75 h | $18,750 MXN | Chatbot, FAQ, búsqueda, estatus propio, reglas y escalamiento | Atención digital 24/7 en Web y App |
| S4 | Sem. 10 | 37.5 h | $9,375 MXN | Regresión, UAT, seguridad, rendimiento, despliegue, capacitación y manuales | Versión candidata a producción y acta de aceptación |

Nota (pág. 11): "Cada sprint incluye análisis, construcción, pruebas y revisión; el Sprint 4 se utiliza para endurecimiento, aceptación final, despliegue y capacitación." Las horas son "esfuerzo total del equipo, no horas por persona".

### SPRINT 0 - Gestión de usuario (Sem. 1-2, 75 h, $18,750)
Módulo: Gestión de usuario. Canal/usuarios: Web, Administrador.

- [ ] **PS-S0-01** Perfiles de usuario diferenciados: alumno, profesor, colaborador, bibliotecario, administrador. Actor: Administrador. [AMBIGUO: no define permisos de cada perfil; ver sección 14.]
- [ ] **PS-S0-02** Roles y permisos (RBAC): "permisos por rol", mínimo privilegio.
- [ ] **PS-S0-03** Altas, bajas y cambios de usuarios.
- [ ] **PS-S0-04** Historial por usuario.
- [ ] **PS-S0-05** Autenticación: usuario/contraseña, JWT, contraseñas "almacenadas mediante hash seguro".
- [ ] **PS-S0-06** Backup/restore de información; backups programados y "prueba documentada de restauración".
- [ ] **PS-S0-07** Hito: "Base segura y operativa para los siguientes módulos."
- [ ] **PS-S0-08** Taller de reglas de negocio en Sprint 0 (mitigación de riesgo): matriz de decisión validada por el Product Owner antes de iniciar el Sprint 2 (por tipo de usuario: préstamos, renovación, multas).
- [ ] **PS-S0-09** Levantamiento y validación de la línea base de métricas (PS-MET-01..05) durante el Sprint 0.
- [ ] **PS-S0-10** Infraestructura de despliegue y accesos disponibles desde el Sprint 0 (supuesto del cliente, PS-SUP-04).
- [ ] **PS-S0-11** Migración/importación del padrón de usuarios: el padrón "puede exportarse en formato tabular estándar" (supuesto PS-SUP-03). [AMBIGUO: no se asigna a un sprint la carga; el diagnóstico de datos está en S1.]

### SPRINT 1 - Mantenimiento de libros y Búsqueda de libros (Sem. 3-4, 75 h, $18,750)
Módulo "Mantenimiento de libros": Web, Administrador, Bibliotecario, Colaborador.
Módulo "Búsqueda de libros": App + Web, Todos los perfiles.

- [ ] **PS-S1-01** Solicitud y recepción de material.
- [ ] **PS-S1-02** Ficha bibliográfica completa.
- [ ] **PS-S1-03** Alta y ubicación física del ejemplar.
- [ ] **PS-S1-04** Control de estados del ejemplar.
- [ ] **PS-S1-05** Bajas y actualizaciones de ejemplares.
- [ ] **PS-S1-06** Filtros (en mantenimiento de libros).
- [ ] **PS-S1-07** Inventarios parciales.
- [ ] **PS-S1-08** Búsqueda por autor / tema / título / clave / editorial, mostrando existencia, ubicación y disponibilidad e inventarios parciales. Canal: App móvil (React Native/Expo) + Web, todos los perfiles.
- [ ] **PS-S1-09** Catálogo "en tiempo real" (consistencia: transacciones de BD y validación de concurrencia).
- [ ] **PS-S1-10** Accesibilidad (listada en entregable S1 del plan): contraste, navegación por teclado, etiquetas, referencia WCAG 2.1 AA, apoyo a discapacidad visual.
- [ ] **PS-S1-11** Caché Redis de consultas de catálogo.
- [ ] **PS-S1-12** Diagnóstico de datos del acervo y padrón en Sprint 1, reglas de limpieza documentadas y carga de prueba antes del despliegue (mitigación PS-RIE-03).
- [ ] **PS-S1-13** Hito: "Catálogo utilizable y consulta de disponibilidad."
- Notas: los estados concretos del ejemplar (p. ej. disponible, prestado) y campos de la ficha NO se enumeran. [AMBIGUO]

### SPRINT 2 - Préstamos y Devoluciones (Sem. 5-7, 112.5 h, $28,125)
Ambos módulos: Web, Administrador y Bibliotecario.

Préstamos de libros:
- [ ] **PS-S2-01** Validaciones automáticas de reglas por tipo de usuario.
- [ ] **PS-S2-02** Recibos (generación de recibo).
- [ ] **PS-S2-03** Control de vigencias.
- [ ] **PS-S2-04** Renovaciones (validación automática).
- [ ] **PS-S2-05** Lista de espera.
- [ ] **PS-S2-06** Notificaciones por correo electrónico y WhatsApp (recibos y estatus de préstamos); correo como "canal mínimo garantizado".

Devolución de libros:
- [ ] **PS-S2-07** Actualización de disponibilidad.
- [ ] **PS-S2-08** Vencimientos.
- [ ] **PS-S2-09** Multas (cálculo por vencimiento).
- [ ] **PS-S2-10** Avisos.
- [ ] **PS-S2-11** Registro de pagos.

Integraciones y metas asociadas:
- [ ] **PS-S2-12** Integración con Tesorería (pérdidas y pagos; conciliación mismo día, PS-MET-04) y Servicios Escolares (datos de alumnos/profesores). En S2 se desarrolla "contra servicios simulados"; conexión real en S4 (PS-RIE-02).
- [ ] **PS-S2-13** Tiempo de registro de préstamo/devolución < 1 min, con recibo (PS-MET-01).
- [ ] **PS-S2-14** Hito: "Ciclo bibliotecario completo con reglas automatizadas."
- [ ] **PS-S2-15** Precondición: matriz de decisión de reglas validada por el Product Owner antes de iniciar S2.
- Notas: NO se dan parámetros concretos de reglas (días de préstamo, nº de renovaciones, tarifa de multa, tope de multa, tamaño de la lista de espera, canal/plazo de avisos). [AMBIGUO]

### SPRINT 3 - Chatbot (Sem. 8-9, 75 h, $18,750)
Canal: App + Web, todos los perfiles.

- [ ] **PS-S3-01** FAQ (preguntas frecuentes).
- [ ] **PS-S3-02** Búsqueda de material por chatbot.
- [ ] **PS-S3-03** Consulta del estatus propio (con "control de acceso a datos personales").
- [ ] **PS-S3-04** Explicación de reglas de préstamo/negocio.
- [ ] **PS-S3-05** Escalamiento al bibliotecario cuando la consulta lo requiera.
- [ ] **PS-S3-06** Disponibilidad 24/7 "sujeto a la disponibilidad de infraestructura y servicios externos"; validada con monitoreo, reinicio automático y registro de incidentes.
- [ ] **PS-S3-07** Tecnología: motor híbrido de intents + base de conocimiento.
- [ ] **PS-S3-08** Meta: absorber el ~40% de consultas repetitivas (PS-MET-03).
- [ ] **PS-S3-09** Hito: "Atención digital 24/7 en Web y App."
- Notas: el mecanismo de escalamiento (canal, SLA, handoff) no está definido. [AMBIGUO]

### SPRINT 4 - Integración y cierre (Sem. 10, 37.5 h, $9,375)
Canal/usuarios: Transversal.

- [ ] **PS-S4-01** Regresión.
- [ ] **PS-S4-02** Pruebas de aceptación (UAT).
- [ ] **PS-S4-03** Seguridad (pruebas de seguridad, HTTPS/TLS, registros de acceso, revisión de permisos).
- [ ] **PS-S4-04** Rendimiento (pruebas de carga, medición de endpoints críticos; <= 3 s).
- [ ] **PS-S4-05** Despliegue (Docker + nube institucional/comercial, reproducible).
- [ ] **PS-S4-06** Capacitación.
- [ ] **PS-S4-07** Documentación y manuales.
- [ ] **PS-S4-08** Conexión real a Servicios Escolares y Tesorería (sustituye servicios simulados).
- [ ] **PS-S4-09** Holgura reservada en S4 por capacidad acotada del equipo (PS-RIE-06).
- [ ] **PS-S4-10** Hito: "Versión candidata a producción y acta de aceptación."
- [ ] **PS-S4-11** Garantía de 30 días naturales inicia con la "aceptación final" (PS-TYC-09).

---

## 4. Requisitos no funcionales y controles de calidad (pág. 7-8)

| ID | Atributo | Meta | Cómo se valida |
|---|---|---|---|
| PS-NFR-01 | Rendimiento | Tiempo de respuesta ≤ 3 s en operaciones normales del alcance | Pruebas de carga y medición de endpoints críticos |
| PS-NFR-02 | Disponibilidad | Chatbot 24/7, sujeto a infraestructura y servicios externos | Monitoreo, reinicio automático y registro de incidentes |
| PS-NFR-03 | Usabilidad | Flujos principales completables en ≤ 3 clics cuando el proceso lo permita | Pruebas de tareas y revisión UX en Sprint Review |
| PS-NFR-04 | Accesibilidad | Interfaz multiplataforma y apoyo a discapacidad visual | Contraste, navegación por teclado, etiquetas y referencia WCAG 2.1 AA |
| PS-NFR-05 | Seguridad | Cifrado en tránsito, control de roles, mínimo privilegio y auditoría | HTTPS/TLS, registros de acceso, revisión de permisos y pruebas de seguridad |
| PS-NFR-06 | Respaldo | Backup y restore de información | Backups programados y prueba documentada de restauración |
| PS-NFR-07 | Consistencia | Catálogo y disponibilidad actualizados en tiempo real | Transacciones de base de datos y validación de concurrencia |

Otros NFR/controles: auditoría en BD (PS-TEC-04); backups automáticos, monitoreo y recuperación (PS-TEC-07); trazabilidad por ejemplar (PS-MET-02).

## 5. Restricciones técnicas (pág. 7)

| ID | Componente | Tecnología propuesta | Uso |
|---|---|---|---|
| PS-TEC-01 | Frontend Web | React + TypeScript | Portal responsivo: administración, catálogo, préstamos, devoluciones y "reportes operativos" |
| PS-TEC-02 | App móvil | React Native / Expo | Búsqueda de libros y chatbot; preparada para ampliar funciones móviles después |
| PS-TEC-03 | Backend/API | Node.js + NestJS o Express | Servicios REST, validación de reglas y capa de integración |
| PS-TEC-04 | Base de datos | PostgreSQL | Usuarios, roles, libros, ejemplares, préstamos, renovaciones, multas, pagos, espera y auditoría |
| PS-TEC-05 | Caché | Redis | Caché de consultas de catálogo; apoyo a sesiones/colas cuando sea necesario |
| PS-TEC-06 | Autenticación | JWT + RBAC | Usuario/contraseña, permisos por rol, hash seguro de contraseñas |
| PS-TEC-07 | Infraestructura | Docker + nube institucional/comercial | Despliegue reproducible, backups automáticos, monitoreo y recuperación |
| PS-TEC-08 | Integraciones | REST APIs / webhooks | Servicios Escolares, Tesorería, email y WhatsApp "conforme a credenciales disponibles" |
| PS-TEC-09 | Chatbot | Motor híbrido de intents + base de conocimiento | FAQ, búsqueda, estatus propio, reglas de negocio y escalamiento; control de acceso a datos personales |

Otras restricciones técnicas:
- [ ] **PS-TEC-10** Control de versiones en Git, ramas por funcionalidad y revisión de código (sección 4).
- [ ] **PS-TEC-11** Alcance móvil limitado a búsqueda y chatbot (PS-SUP-06).
- [ ] **PS-TEC-12** Integraciones vía API REST o servicio equivalente documentado (PS-SUP-05).
- [ ] **PS-TEC-13** Adaptadores intercambiables para APIs de terceros; correo como canal mínimo garantizado (PS-RIE-05).
- [ ] **PS-TEC-14** Notificaciones email/WhatsApp sujetas a APIs contratadas; costos de WhatsApp/correo transaccional/dominios/licencias fuera de precio.

---

## 6. Alcance: dentro y fuera

Dentro de alcance:
- [ ] **PS-ALC-01** Gestión de usuarios (perfiles, roles, historial, autenticación, backup/restore).
- [ ] **PS-ALC-02** Catálogo/mantenimiento del acervo, búsqueda multiplataforma.
- [ ] **PS-ALC-03** Préstamos, renovaciones, lista de espera, devoluciones, multas, registro de pagos.
- [ ] **PS-ALC-04** Integraciones con Servicios Escolares y Tesorería; notificaciones email y WhatsApp.
- [ ] **PS-ALC-05** Chatbot 24/7 con escalamiento.
- [ ] **PS-ALC-06** Portal web completo + app móvil solo búsqueda y chatbot.
- [ ] **PS-ALC-07** QA, UAT, seguridad, rendimiento, despliegue, capacitación, manuales.
- [ ] **PS-ALC-08** "El alcance base es la matriz de requerimientos proporcionada por el cliente y las historias aceptadas en el Product Backlog."

Fuera de alcance / no incluido (explícito):
- [ ] **PS-ALC-09** Funciones móviles distintas de búsqueda y chatbot (solo "preparada para ampliar").
- [ ] **PS-ALC-10** "Costos de nube, WhatsApp, correo transaccional, dominios o licencias externas no están incluidos salvo que se indiquen expresamente."
- [ ] **PS-ALC-11** IVA y servicios de terceros (inversión total "antes de IVA y servicios de terceros").
- [ ] **PS-ALC-12** Mantenimiento evolutivo, nuevas funciones o soporte después de la garantía: "se cotizan por separado".
- [ ] **PS-ALC-13** Cualquier solicitud no contemplada: se analiza en impacto, horas y costo; solo entra tras aprobación escrita y se incorpora a un sprint posterior.
- [ ] **PS-ALC-14** "No se atribuyen certificaciones externas que no estén documentadas" (aclaración sobre la experiencia del equipo).

---

## 7. Metodología y Definición de Terminado (pág. 9)

Scrum con entregas incrementales. Product Owner prioriza y acepta; Scrum Master facilita y elimina bloqueos; equipo construye y valida.

| ID | Práctica | Aplicación |
|---|---|---|
| PS-MET-10 | Backlog y trazabilidad | Cada requerimiento se convierte en épicas/historias de usuario con criterios de aceptación y relación directa con la matriz |
| PS-MET-11 | Sprint Planning | Objetivo del sprint, capacidad, historias comprometidas, riesgos y dependencias |
| PS-MET-12 | Ejecución y seguimiento | Daily breve, tablero de tareas, control de versiones en Git, ramas por funcionalidad y revisión de código |
| PS-MET-13 | Validación continua | Pruebas unitarias, integración y funcionales durante el sprint, no únicamente al final |
| PS-MET-14 | Sprint Review | Demostración al PO con datos de prueba; aceptación, rechazo justificado o retroalimentación |
| PS-MET-15 | Retrospective | Revisión de proceso, métricas, bloqueos y acciones de mejora |
| PS-MET-16 | Gestión de cambios | Cambios fuera del alcance se registran, estiman y aprueban antes de entrar al backlog de un sprint |

Definición de Terminado (DoD):
- [ ] **PS-DOD-01** Funcionalidad implementada y vinculada a un requerimiento o historia aprobada.
- [ ] **PS-DOD-02** Criterios de aceptación ejecutados y documentados.
- [ ] **PS-DOD-03** Código revisado por al menos otro integrante y almacenado en el repositorio del proyecto.
- [ ] **PS-DOD-04** Pruebas automáticas o manuales pertinentes completadas sin defectos críticos abiertos.
- [ ] **PS-DOD-05** Requisitos no funcionales aplicables verificados, "especialmente seguridad y respuesta ≤ 3 s".
- [ ] **PS-DOD-06** Demostración realizada y resultado registrado en Sprint Review.

Criterio de aceptación a nivel de sprint: aceptación documentada al cierre de cada Sprint Review; "El silencio del cliente no se considera aceptación automática."

---

## 8. Capacidad y esfuerzo (págs. 10-12)

- [ ] **PS-CAP-01** 5 integrantes x 1.5 h/día x 5 días/sem = 7.5 h/semana por integrante; 37.5 h-equipo/semana; 10 semanas; 375 h-equipo total. "Ningún sprint compromete más horas de las que el equipo puede entregar en las semanas asignadas."
- [ ] **PS-CAP-02** Distribución de esfuerzo: Análisis y diseño 62.5 h (16.7%); Desarrollo frontend y móvil 85 h (22.7%); Backend, datos e integraciones 105 h (28.0%); QA, seguridad y rendimiento 70 h (18.6%); Gestión, documentación y capacitación 52.5 h (14.0%); Total 375 h (100%).

## 9. Riesgos y mitigaciones (pág. 12)

| ID | Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|---|
| PS-RIE-01 | Reglas de préstamo, renovación y multas ambiguas o distintas por tipo de usuario | Alta | Alto | Taller de reglas en Sprint 0 y matriz de decisión validada por el PO antes de iniciar Sprint 2 |
| PS-RIE-02 | Retraso en credenciales y ambiente de prueba de Servicios Escolares y Tesorería | Media | Alto | Desarrollo contra servicios simulados desde Sprint 2 y conexión real en Sprint 4; el cliente designa un responsable técnico por sistema |
| PS-RIE-03 | Calidad insuficiente de datos del acervo y del padrón | Media | Alto | Diagnóstico de datos en Sprint 1, reglas de limpieza documentadas y carga de prueba antes del despliegue |
| PS-RIE-04 | Solicitudes de cambio durante la ejecución | Media | Medio | Control de cambios formal: estimación en horas y costo, aprobación escrita, incorporación a un sprint posterior |
| PS-RIE-05 | Indisponibilidad o limitaciones de APIs de terceros (WhatsApp, correo transaccional) | Media | Medio | Adaptadores intercambiables y correo electrónico como canal mínimo garantizado |
| PS-RIE-06 | Capacidad acotada del equipo (7.5 h semanales por integrante) | Alta | Medio | Alcance por sprint limitado a 37.5 h-equipo/semana, con holgura reservada en Sprint 4 |
| PS-RIE-07 | Ausencia del PO en la revisión de cierre de sprint | Baja | Alto | Agenda fija de Sprint Review desde el inicio; el silencio del cliente no constituye aceptación |

Cada riesgo tiene mitigación "asignada y revisable en la Sprint Review correspondiente".

## 10. Supuestos (pág. 13)

- [ ] **PS-SUP-01** El cliente designa un PO con autoridad para priorizar el backlog y aceptar entregables.
- [ ] **PS-SUP-02** La matriz de requerimientos entregada es la versión vigente y constituye el alcance base.
- [ ] **PS-SUP-03** El acervo y el padrón de usuarios pueden exportarse en formato tabular estándar para su migración.
- [ ] **PS-SUP-04** La infraestructura de despliegue está disponible desde el Sprint 0, junto con los accesos necesarios.
- [ ] **PS-SUP-05** Integraciones con Servicios Escolares y Tesorería mediante API REST o servicio equivalente documentado.
- [ ] **PS-SUP-06** Alcance móvil limitado a búsqueda de libros y chatbot.
- [ ] **PS-SUP-07** Capacidad constante de 37.5 h-equipo/semana durante las 10 semanas.

## 11. Precios y pago (pág. 13)

- [ ] **PS-PRC-01** Tarifa integrada de referencia: $250 MXN por hora-equipo (desarrollo, revisión de código, pruebas, gestión y documentación).
- [ ] **PS-PRC-02** Tabla: S0 75 h $18,750 (Sem 1-2); S1 75 h $18,750 (3-4); S2 112.5 h $28,125 (5-7); S3 75 h $18,750 (8-9); S4 37.5 h $9,375 (10). TOTAL 375 h, $93,750 MXN, 10 semanas, "antes de IVA y servicios de terceros".
- [ ] **PS-PRC-03** Pago: 40% del monto de cada sprint al iniciar la iteración; 60% restante tras Sprint Review y aceptación documentada del incremento.
- [ ] **PS-PRC-04** Cambios de alcance se estiman por separado antes de incorporarse a un sprint futuro.

## 12. Términos y condiciones (pág. 15)

| ID | Cláusula | Condición |
|---|---|---|
| PS-TYC-01 | Vigencia | 30 días naturales desde el 11 de septiembre de 2026 |
| PS-TYC-02 | Alcance contractual | Matriz de requerimientos del cliente e historias aceptadas en el Product Backlog |
| PS-TYC-03 | Forma de pago | 40% al inicio y 60% a la aceptación de cada sprint |
| PS-TYC-04 | Cambios de alcance | Análisis de impacto, horas y costo; solo con aprobación escrita |
| PS-TYC-05 | Aceptación | Documentada al cierre de cada Sprint Review; el silencio no es aceptación automática |
| PS-TYC-06 | Dependencias del cliente | Acceso, documentación y ambiente de prueba para Servicios Escolares, Tesorería y demás integraciones |
| PS-TYC-07 | Servicios de terceros | Costos de nube, WhatsApp, correo transaccional, dominios o licencias no incluidos salvo indicación expresa |
| PS-TYC-08 | Propiedad intelectual | Tras la liquidación total, el cliente recibe código fuente y documentación del alcance contratado; componentes de terceros conservan sus licencias |
| PS-TYC-09 | Confidencialidad y datos | Solo la información necesaria para desarrollo y pruebas, con control de acceso y sin divulgar a terceros no autorizados |
| PS-TYC-10 | Garantía | Corrección sin costo 30 días naturales posteriores a la aceptación final, para defectos reproducibles del alcance entregado |
| PS-TYC-11 | Soporte posterior | Mantenimiento evolutivo, nuevas funciones o soporte tras la garantía: cotización aparte |
| PS-TYC-12 | Cancelación | Se liquidan trabajos ejecutados y entregables completados hasta la fecha efectiva de terminación |

Firmas de conformidad (pág. 16): firmas del Product Owner (nombre en blanco) y Scrum Master (Elihu Orlando Osuna Maltos), manuscritas o electrónicas, "antes de la entrega definitiva para cumplir completamente con el criterio de conformidad". Campos de firma/fecha vacíos en el PDF.

## 13. Diferenciadores (pág. 14, compromisos de proceso)

- Propuesta basada en requerimientos reales (matriz de funciones, plataformas y usuarios).
- Trazabilidad de principio a fin: cada historia relacionada con requerimientos, pruebas y evidencia de aceptación.
- Entrega incremental: módulos funcionales al cierre de cada sprint; el cliente puede ajustar prioridades.
- Reglas de negocio explícitas: préstamos, vigencias y multas como validaciones verificables.
- Integraciones desde el diseño: Servicios Escolares, Tesorería, email y WhatsApp como dependencias de arquitectura.
- Calidad medible: objetivos de respuesta ≤ 3 s, pruebas, seguridad, respaldo y accesibilidad.
- Planeación sobre capacidad real (37.5 h-equipo/semana).
- Comunicación directa: roles claros y revisión con PO al final de cada sprint.

---

## 14. Ambigüedades, huecos e inconsistencias detectadas

1. **IDs/historias**: el documento no tiene IDs ni historias de usuario ni criterios de aceptación detallados por función; remite a una "matriz de requerimientos" externa que NO está en el PDF. Los criterios por función deben tomarse de esa matriz.
2. **Sección "Fuentes base de la propuesta"** (pág. 16 en el índice) no aparece; el PDF tiene 16 págs. y la pág. 16 son las firmas. El índice también marca "Firmas" y "Términos" en pág. 15 y "Fuentes" en 16.
3. **Nombre "Biblioteca Ducky"** no aparece en el PDF.
4. **RRHH** no se menciona; solo Servicios Escolares y Tesorería. No se aclara si "datos de alumnos/profesores" para profesores/colaboradores proviene de Servicios Escolares o de otra área.
5. **Reglas de negocio sin parámetros**: no hay días de préstamo por tipo de usuario, máximo de préstamos/renovaciones, tarifa/tope de multas, política de pérdidas, reglas de lista de espera. Dependen del taller de S0 y la matriz de decisión.
6. **Perfil "colaborador"**: aparece como perfil y en mantenimiento de libros (S1) pero no se define sus permisos ni si puede prestar.
7. **Reportes**: solo se menciona "reportes operativos" en el frontend web y "recibos"; no se enumeran reportes concretos (ni "devoluciones", "inventarios" salvo "inventarios parciales").
8. **Pérdidas**: se mencionan como dato de integración con Tesorería y en la sección 1, pero no figuran en ninguna función de sprint (S2 solo "multas" y "registro de pagos").
9. **Calendario de integraciones**: S2 usa servicios simulados; conexión real en S4. Esto choca con la meta "conciliación el mismo día mediante integración" para el entregable de S2 (hito "ciclo completo") y con las notificaciones WhatsApp (S2) sujetas a APIs contratadas.
10. **Servicios Escolares en S0**: los datos de alumnos/profesores se necesitan desde usuarios (S0) pero no se asigna integración hasta S2/S4; la migración del padrón no tiene sprint explícito.
11. **Accesibilidad**: aparece en el entregable de S1 (plan) pero no en la fila S1 de la tabla de alcance; WCAG 2.1 AA solo como "referencia" (no como cumplimiento exigido).
12. **"3 clics" y "≤ 3 s"** condicionados ("cuando aplique", "operaciones normales/incluidas"); sin definición de carga concurrente ni usuarios simultáneos.
13. **Disponibilidad 24/7** del chatbot "sujeta a" infraestructura y servicios externos; sin SLA numérico. Catálogo/estatus "continua en Web y App" (línea base) vs. app móvil solo búsqueda y chatbot: la consulta de "estatus propio" en Web/App se cubre solo vía chatbot.
14. **Estados del ejemplar y campos de la ficha bibliográfica** no enumerados; "clave" en búsqueda no se define (¿ISBN, clasificación, clave interna?).
15. **Escalamiento al bibliotecario**: sin canal, tiempos ni mecánica definidos. Motor del chatbot "híbrido" sin detalle (¿LLM?).
16. **Duración**: "5 sprints (Sprint 0 a Sprint 4)" en 10 semanas, con duraciones desiguales (2, 2, 3, 2, 1 semanas). Capacidad constante por semana, por lo que S2 pesa 112.5 h. Aritmética verificada: 375 h x $250 = $93,750; porcentajes de esfuerzo suman 100%.
17. **Pago 40/60 y "acta de aceptación"**: el cierre depende de firma del PO; el PO está sin nombre designado.
18. **Línea base**: las cifras son estimaciones a validar en S0 y que "se adoptarán como métricas de éxito" (podrían cambiar).
19. **Infra**: "nube institucional/comercial" sin elegir; backend "NestJS o Express" y "Redis cuando sea necesario" son decisiones abiertas.
20. **Restauración/backup**: sin RPO/RTO ni frecuencia especificados ("programados").
