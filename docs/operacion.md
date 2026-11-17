# LibriGest - Guía de operación

Cubre RNF-02 (respaldo/restauración, D-14), RNF-03/05/11/13 (medición de rendimiento, D-15), RNF-12 (disponibilidad),
RNF-06 (checklist de accesibilidad, D-16), RNF-07 (procesos de 3 clics, D-17) y RNF-10 (lista de avisos, D-11).
Todos los scripts usan solo la biblioteca estándar de Python 3 y se ejecutan desde la raíz del proyecto.

## 1. Disponibilidad (RNF-12)

- `docker-compose.yml`: `restart: unless-stopped` en `db`, `web` y `ollama`; el servicio vuelve solo tras un fallo del proceso o
  un reinicio del servidor (no si se detuvo a mano con `docker compose stop`).
- Healthchecks: `db` (`pg_isready`), `ollama` (`ollama list`) y `web` (`GET /api/health`, cada 10 s, 5 reintentos). El mismo chequeo está en el
  `Dockerfile` (`HEALTHCHECK`). Estado: `docker compose ps` (columna STATUS: `healthy`).
- Variables opcionales (ver `.env.example`; se pasan al servicio `web`): `TIPO_CAMBIO_USD_MXN` (18.00),
  `PRESUPUESTO_MENSUAL_USD` (5000), `ESPERA_DIAS_RESERVA` (2), `WEB_CONCURRENCY` (4 procesos de gunicorn),
  `DEMO_MOSTRAR_TOKEN` (true) y `HTTPS` (false), ver sección 7. Tras cambiarlas: `docker compose up -d web`.

## 2. Respaldo y restauración (RNF-02, D-14)

Objetivos: **RPO 24 h** (se programa un respaldo diario; como máximo se pierde un día de datos) y
**RTO 30 min** (restaurar el último respaldo y levantar el servicio toma minutos para el tamaño del proyecto).

### Respaldar

```
python3 scripts/respaldo.py                 # -> backups/librigest_YYYYmmdd_HHMMSS.dump (+ .conteos)
python3 scripts/respaldo.py --salida /ruta --db otra_bd
```

Ejecuta `docker compose exec -T db pg_dump -Fc` y guarda el volcado en formato personalizado. Junto al `.dump` escribe un
`.conteos` con las filas por tabla en ese momento (lo usa la verificación). `backups/` está en `.dockerignore` y debe ir
en `.gitignore` (contiene datos personales; no se versiona). Copiar los respaldos fuera de la máquina (disco externo/nube).

Programación diaria (RPO 24 h):

- Linux/macOS (`crontab -e`): `0 2 * * * cd /ruta/proyecto && python3 scripts/respaldo.py >> backups/respaldo.log 2>&1`
- Windows: Programador de tareas, acción `python scripts\respaldo.py`, iniciar en la carpeta del proyecto, diaria 02:00.

### Verificar un respaldo (la "prueba documentada")

```
python3 scripts/restaurar.py backups/librigest_20261027_101008.dump --verificar
```

Crea una BD temporal `verif_<fecha>`, restaura ahí, compara las filas por tabla con el `.conteos` del respaldo (o con la BD
actual si no existe), elimina la BD temporal y devuelve código 0 solo si todo coincide. **No toca la BD de producción.**
Ejemplo de salida real (extracto):

```
Verificacion contra respaldo (librigest_h_20261027_101008.conteos): 21 tablas restauradas en BD temporal (eliminada).
   rol                      esperado=8      restaurado=8
   rol_permiso              esperado=120    restaurado=120
   usuario                  esperado=9      restaurado=9
VERIFICACION CORRECTA: los conteos coinciden.
```

Se recomienda verificar al menos el respaldo más reciente cada semana.

### Restaurar (recuperación ante desastre)

```
python3 scripts/restaurar.py backups/librigest_20261027_101008.dump          # pide confirmación [s/N]
python3 scripts/restaurar.py backups/librigest_20261027_101008.dump -y       # sin preguntar
python3 scripts/restaurar.py <archivo> --db librigest_prueba                 # restaurar en otra BD
```

Usa `pg_restore --clean --if-exists --no-owner`: **reemplaza** los datos de la BD destino (por defecto la de `.env`,
`POSTGRES_DB`). Procedimiento ante pérdida de datos: (1) `docker compose stop web`; (2) restaurar el último respaldo;
(3) `docker compose start web`; (4) comprobar `GET /api/health` y entrar con una cuenta de administrador. Si el volumen
`pgdata` se perdió, `docker compose up -d db` recrea la BD vacía con el esquema de `db/` y después se restaura.

## 3. Medición de rendimiento (RNF-03/05/11/13, D-15)

```
python3 scripts/medir_rendimiento.py [--url http://localhost:8000] [-n 20] [-c 20] [--limite 3.0] [--escritura [--db librigest]]
```

Inicia sesión (por defecto `ADM001`), llama a cada endpoint crítico (libros y búsqueda, usuarios, préstamos, adeudos,
espera, compras, notificaciones, `asistente/mensajes`, reportes) `-n` veces **una a la vez** y luego `-c` solicitudes
**concurrentes**, e imprime p50 / p95 / máx. Sale con código 1 si el p95 de algún endpoint supera 3 s o hay errores
HTTP (un tiempo agotado cuenta como HTTP 0); los módulos no instalados (404/403) se omiten con aviso.
`--escritura` agrega los flujos de escritura (crear préstamo, renovar, devolver y registrar pago, `-n` iteraciones en
serie): crea su propio usuario y libro `ZPERF01` por la API y al terminar los borra, con sus préstamos, adeudos y
bitácora, con SQL en la BD `--db` (requiere `docker compose`). `--url` permite apuntar a cualquier servidor.

### Dataset de volumen (D-15) — procedimiento

```
python3 scripts/cargar_datos_volumen.py                 # crea/recrea librigest_volumen (db/*.sql + semilla) y la llena
docker compose run --rm -d --no-deps -p 8199:8000 \
  -e DATABASE_URL=postgresql://librigest:librigest@db:5432/librigest_volumen --name lg_vol web
python3 scripts/medir_rendimiento.py --url http://localhost:8199 -n 20 -c 20 --escritura --db librigest_volumen
docker rm -f lg_vol && python3 scripts/cargar_datos_volumen.py --eliminar     # limpieza
```

El cargador usa SQL (`generate_series`) y deja 5 000 usuarios, 10 002 ejemplares (2 503 libros de 4 copias), 20 664
préstamos (≈15 % abiertos, el resto devueltos en 2 años, 7 082 adeudos con 10 % pendientes, 600 renovaciones), lista de
espera de 250 libros con todas sus copias prestadas, 3 000 conversaciones, 502 solicitudes de compra y 20 000 filas de
bitácora; verifica los mínimos y que no haya discrepancias de inventario. **Nunca toca la BD principal**: `--db librigest`
exige confirmación escrita y solo agrega filas.

### Resultados (2026-10-27, Docker Desktop local, 4 procesos gunicorn, `-n 20 -c 20`)

| Escenario | p95 máx. una a la vez | p95 máx. con 20 concurrentes | Escrituras (p95 máx.) |
|---|---|---|---|
| Demo (9 usuarios, 18 ejemplares) | 0.046 s (`asistente/mensajes`) | 0.226 s (`asistente/mensajes`) | 0.066 s |
| Volumen D-15 (5 000 / 10 002 / 20 664) | 0.281 s (`reportes/prestamos`) | 2.430 s (`reportes/prestamos`) | 0.064 s |

Volumen, por endpoint (p50 / p95 / máx. en segundos):

| Endpoint | Una a la vez | 20 concurrentes |
|---|---|---|
| libros | 0.161 / 0.175 / 0.178 | 0.698 / 1.224 / 1.265 |
| libros?q= | 0.176 / 0.200 / 0.203 | 0.752 / 1.318 / 1.350 |
| usuarios | 0.039 / 0.043 / 0.045 | 0.173 / 0.276 / 0.281 |
| prestamos | 0.048 / 0.053 / 0.057 | 0.245 / 0.425 / 0.430 |
| adeudos | 0.039 / 0.044 / 0.048 | 0.212 / 0.374 / 0.381 |
| espera | 0.058 / 0.061 / 0.062 | 0.303 / 0.533 / 0.564 |
| compras | 0.171 / 0.186 / 0.195 | 0.598 / 1.037 / 1.059 |
| asistente/mensajes | 0.029 / 0.033 / 0.035 | 0.139 / 0.223 / 0.226 |
| reportes/con_adeudos | 0.192 / 0.201 / 0.210 | 0.881 / 1.585 / 1.601 |
| reportes/prestamos (20 664 filas) | 0.259 / 0.281 / 0.281 | 1.365 / 2.430 / 2.480 |
| reportes/indicadores | 0.164 / 0.194 / 0.194 | 0.688 / 1.132 / 1.146 |
| Escritura: crear préstamo / renovar / devolver / pagar | 0.056 / 0.036 / 0.039 / 0.037 (p50) | p95: 0.064 / 0.052 / 0.042 / 0.042 |

Los demás endpoints (notificaciones, reportes de catálogo, existencia, vencidos, errores, consultas para el bibliotecario) quedaron por
debajo de 0.7 s en ambos modos. **Límite de 3 s cumplido en todos**, pero `reportes/prestamos` sin filtro de fechas (un
reporte de 20 664 filas) con 20 usuarios simultáneos queda en 2.4 s: usar `desde`/`hasta` en producción.

Hallazgos de la primera medición (p95 > 3 s) y correcciones:

1. **Lista de espera**: cada `GET /api/espera` ejecutaba el mantenimiento (`barrer`) sobre *todos* los libros con espera
   (1.7 s con 1 000 entradas; 30 s con 20 concurrentes por los bloqueos). Ahora solo toca los libros que lo necesitan
   (`espera/model.py::libros_por_avanzar`: posiciones no consecutivas o ejemplares sin apartar). Pasó a 0.06 s.
2. **Listados sin tope**: usuarios (5 000 filas), préstamos (20 664) y multas devolvían todo (p95 4.5 s y 9.3 s con 20
   concurrentes). Ahora aceptan `?limite=` (500 por defecto, 2 000 máximo; `core/repo.py::tope`) y la pantalla indica
   "primeros 500: usa la búsqueda o los filtros". Pasaron a 0.28 s y 0.43 s.
3. **Procesos**: gunicorn pasó de 2 a 4 (`WEB_CONCURRENCY`, una por núcleo).

No hizo falta agregar índices: los planes usan los existentes (`EXPLAIN ANALYZE` de la lista de espera: 13 ms).

## 3.1 Errores (PS-S3-06)

Los errores 500 y los errores de JavaScript del navegador quedan en `bitacora` (`accion = 'error_sistema'`, detalle
`servidor|GET /ruta: Tipo: mensaje` o `cliente|#/ruta: mensaje (archivo:línea)`). El servidor escribe con una conexión
propia (la petición fallida hace rollback). `POST /api/errores` es público y limita a 5 reportes por minuto por IP y
60 en total; `main.js` envía como máximo 5 por carga de página. Consulta: **Reportes → Errores** (permiso `reportes`).
**Indicadores** (PS-MET-02/03): el tiempo de atención en mostrador *no es derivable* (no se registra el inicio de
la atención): la fila lo indica y se mantiene el cronometraje manual (PS-MET-01); sí se calcula la duración promedio del
préstamo.

## 3.2 Asistente con IA local (D-13, RNF-12/13)

El servicio `ollama` (imagen `ollama/ollama:0.40.16`, sin puerto publicado) guarda los modelos en el volumen `ollama_models` y tiene tope de memoria `OLLAMA_MEM_LIMIT` (2 GB). `scripts/levantar.py` descarga el modelo si falta (`ollama pull`, con progreso) y lo precalienta con una petición mínima (omitir con `--sin-ia`). `web` solo espera que `ollama` haya iniciado: si no responde, el asistente usa reglas.

**Elección del modelo** (equipo de pruebas: Docker Desktop con 10 CPU y 8 GB, solo CPU; mismas 11 preguntas con contexto de la base real; tiempos por pregunta, la primera incluye cargar el modelo):

| Modelo | Descarga | RAM en uso | Tiempo por respuesta | Calidad con el contexto |
| --- | --- | --- | --- | --- |
| `qwen2.5:0.5b` | 397 MB | 0.7-0.8 GB | 0.2-2.3 s | Pobre: respuestas cortas o equivocadas ("no, no tienen" teniendo el libro; fechas sueltas) |
| `qwen3:0.6b` | 522 MB | 1.1 GB | 0.2-1.8 s | Inventa (capital de Francia "Berlín") y dice "no tengo información" con el dato a la vista |
| `gemma3:270m` | 291 MB | 0.7 GB | 0.2-0.8 s | Inservible: saluda en cada respuesta e ignora la pregunta |
| `gemma3:1b` | 806 MB | 1.4 GB | 1.2-2.5 s | Inventó libros ("Python Programming") |
| `llama3.2:1b` | 1.3 GB | 1.7 GB | 0.3-3.3 s | Responde "No lo sabes" aun con el dato en el contexto |
| **`qwen2.5:1.5b`** (elegido) | 986 MB | 1.4 GB | 0.25-1.9 s (frío ~3-3.5 s) | La más fiel al contexto: fechas, ubicación y adeudos correctos |

`qwen2.5:0.5b` sigue disponible para equipos muy limitados (`OLLAMA_MODEL=qwen2.5:0.5b`), con respuestas peores; la guarda de fidelidad descarta lo que no esté respaldado y entonces responden las reglas.

**Latencia** (RNF-13, ≤ 3 s), `qwen2.5:1.5b`, 10 núcleos: 24 preguntas con el modelo ya cargado, mediana 0.98 s, p95 1.59 s, máximo 1.88 s. La primera pregunta con el modelo frío (tras 10 min sin uso, `keep_alive`) tarda ~3-3.5 s. Con las reglas (IA desactivada o caída) responde en ~0.03 s. **En equipos con menos núcleos el tiempo sube** (no medido): la pantalla muestra "Escribiendo…" y, si el modelo no responde en `OLLAMA_TIMEOUT` (20 s), contestan las reglas; para ir más rápido usa `qwen2.5:0.5b`.

**Recursos** (`docker stats` durante una respuesta): `ollama` 1.3 GiB de RAM y hasta ~10 núcleos al 100 % durante ~1 s; en reposo 0 % de CPU y el modelo sigue cargado 10 min (después libera la RAM). Disco: ~1 GB en el volumen.

**Problemas frecuentes**
- La pantalla dice "Modo básico": el modelo no está descargado o `ollama` no corre. `docker compose ps`, `docker compose logs ollama`, `docker compose exec ollama ollama list`; descarga con `python3 scripts/levantar.py --no-build`.
- Primera respuesta lenta: el modelo se carga en memoria (~3 s); `levantar.py` lo precalienta.
- Memoria insuficiente (`ollama` se reinicia): sube `OLLAMA_MEM_LIMIT` o usa `qwen2.5:0.5b`. Cambios de variables: `docker compose up -d`.
- Respuestas con `fuente: "reglas"` aunque la IA esté activa: la respuesta del modelo se descartó (cifra o título que no estaba en el contexto, tema ajeno) o hubo tiempo agotado; las caídas se anotan en Errores (máx. 1 cada 10 min).

## 4. lista de avisos (RNF-10, D-11)

Los avisos (correo, WhatsApp, Servicios Escolares, Tesorería) no se envían: se registran en `bitacora` con acción
`notif_<canal>` (`app/core/notificaciones.py`). Pantalla **Notificaciones** (personal con permiso `notificaciones`):
`GET /api/notificaciones?canal=&q=&desde=&limite=100`, con filtros de canal, periodo y persona/texto; **Mis
notificaciones** (`#/notificaciones/mias`, `GET /api/notificaciones/mias`) muestra solo las del usuario en sesión. Cada fila
se marca "Simulado". Cambiar a un proveedor real solo requiere modificar `core/notificaciones.py::enviar`.

## 5. Checklist de accesibilidad (RNF-06, D-16: WCAG 2.1 AA básico)

Revisión manual por pantalla (cada paquete no edita CSS; el responsable de estilos aplica las correcciones):

- [ ] Contraste de texto >= 4.5:1 (texto grande >= 3:1) en tema claro y en insignias (`good/warn/bad`), botones y enlaces.
- [ ] Foco visible (`:focus-visible`) en todos los controles; el orden de tabulación sigue el orden visual.
- [ ] Todo se opera solo con teclado: menú lateral, filtros, tablas, formularios, diálogos (el diálogo atrapa el foco,
      Esc lo cierra y devuelve el foco al disparador).
- [ ] Cada campo tiene `<label for>` (o `aria-label`); los obligatorios se indican con texto, no solo con color; los
      errores se asocian con `aria-describedby`.
- [ ] Mensajes de éxito/error en regiones `aria-live` (`role="alert"` para errores).
- [ ] `<html lang="es">`, enlace "Saltar al contenido", un único `<h1>` por pantalla, jerarquía de encabezados correcta.
- [ ] Tablas con `<th scope>` y título; los estados no dependen solo del color (la insignia lleva texto).
- [ ] La interfaz es utilizable con zoom al 200 % y en ancho móvil (320 px) sin pérdida de contenido.
- [ ] Imágenes e iconos informativos con texto alternativo; decorativos con `alt=""`/`aria-hidden`.
- [ ] Revisión estática: buscar `<input`/`<select>` sin label y `onclick` en elementos no interactivos.

## 6. Procesos de 3 clics (RNF-07, D-17)

Conteo desde la pantalla de inicio con la barra lateral, sin contar escritura. Máximo 3 clics.

| Proceso | Ruta de clics |
|---|---|
| Prestar | Préstamos y devoluciones -> Nuevo préstamo -> Confirmar |
| Devolver | Préstamos y devoluciones -> Devolver (fila del préstamo) -> Confirmar |
| Renovar | Préstamos y devoluciones -> Renovar (fila del préstamo) -> Confirmar |
| Registrar pago | Multas y pagos -> Registrar pago (fila del adeudo) -> Confirmar |
| Buscar y ver ubicación | Buscar y localizar -> Ver (resultado) -> (ubicación visible en la ficha) |
| Registrar libro | Catálogo -> Registrar libro -> Guardar |
| Crear solicitud de compra | Compras -> Nueva solicitud -> Guardar solicitud |
| Crear y enviar a Tesorería | Compras -> Nueva solicitud -> Guardar y enviar |

Verificado en Chrome el 2026-10-27 (7 procesos ≤ 3 clics). Antes de la corrección, enviar una solicitud costaba 4 clics
(Revisar y enviar -> Confirmar y enviar); ahora "Guardar y enviar" la envía en 3. "Revisar y enviar" conserva la pantalla
de confirmación (4 clics) para quien quiera revisar antes.

## 7. Seguridad (PS-S4-03, PS-NFR-05)

- **Token de recuperación**: `DEMO_MOSTRAR_TOKEN=true` (por defecto en `.env.example`, solo demostración) devuelve el código
  en la respuesta de `POST /api/recuperar`. Con `false` la API responde únicamente `{"ok": true}` (también si el correo no
  existe) y el código se registra como correo simulado (`notif_email`, visible en Notificaciones). Ponerlo en `false` en
  cualquier despliegue real.
- **Cookie de sesión**: siempre `HttpOnly` y `SameSite=Lax`; con `HTTPS=true` también `Secure`.
- **TLS** (no se ejecuta aquí): el contenedor `web` habla HTTP en el puerto 8000. Publicarlo detrás de un proxy inverso
  que termine TLS (nginx, Caddy o Traefik) con certificado válido, redirigir 80 -> 443, enviar `X-Forwarded-Proto`, no
  exponer los puertos 8000 y 5432 al exterior y poner `HTTPS=true`. Ejemplo mínimo con Caddy:
  `librigest.ejemplo.edu.mx { reverse_proxy web:8000 }` (certificado automático).
- Cambiar `SECRET_KEY` y las credenciales de PostgreSQL; las cuentas demo son públicas. Registros de acceso: `--access-logfile`
  de gunicorn y `bitacora`.
