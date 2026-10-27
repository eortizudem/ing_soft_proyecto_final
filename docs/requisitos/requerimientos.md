# LibriGest (Biblioteca Ducky) - Checklist de Requerimientos

Fuente: `Requerimientos Proyecto Final Ing Software - Requerimientos.pdf` (2 paginas, una sola tabla).

## 0. Notas sobre la fuente

- El PDF es **solo una matriz** (Sprint / Funcion / Requerimientos funcionales / Requerimientos no funcionales / Plataforma APP-WEB / Usuarios). **No contiene** IDs propios (RF/RNF/HU), historias de usuario, criterios de aceptacion, casos de uso, descripciones de pantallas, reportes formales ni prioridades explicitas.
- Los IDs de este documento (`RF-xx`, `RNF-xx`) **fueron asignados aqui** para trazabilidad; no existen en el original.
- Prioridad: no declarada. Se deja `No declarada` (el sprint es la unica senal de orden).
- El PDF numera sprints **0, 1, 2, 3** (no S1-S3). Se conserva "Sprint 0" como en el original.
- Las "Reglas 1-6" se citan en el texto pero **no se definen en una seccion aparte**; solo se conoce su contenido por las menciones (ver seccion 6).
- Los requerimientos no funcionales del original estan en celdas combinadas: aplican a todas las funciones del bloque (Mantenimiento + Busqueda comparten NFR; Prestamos + Devolucion comparten NFR). Se replican con IDs separados por funcion donde asi aplica.

## 1. Matriz de modulos (plataforma y usuarios)

Leyenda: ok = habilitado, --- = no habilitado.

| Sprint | Funcion | APP | WEB | Administrador | Bibliotecario | Profesor | Alumno | Colaborador |
|---|---|---|---|---|---|---|---|---|
| 0 | GESTION DE USUARIO | --- | ok | ok | --- | --- | --- | --- |
| 1 | MANTENIMIENTO DE LIBROS | --- | ok | ok | ok | --- | --- | ok |
| 1 | BUSQUEDA DE LIBROS | ok | ok | ok | ok | ok | ok | ok |
| 2 | PRESTAMOS DE LIBROS | --- | ok | ok | ok | --- | --- | --- |
| 2 | DEVOLUCION DE LIBROS | --- | ok | ok | ok | --- | --- | --- |
| 3 | CHATBOT | ok | ok | ok | ok | ok | ok | ok |

## 2. Roles / actores mencionados

- Columnas de usuarios: Administrador, Bibliotecario, Profesor, Alumno, Colaborador.
- Roles nombrados en los requerimientos funcionales: Administrador de Biblioteca, Comprador de Libros, Administrador del Catalogo, Bibliotecario, Profesor, Alumno.
- Entidades externas: Servicios Escolares, Tesoreria, Editoriales.

## 3. Requerimientos funcionales

### Modulo: GESTION DE USUARIO (Sprint 0) - Plataforma: WEB - Usuarios: Administrador

- [ ] **RF-01** - Creacion y administracion de perfiles: Administrador de Biblioteca, Comprador de Libros, Administrador del Catalogo, Bibliotecario, Profesor y Alumno.
  - Prioridad: No declarada | Sprint: 0 | Actor: Administrador | Modulo: Gestion de usuario
  - Criterios de aceptacion: no declarados.
- [ ] **RF-02** - Asignacion de roles y permisos segun el organigrama de la Biblioteca.
  - Prioridad: No declarada | Sprint: 0 | Actor: Administrador | Modulo: Gestion de usuario
  - Criterios de aceptacion: no declarados.
- [ ] **RF-03** - Alta, baja y modificacion de datos de Alumnos y Profesores (sincronizado con Servicios Escolares).
  - Prioridad: No declarada | Sprint: 0 | Actor: Administrador | Modulo: Gestion de usuario
  - Criterios de aceptacion: no declarados.
- [ ] **RF-04** - Consulta de historial de prestamos, renovaciones, multas y adeudos por usuario.
  - Prioridad: No declarada | Sprint: 0 | Actor: Administrador | Modulo: Gestion de usuario
  - Criterios de aceptacion: no declarados.

### Modulo: MANTENIMIENTO DE LIBROS (Sprint 1) - Plataforma: WEB - Usuarios: Administrador, Bibliotecario, Colaborador

- [ ] **RF-05** - Registro de solicitud de compra de libros (lista de peticiones) con base en presupuesto mensual asignado (rol Comprador de Libros).
  - Prioridad: No declarada | Sprint: 1 | Actor: Comprador de Libros | Modulo: Mantenimiento de libros
- [ ] **RF-06** - Registro de recepcion de libros y de la factura entregada por las Editoriales, con enlace a Tesoreria.
  - Prioridad: No declarada | Sprint: 1 | Actor: no especificado | Modulo: Mantenimiento de libros
- [ ] **RF-07** - Generacion de Ficha Bibliografica y etiquetado de libros nuevos (rol Administrador del Catalogo).
  - Prioridad: No declarada | Sprint: 1 | Actor: Administrador del Catalogo | Modulo: Mantenimiento de libros
- [ ] **RF-08** - Alta de libros en el catalogo (autor, tema, titulo, clave, editorial y existencias).
  - Prioridad: No declarada | Sprint: 1 | Actor: no especificado | Modulo: Mantenimiento de libros
- [ ] **RF-09** - Asignacion de ubicacion en librero para su colocacion (rol Bibliotecario).
  - Prioridad: No declarada | Sprint: 1 | Actor: Bibliotecario | Modulo: Mantenimiento de libros
- [ ] **RF-10** - Marcado de libros como reservados o de consulta externa.
  - Prioridad: No declarada | Sprint: 1 | Actor: no especificado | Modulo: Mantenimiento de libros
- [ ] **RF-11** - Baja/actualizacion de fichas de libros perdidos, robados, danados u obsoletos.
  - Prioridad: No declarada | Sprint: 1 | Actor: no especificado | Modulo: Mantenimiento de libros
- [ ] **RF-12** - Listado de Libros por diversos filtros (autor, tema, titulo, clave, editorial, disponibilidad).
  - Prioridad: No declarada | Sprint: 1 | Actor: no especificado | Modulo: Mantenimiento de libros

(Criterios de aceptacion de RF-05 a RF-12: no declarados.)

### Modulo: BUSQUEDA DE LIBROS (Sprint 1) - Plataforma: APP y WEB - Usuarios: todos (Administrador, Bibliotecario, Profesor, Alumno, Colaborador)

- [ ] **RF-13** - Consulta del catalogo por autor, tema, titulo, clave o editorial.
  - Prioridad: No declarada | Sprint: 1 | Actor: todos | Modulo: Busqueda de libros
- [ ] **RF-14** - Consulta de existencia y ubicacion fisica del Libro dentro de la Biblioteca.
  - Prioridad: No declarada | Sprint: 1 | Actor: todos | Modulo: Busqueda de libros
- [ ] **RF-15** - Consulta de disponibilidad en tiempo real (prestamo externo o consulta/uso interno).
  - Prioridad: No declarada | Sprint: 1 | Actor: todos | Modulo: Busqueda de libros
- [ ] **RF-16** - Generacion de listas parciales de existencia, para apoyar la elaboracion de inventarios.
  - Prioridad: No declarada | Sprint: 1 | Actor: todos (segun matriz; ver ambiguedad A-6) | Modulo: Busqueda de libros

(Criterios de aceptacion de RF-13 a RF-16: no declarados.)

### Modulo: PRESTAMOS DE LIBROS (Sprint 2) - Plataforma: WEB - Usuarios: Administrador, Bibliotecario

- [ ] **RF-17** - Validacion de condicion del Solicitante (Regla 1: sin multas, max. 2 ejemplares prestados, sin prestamos vencidos).
  - Prioridad: No declarada | Sprint: 2 | Actor: Administrador / Bibliotecario | Modulo: Prestamos
- [ ] **RF-18** - Validacion de condicion del Libro (disponible y catalogado como prestamo externo).
  - Prioridad: No declarada | Sprint: 2 | Actor: Administrador / Bibliotecario | Modulo: Prestamos
- [ ] **RF-19** - Registro de Prestamo y generacion de Recibo de Prestamo (email, whatsapp, impresion).
  - Prioridad: No declarada | Sprint: 2 | Actor: Administrador / Bibliotecario | Modulo: Prestamos
- [ ] **RF-20** - Control de vigencia del prestamo: 5 dias habiles para Alumnos (Regla 5) y 10 dias habiles para Profesores (Regla 6), sin contar sabados ni domingos.
  - Prioridad: No declarada | Sprint: 2 | Actor: Administrador / Bibliotecario | Modulo: Prestamos
- [ ] **RF-21** - Renovacion de Prestamo: maximo 2 renovaciones para Alumnos (Regla 2) y maximo 3 para Profesores (Regla 6), autorizada por el Administrador.
  - Prioridad: No declarada | Sprint: 2 | Actor: Administrador (autoriza) | Modulo: Prestamos
- [ ] **RF-22** - Gestion de Lista de Espera para libros no disponibles.
  - Prioridad: No declarada | Sprint: 2 | Actor: Administrador / Bibliotecario | Modulo: Prestamos

(Criterios de aceptacion de RF-17 a RF-22: no declarados.)

### Modulo: DEVOLUCION DE LIBROS (Sprint 2) - Plataforma: WEB - Usuarios: Administrador, Bibliotecario

- [ ] **RF-23** - Registro de Devolucion de Libro y actualizacion automatica de disponibilidad en el catalogo.
  - Prioridad: No declarada | Sprint: 2 | Actor: Administrador / Bibliotecario | Modulo: Devolucion
- [ ] **RF-24** - Validacion de la fecha de vencimiento contra la fecha actual.
  - Prioridad: No declarada | Sprint: 2 | Actor: Administrador / Bibliotecario | Modulo: Devolucion
- [ ] **RF-25** - Generacion de Multas por: entrega extemporanea (Regla 3: $10 pesos por dia de retraso), dano y perdida de Libro (Regla 4: valor de reposicion = precio de ultima compra en USD al tipo de cambio actual).
  - Prioridad: No declarada | Sprint: 2 | Actor: Administrador / Bibliotecario | Modulo: Devolucion
- [ ] **RF-26** - Aviso automatico a Servicios Escolares y Tesoreria en caso de perdida de libro.
  - Prioridad: No declarada | Sprint: 2 | Actor: Sistema (destinatarios: Servicios Escolares, Tesoreria) | Modulo: Devolucion
- [ ] **RF-27** - Registro del pago de multa reportado por el Alumno/Profesor tras pagar en Tesoreria.
  - Prioridad: No declarada | Sprint: 2 | Actor: Administrador / Bibliotecario | Modulo: Devolucion
- [ ] **RF-28** - Generacion de lista de Alumnos deudores de libros y multas en epoca de examenes, con aviso a Servicios Escolares para su suspension.
  - Prioridad: No declarada | Sprint: 2 | Actor: Administrador / Bibliotecario | Modulo: Devolucion

(Criterios de aceptacion de RF-23 a RF-28: no declarados.)

### Modulo: CHATBOT (Sprint 3) - Plataforma: APP y WEB - Usuarios: todos

- [ ] **RF-29** - Respuesta a consultas frecuentes: horarios, politicas de prestamo, ubicacion y disponibilidad de libros.
  - Prioridad: No declarada | Sprint: 3 | Actor: todos | Modulo: Chatbot
- [ ] **RF-30** - Apoyo en la busqueda de libros por autor, tema, titulo, clave o editorial.
  - Prioridad: No declarada | Sprint: 3 | Actor: todos | Modulo: Chatbot
- [ ] **RF-31** - Consulta del estatus de prestamos, renovaciones y multas del propio usuario.
  - Prioridad: No declarada | Sprint: 3 | Actor: todos (usuario autenticado) | Modulo: Chatbot
- [ ] **RF-32** - Explicacion de reglas de negocio (vigencia de prestamo, numero de renovaciones, costo de multas).
  - Prioridad: No declarada | Sprint: 3 | Actor: todos | Modulo: Chatbot
- [ ] **RF-33** - Escalamiento a Bibliotecario cuando el Chatbot no puede resolver la consulta.
  - Prioridad: No declarada | Sprint: 3 | Actor: Chatbot -> Bibliotecario | Modulo: Chatbot

(Criterios de aceptacion de RF-29 a RF-33: no declarados.)

## 4. Requerimientos no funcionales

### Gestion de usuario (Sprint 0)
- [ ] **RNF-01** - Autenticacion por usuario y contrasena. (Seguridad) | Sprint 0 | Modulo: Gestion de usuario
- [ ] **RNF-02** - Backup y Restore de la informacion. (Disponibilidad / recuperacion) | Sprint 0 | Modulo: Gestion de usuario
- [ ] **RNF-03** - Tiempo de Respuesta no mayor a 3 segundos. (Desempeno) | Sprint 0 | Modulo: Gestion de usuario
- [ ] **RNF-04** - Uso de Microservicios o APIs para comunicarse con entidades externas. (Arquitectura / integracion) | Sprint 0 | Modulo: Gestion de usuario

### Mantenimiento de libros y Busqueda de libros (Sprint 1; celda combinada, aplica a ambos)
- [ ] **RNF-05** - Tiempo de Respuesta no mayor a 3 segundos. (Desempeno) | Sprint 1 | Modulos: Mantenimiento de libros, Busqueda de libros
- [ ] **RNF-06** - Interfaz: Multiplataforma, Amigable (discapacidad visual). (Usabilidad / accesibilidad) | Sprint 1 | Modulos: Mantenimiento de libros, Busqueda de libros
- [ ] **RNF-07** - Navegacion con 3 clicks como maximo para procesar. (Usabilidad) | Sprint 1 | Modulos: Mantenimiento de libros, Busqueda de libros
- [ ] **RNF-08** - Actualizacion del catalogo en tiempo real, para eliminar la inconsistencia actual entre el catalogo y la disponibilidad real de los libros. (Consistencia de datos) | Sprint 1 | Modulos: Mantenimiento de libros, Busqueda de libros

### Prestamos y Devolucion de libros (Sprint 2; celda combinada, aplica a ambos)
- [ ] **RNF-09** - Validacion automatica de reglas de negocio (Reglas 1, 2, 5 y 6). | Sprint 2 | Modulos: Prestamos, Devolucion
- [ ] **RNF-10** - Notificacion al usuario del estatus del prestamo (email/whatsapp). | Sprint 2 | Modulos: Prestamos, Devolucion
- [ ] **RNF-11** - Tiempo de Respuesta no mayor a 3 segundos. (Desempeno) | Sprint 2 | Modulos: Prestamos, Devolucion

### Chatbot (Sprint 3)
- [ ] **RNF-12** - Disponibilidad 24/7. | Sprint 3 | Modulo: Chatbot
- [ ] **RNF-13** - Tiempo de Respuesta no mayor a 3 segundos. (Desempeno) | Sprint 3 | Modulo: Chatbot
- [ ] **RNF-14** - Integracion multiplataforma (Web y App). | Sprint 3 | Modulo: Chatbot

## 5. Historias de usuario, casos de uso, pantallas, reportes

- Historias de usuario: **no existen** en el PDF.
- Casos de uso: **no existen** en el PDF.
- Pantallas/UI: no hay descripciones; solo restricciones de interfaz (RNF-06, RNF-07).
- Reportes/documentos implicitos en los requerimientos funcionales (no definidos en formato): Ficha Bibliografica (RF-07), Recibo de Prestamo (RF-19), listas parciales de existencia (RF-16), lista de deudores en epoca de examenes (RF-28), historial por usuario (RF-04), lista de peticiones de compra (RF-05).
- Restricciones de seguridad: solo RNF-01 (usuario/contrasena) y roles/permisos (RF-02). Backup/Restore: RNF-02.

## 6. Reglas de negocio citadas (reconstruidas de las menciones)

- **Regla 1** (RF-17): Solicitante sin multas, max. 2 ejemplares prestados, sin prestamos vencidos.
- **Regla 2** (RF-21): Max. 2 renovaciones para Alumnos.
- **Regla 3** (RF-25): Multa por entrega extemporanea = $10 pesos por dia de retraso.
- **Regla 4** (RF-25): Dano o perdida: valor de reposicion = precio de ultima compra en USD al tipo de cambio actual.
- **Regla 5** (RF-20): Prestamo de Alumnos = 5 dias habiles.
- **Regla 6** (RF-20, RF-21): Prestamo de Profesores = 10 dias habiles; max. 3 renovaciones.
- Otras reglas: dias habiles no cuentan sabados ni domingos; renovacion autorizada por el Administrador.

## 7. Ambiguedades y contradicciones detectadas

- **A-1** Sin IDs, prioridades, criterios de aceptacion, HU ni casos de uso en la fuente; deben acordarse con el cliente/profesor o redactarse en fases posteriores.
- **A-2** Roles inconsistentes: los funcionales listan 6 perfiles (Administrador de Biblioteca, Comprador de Libros, Administrador del Catalogo, Bibliotecario, Profesor, Alumno) pero la matriz tiene 5 columnas (Administrador, Bibliotecario, Profesor, Alumno, **Colaborador**). "Colaborador" no se define; Comprador de Libros y Administrador del Catalogo no tienen columna propia (posiblemente son "Colaborador" o "Administrador").
- **A-3** Mantenimiento de libros: columna APP = `---` pero RNF-06 pide "Interfaz: Multiplataforma". Contradiccion aparente (RNF-06 comparte celda con Busqueda, que si es APP+WEB).
- **A-4** Profesor y Alumno no tienen acceso a Prestamos/Devolucion (solo Administrador y Bibliotecario), pero RNF-10 pide notificarles y RF-27 habla de pago "reportado por el Alumno/Profesor". Tampoco pueden consultar su historial (RF-04 solo Administrador), pero el Chatbot (RF-31) les muestra su estatus.
- **A-5** RF-21: renovacion "autorizada por el Administrador" pero el Bibliotecario tiene acceso al modulo; no se aclara quien registra y quien autoriza. Tampoco queda claro si las renovaciones tienen limite compartido por libro o por prestamo.
- **A-6** RF-16 (listas parciales de existencia "para inventarios") esta habilitado para Profesor/Alumno segun la matriz, aunque parece funcion interna de personal.
- **A-7** Regla 1 "max. 2 ejemplares prestados": no se aclara si aplica igual a Profesores (el limite de Profesores no se menciona).
- **A-8** Reglas 1-6 no estan definidas formalmente; Regla 6 se cita para dos cosas distintas (vigencia 10 dias y 3 renovaciones). RNF-09 valida solo reglas 1, 2, 5 y 6 (las multas, Reglas 3 y 4, no se mencionan como validacion automatica).
- **A-9** Multa $10 pesos/dia: no se define moneda explicita (pesos mexicanos?), si hay tope, ni si cuenta dias habiles o naturales. Regla 4 mezcla precio en USD con tipo de cambio actual: no se define la fuente del tipo de cambio.
- **A-10** RF-19: "email, whatsapp, impresion" - no se aclara si son canales simultaneos u opcionales. RNF-10 solo menciona email/whatsapp.
- **A-11** RNF-02 (Backup/Restore): sin RPO/RTO ni frecuencia. RNF-12 (24/7): sin porcentaje de disponibilidad. RNF-03/05/11/13 (3 s): no se define sobre que carga, percentil ni condiciones.
- **A-12** RNF-06 "Amigable (discapacidad visual)": no se cita norma (p. ej. WCAG) ni nivel.
- **A-13** RNF-07 "3 clicks como maximo para procesar": no se define que proceso(s) cuentan.
- **A-14** RNF-04: "Microservicios o APIs" (alternativa abierta); entidades externas identificables: Servicios Escolares, Tesoreria, Editoriales, canales email/whatsapp.
- **A-15** RF-28 "epoca de examenes": no se define el calendario ni quien dispara la generacion de la lista. RF-26 se limita a "perdida" (no a dano).
- **A-16** Gestion de usuario (Sprint 0) es WEB y solo Administrador, pero la matriz no incluye autenticacion en otros modulos explicitamente (RNF-01 aplica globalmente por inferencia).
- **A-17** RF-10 "reservados o de consulta externa": el estado "consulta externa" parece ser un tipo de catalogacion (vs. "consulta/uso interno" en RF-15) y se conecta con RF-18 "catalogado como prestamo externo"; terminologia inconsistente (consulta externa vs. prestamo externo).
