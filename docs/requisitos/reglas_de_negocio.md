# LibriGest (Biblioteca Ducky) - Reglas de Negocio

Fuente: `Requerimientos Proyecto Final Ing Software - Reglas de Negocio.pdf` (2 páginas, 3 tablas/secciones: "Reglas y Políticas de Préstamo de Libros - Biblioteca Universidad Ducky", "Roles dentro de la operación de la Biblioteca", "Contexto y objetivo del proyecto").

## Notas generales sobre la fuente

- El documento NO usa IDs `RN-XX`; usa "Regla 1" ... "Regla 6". Aquí se mapean 1:1 como `RN-01` ... `RN-06` (RN-0N = Regla N). Los roles y el contexto se numeran como `RO-XX` y `CTX-XX` (IDs propios de este checklist, no del documento).
- El documento NO indica sprint (S1/S2/S3) para ninguna regla. Columna "Sprint": **no especificado**.
- El documento NO define mensajes de validación ni de error. Donde se propone un mensaje, se marca como **[SUGERIDO - no está en la fuente]**.
- La columna "Módulo/entidad" es inferencia de este checklist (no viene en la fuente).
- Nomenclatura: la fuente dice "Biblioteca Universidad Ducky" / "Universidad Ducky"; el proyecto se llama LibriGest / Biblioteca Ducky.

---

## 1. Reglas de préstamo (tabla "REGLA | NOMBRE | DESCRIPCIÓN")

### RN-01 - Regla 1: Autorización de préstamo de libros
- [ ] **Texto verbatim:** "El alumno se considera autorizado si no debe multas, no tiene más de dos ejemplares prestados actualmente y no tiene préstamos vencidos. El libro puede ser prestado si está disponible y su uso está catalogado como préstamo externo."
- **Sprint:** no especificado
- **Módulo/entidad (inferido):** Préstamos; Alumno, Ejemplar/Libro, Multa, Préstamo, Catálogo.
- **Condiciones atómicas (todas deben cumplirse; AND):**
  - [ ] RN-01.a Alumno sin multas pendientes (deuda de multas = 0).
  - [ ] RN-01.b Alumno con ejemplares prestados actualmente <= 2 (texto: "no tiene más de dos"). Es decir, con 2 ya prestados NO excede; ver ambigüedad A-01.
  - [ ] RN-01.c Alumno sin préstamos vencidos.
  - [ ] RN-01.d Libro/ejemplar disponible.
  - [ ] RN-01.e Uso del libro catalogado como "préstamo externo".
- **Parámetros:** máx. ejemplares simultáneos = 2 (alumno); tipo de uso requerido = "préstamo externo"; estado requerido del ejemplar = disponible.
- **Mensajes:** no definidos. [SUGERIDO] por condición incumplida: "El alumno tiene multas pendientes", "El alumno alcanzó el límite de ejemplares prestados", "El alumno tiene préstamos vencidos", "El ejemplar no está disponible", "El libro no es de préstamo externo".
- **Ambigüedades:**
  - A-01: "no tiene más de dos ejemplares prestados actualmente" - literalmente permite tener 2 y seguir autorizado, lo que llevaría a 3 con el nuevo préstamo. Lo más probable es que el límite real sea 2 en total (tener 2 bloquea el 3.º). **Confirmar con el cliente.** Evidencia a favor de la lectura "máximo 2 en total": Regla 2/6 usan "no exceda"; contradice la lectura literal. Decisión pendiente.
  - A-02: "no debe multas" - ¿cualquier monto > 0 bloquea? ¿multa pendiente = sin pagar? Se asume sí.
  - A-03: La regla habla solo de "alumno"; para profesores (Regla 6) no se dice si aplican las mismas condiciones (multas, vencidos, límite de ejemplares) ni cuántos ejemplares pueden tener.
  - A-04: Existen otros tipos de uso además de "préstamo externo" (p. ej. consulta interna/sala) pero no se enumeran; se necesita el catálogo de valores del atributo "uso".
  - A-05: "Disponible" no está definido (¿excluye reservado, en reparación, extraviado?). Ver CTX-02 (inconsistencia catálogo vs disponibilidad).

### RN-02 - Regla 2: Autorización de renovación de préstamo
- [ ] **Texto verbatim:** "El préstamo puede ser renovado según la fecha de vencimiento y siempre que el número de renovaciones no exceda de dos (alumnos)."
- **Sprint:** no especificado
- **Módulo/entidad (inferido):** Renovaciones; Préstamo (fecha_vencimiento, num_renovaciones), Alumno.
- **Condiciones atómicas:**
  - [ ] RN-02.a La renovación depende de la fecha de vencimiento del préstamo.
  - [ ] RN-02.b Número de renovaciones del préstamo <= 2 para alumnos (máx. 2 renovaciones).
- **Parámetros:** máx. renovaciones alumno = 2. (Profesores: 3, ver RN-06.)
- **Mensajes:** no definidos. [SUGERIDO] "El préstamo alcanzó el máximo de renovaciones permitidas (2)"; "El préstamo no puede renovarse por su fecha de vencimiento".
- **Ambigüedades:**
  - A-06: "según la fecha de vencimiento" no indica la condición exacta: ¿solo se puede renovar antes/en la fecha de vencimiento (no vencido)? ¿ventana de días previos? ¿se puede renovar uno ya vencido? **Confirmar.**
  - A-07: No se indica la duración de cada renovación (¿otros 5 días hábiles, igual que RN-05?) ni desde qué fecha se cuenta (¿desde el vencimiento original o desde hoy?).
  - A-08: No se indica si multas pendientes, préstamos vencidos o reservas de otro usuario bloquean la renovación.
  - A-09: "no exceda de dos" - se interpreta que se permiten 2 renovaciones y la 3.ª se rechaza.
  - A-10: Rol Alumno "solicita ... renovaciones" (ver RO-06); el rol Bibliotecario "recibe y renueva préstamos" (RO-04). Se asume renovación posible por ambos canales.

### RN-03 - Regla 3: Costo diario de multa
- [ ] **Texto verbatim:** "Por cada día de retraso en la devolución se cobrará al alumno o profesor una multa de $10 pesos."
- **Sprint:** no especificado
- **Módulo/entidad (inferido):** Multas; Multa, Préstamo (fecha_vencimiento, fecha_devolución), Alumno, Profesor.
- **Parámetros:** tarifa = $10 pesos por día de retraso; aplica a alumno Y profesor; moneda: pesos (se asume MXN).
- **Fórmula derivada:** multa = días_de_retraso x $10.
- **Mensajes:** no definidos. [SUGERIDO] "Devolución con N día(s) de retraso. Multa generada: $X pesos".
- **Ambigüedades:**
  - A-11: "día de retraso" no define si son días naturales o hábiles (Regla 5 usa hábiles para la vigencia, esta regla no dice nada). Sábados/domingos/festivos: ¿generan multa? **Confirmar.**
  - A-12: No hay tope máximo de multa ni de días.
  - A-13: Momento de generación (al devolver vs. acumulación diaria) no especificado. El rol Bibliotecario "genera multas" (RO-04), lo que sugiere generación manual/asistida al devolver.
  - A-14: Moneda "pesos" sin país/ISO; se asume MXN (RN-04 menciona dólares al "tipo de cambio actual").
  - A-15: No dice si se cobra por retraso en libros aún no devueltos (préstamo vencido sin devolver).

### RN-04 - Regla 4: Costo de reposición por pérdida
- [ ] **Texto verbatim:** "Si el alumno pierde el libro prestado, deberá pagar un valor de reposición equivalente al valor presente del libro (precio de la última compra en dólares, al tipo de cambio actual)."
- **Sprint:** no especificado
- **Módulo/entidad (inferido):** Multas/Pérdidas; Libro (precio_última_compra_usd), Préstamo, Tipo de cambio.
- **Parámetros:** monto = precio de la última compra del libro (USD) x tipo de cambio actual (USD -> pesos); aplica al "alumno".
- **Fórmula derivada:** reposición_MXN = precio_ultima_compra_USD x tipo_cambio_actual.
- **Mensajes:** no definidos. [SUGERIDO] "Libro extraviado. Valor de reposición: $X pesos (USD Y a tipo de cambio Z)".
- **Ambigüedades:**
  - A-16: Fuente del "tipo de cambio actual" (manual, DOF/Banxico, API) no especificada. Redondeo no especificado.
  - A-17: Solo menciona "alumno"; no dice si aplica también a profesores (Regla 6 no lo menciona).
  - A-18: No dice si se suman las multas por retraso acumuladas hasta el reporte de la pérdida.
  - A-19: Requiere conservar historial de compras con precio en USD (la entidad Libro/Compra debe guardar "precio de la última compra"). Caso de libros sin historial de compra no definido (ej. donados).
  - A-20: "Valor presente" se define entre paréntesis; se toma ese paréntesis como definición operativa.
  - A-21: El préstamo perdido/pago pendiente debería bloquear nuevos préstamos (RN-01.a: "no debe multas"); no se dice explícitamente que la reposición cuente como multa.

### RN-05 - Regla 5: Vigencia del préstamo para alumnos
- [ ] **Texto verbatim:** "Un préstamo tiene una vigencia de 5 días hábiles, sin contar sábados y domingos."
- **Sprint:** no especificado
- **Módulo/entidad (inferido):** Préstamos; Préstamo (fecha_préstamo, fecha_vencimiento), Calendario.
- **Parámetros:** duración = 5 días hábiles; se excluyen sábados y domingos.
- **Fórmula derivada:** fecha_vencimiento = fecha_préstamo + 5 días hábiles (L-V).
- **Mensajes:** no definidos.
- **Ambigüedades:**
  - A-22: Días festivos/inhábiles/vacaciones escolares no se mencionan (solo sábados y domingos). Se asume que festivos SÍ cuentan como hábiles salvo que se aclare.
  - A-23: Si el préstamo se realiza en sábado/domingo (si la biblioteca abre), no se define desde cuándo se cuenta.
  - A-24: El título dice "para alumnos" pero el texto dice "Un préstamo" (genérico); profesores tienen 10 días hábiles (RN-06).
  - A-25: Si el día 1 es el día del préstamo o el siguiente día hábil no se especifica.

### RN-06 - Regla 6: Reglas para maestros
- [ ] **Texto verbatim:** "Los profesores pueden solicitar préstamos. Tienen un máximo de 3 renovaciones, multa diaria de $10 pesos y una duración de préstamo de 10 días hábiles, sin contar sábados y domingos."
- **Sprint:** no especificado
- **Módulo/entidad (inferido):** Préstamos / Renovaciones / Multas; Profesor.
- **Parámetros (profesor):**
  - [ ] RN-06.a Puede solicitar préstamos.
  - [ ] RN-06.b Máx. renovaciones = 3.
  - [ ] RN-06.c Multa diaria = $10 pesos (igual que RN-03).
  - [ ] RN-06.d Duración del préstamo = 10 días hábiles, sin contar sábados y domingos.
- **Mensajes:** no definidos.
- **Ambigüedades:**
  - A-26: No se dice si el profesor está sujeto a RN-01 (sin multas, sin vencidos, límite de 2 ejemplares, disponible, préstamo externo). Se desconoce el límite de ejemplares simultáneos del profesor.
  - A-27: "Reglas para maestros" vs "profesores": mismo actor (rol "Profesor").
  - A-28: Misma ambigüedad que A-22 sobre festivos y A-07 sobre duración de cada renovación (¿10 días hábiles?).
  - A-29: RN-04 (reposición por pérdida) solo cita "alumno"; no hay regla explícita para pérdida por profesor.

---

## 2. Roles (tabla "ROL | REPORTA A | RESPONSABILIDADES")

### RO-01 - Administrador de Biblioteca
- [ ] **Reporta a:** Rectoría
- **Responsabilidades (verbatim):** "Responsable de la Biblioteca; busca dar mejor servicio a los Alumnos"

### RO-02 - Comprador de Libros
- [ ] **Reporta a:** Administrador de Biblioteca
- **Responsabilidades (verbatim):** "Solicita libros a las Editoriales con base en la lista de peticiones y el presupuesto mensual"
- Entidades implicadas (inferido): Lista de peticiones, Presupuesto mensual, Editorial, Pedido/Compra.

### RO-03 - Administrador del Catálogo
- [ ] **Reporta a:** Administrador de Biblioteca
- **Responsabilidades (verbatim):** "Actualiza el catálogo (fichas bibliográficas) y etiqueta los libros"
- Entidades implicadas (inferido): Catálogo, Ficha bibliográfica, Etiqueta de libro.

### RO-04 - Bibliotecario
- [ ] **Reporta a:** Administrador de Biblioteca
- **Responsabilidades (verbatim):** "Vigila la puerta; ayuda a localizar libros; coloca libros en libreros; controla préstamo de revistas; presta, recibe y renueva préstamos; registra pagos de multas; genera listas de alumnos suspendidos; genera multas"
- Desglose atómico:
  - [ ] RO-04.a Vigila la puerta.
  - [ ] RO-04.b Ayuda a localizar libros.
  - [ ] RO-04.c Coloca libros en libreros.
  - [ ] RO-04.d Controla préstamo de revistas.
  - [ ] RO-04.e Presta, recibe y renueva préstamos.
  - [ ] RO-04.f Registra pagos de multas.
  - [ ] RO-04.g Genera listas de alumnos suspendidos.
  - [ ] RO-04.h Genera multas.

### RO-05 - Profesor
- [ ] **Reporta a:** Dirección Académica
- **Responsabilidades (verbatim):** "Consulta el catálogo y solicita préstamos de libros bajo las condiciones de la Regla 6"
- Vincula con RN-06.

### RO-06 - Alumno
- [ ] **Reporta a:** Servicios Escolares
- **Responsabilidades (verbatim):** "Consulta el catálogo, solicita préstamos, renovaciones y realiza el pago de multas en Tesorería"
- Desglose: consulta catálogo; solicita préstamos; solicita renovaciones; paga multas en Tesorería.

### Ambigüedades de roles
- A-30: Alumno "realiza el pago de multas en Tesorería" pero Bibliotecario "registra pagos de multas": no se define el flujo (¿Tesorería emite comprobante y el Bibliotecario lo registra en el sistema?). Tesorería no aparece como rol del sistema.
- A-31: "Genera listas de alumnos suspendidos" - NO hay ninguna regla que defina cuándo/por qué un alumno queda suspendido ni cuándo se levanta (¿multas impagas? ¿préstamos vencidos?), ni su efecto. **Regla faltante.**
- A-32: "Controla préstamo de revistas" - las revistas no tienen regla de préstamo (vigencia, multa, límite); las Reglas 1-6 son solo de libros. Se desconoce si están en alcance.
- A-33: "Vigila la puerta" y "coloca libros en libreros" son tareas físicas, probablemente fuera del alcance del sistema (aunque la ubicación en libreros puede ser dato del catálogo).
- A-34: Profesor "solicita préstamos" pero no se menciona que solicite renovaciones ni pague multas (aunque RN-03/RN-06 le cobran multa y le dan 3 renovaciones).
- A-35: Rectoría, Dirección Académica, Servicios Escolares, Editoriales y Tesorería aparecen como entidades organizacionales/externas; no se dan roles de sistema para ellas.
- A-36: No se definen roles de acceso/autenticación (permisos) explícitos; se infieren de las responsabilidades.

---

## 3. Contexto y objetivo del proyecto (sección narrativa)

- [ ] **CTX-00 Texto verbatim:** "Actualmente el área de préstamo de libros de la Biblioteca de la Universidad Ducky opera de forma totalmente manual. Esto genera: (1) inconsistencia entre el catálogo y la disponibilidad real de los libros, (2) tiempos de atención muy largos para préstamo y devolución, y (3) dificultad para elaborar inventarios al no contarse con listas parciales de existencia. La Universidad busca automatizar estos procesos como parte de su interés en certificarse bajo la norma internacional de calidad ISO 9001:2015, lo que requiere procedimientos uniformes y un excelente servicio a los alumnos."
- [ ] **CTX-01** Automatizar el préstamo y la devolución de libros (hoy 100 % manual).
- [ ] **CTX-02** Problema (1): eliminar inconsistencia entre catálogo y disponibilidad real. Implica que la disponibilidad se actualice con cada préstamo/devolución (apoya RN-01.d).
- [ ] **CTX-03** Problema (2): reducir tiempos de atención de préstamo y devolución. Sin métrica numérica en la fuente (**no hay tiempo objetivo**).
- [ ] **CTX-04** Problema (3): poder elaborar inventarios con listas parciales de existencia.
- [ ] **CTX-05** Objetivo: certificación ISO 9001:2015 -> procedimientos uniformes y excelente servicio a los alumnos.

---

## 4. Resumen de parámetros numéricos

| Parámetro | Alumno | Profesor | Regla |
|---|---|---|---|
| Ejemplares prestados simultáneos | máx. 2 (ver A-01) | no especificado | RN-01 |
| Vigencia del préstamo | 5 días hábiles (sin sáb/dom) | 10 días hábiles (sin sáb/dom) | RN-05 / RN-06 |
| Renovaciones máximas | 2 | 3 | RN-02 / RN-06 |
| Multa por día de retraso | $10 pesos | $10 pesos | RN-03 / RN-06 |
| Reposición por pérdida | precio última compra (USD) x tipo de cambio actual | no especificado | RN-04 |
| Condición del libro | disponible + "préstamo externo" | no especificado | RN-01 |

## 5. Lista consolidada de ambigüedades a confirmar (prioridad sugerida)

1. A-01 Límite de ejemplares: ¿máximo 2 en total o 3?
2. A-06/A-07/A-08 Condiciones y duración de la renovación.
3. A-11/A-12 Multa: días naturales vs. hábiles, tope.
4. A-26 Reglas de elegibilidad de profesores.
5. A-31 Regla de suspensión de alumnos (inexistente en las reglas).
6. A-32 Reglas de préstamo de revistas (inexistentes).
7. A-16/A-17/A-19 Fuente del tipo de cambio, aplicación a profesores, libros sin precio.
8. A-22 Festivos como días hábiles.
9. A-30 Flujo de pago de multas Tesorería vs. Bibliotecario.
10. Sprint (S1/S2/S3): la fuente no asigna; deberá decidirse en la planeación.
