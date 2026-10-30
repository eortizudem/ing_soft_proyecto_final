# Biblioteca de componentes de LibriGest

Una sola fuente de verdad para el marcado, el comportamiento y las etiquetas. **Todo módulo nuevo
(préstamos, asistente, etc.) debe usar estos componentes** y no definir sus propias tablas,
formularios, toolbars, badges ni mapas de etiquetas.

```js
import { page, btn, dataTable } from '/js/components/index.js';   // todo sale de index.js
```

Reglas: `view.js` es puro (datos -> HTML con componentes); `controller.js` usa `core/crud.js`,
`bindToolbar`, `bindForm`, `onAction` y `confirmAction`; `model.js` solo habla con la API.
Las primitivas de bajo nivel (`html`, `raw`, `attrs`, `$`, `toast`, `showError`) viven en `core/ui.js`.
Las clases CSS son las canónicas de `css/components.css`; no hay estilos en línea.

| Archivo | Componentes |
|---|---|
| `page.js` | `page({title, desc, actions, body})`, `brand()` |
| `actions.js` | `btn`, `backLink`, `actions`, `onAction`, `printHtml` |
| `toolbar.js` | `toolbar`, `bindToolbar` |
| `table.js` | `dataTable` |
| `form.js` | `formField`, `formView`, `formActions`, `submitButton`, `bindForm`, `serializeForm`, `bindFileToText`, `options` |
| `detail.js` | `detailGrid`, `detailView`, `receiptBlock` |
| `card.js` | `card`, `grid`, `linkCard`, `statCard`, `itemCard`, `cardList`, `resultsPanel`, `resultsList`, `note`, `disclosure` |
| `badge.js` | `badge`, `statusBadge` |
| `notice.js`, `empty.js` | `notice`, `emptyState` |
| `modal.js` | `confirmAction` |
| `meter.js` | `meter` |
| `chat.js` | `chatBubble`, `chatPanel`, `appendChat`, `bindChat` |
| `format.js` | `money(n, currency)`, `usd`, `number`, `date`, `today`, `datetime`, `location`, `person`, `book`, `count(n, noun, limit)` (con `LIST_LIMIT` de `core/api.js` avisa que el listado esta acotado) |
| `labels.js` | `LABELS`, `TONES`, `label`, `labelItems`, `tone`, `roleName` |
| `../core/crud.js` | `listPage`, `editPage`, `bindToggle` |

## Ejemplos

**Página y botones** (`when: false` no renderiza nada; úsalo para permisos)
```js
page({ title: 'Préstamos', desc: 'Control de préstamos.',
  actions: btn({ label: 'Nuevo', href: 'prestamos/nuevo', variant: 'primary', when: can('prestamos') }),
  body });
```
`btn({label, href})` genera un enlace `#/ruta`; `btn({label, action:'x', data:{id:1}})` un botón `data-action`.
`variant`: `primary`, `danger`, `link`.

**Lista con filtros** (vista + controlador)
```js
// view.js
page({ title, body: html`${toolbar({
  search: { name: 'q', label: 'Buscar', value: f.q },
  filters: [{ name: 'estado', label: 'Estado', value: f.estado, options: [['', 'Todos'], ...labelItems('prestamo')] }],
})}${resultsPanel()}` });
const rows = (items) => dataTable({ rows: items, empty: { text: 'Sin resultados.' },
  columns: [{ label: 'Folio', key: 'folio' },
            { label: 'Estado', render: (p) => statusBadge('prestamo', p.estado) }] });
// controller.js  (filters = objeto del módulo; conserva el estado al navegar)
await listPage(ctx, { markup: view.listPage(filters), filters, load: model.list, render: view.rows,
                      summary: (items) => count(items.length) });
```

**Formulario**
```js
formView({ id: 'x-form', fields: [
  { name: 'titulo', label: 'Título', required: true, maxlength: 100 },
  { name: 'estado', label: 'Estado', type: 'select', options: labelItems('prestamo') },
  { name: 'nota', label: 'Nota', type: 'textarea', span: 'wide', hint: 'Opcional' },
], actions: [btn({ label: 'Cancelar', href: 'x', variant: 'link' }), submitButton('Guardar')] });
// controller: validación con aria-invalid, foco al primer campo inválido, botón deshabilitado y error del servidor en #alert
editPage(ctx, { markup, formId: 'x-form', save: model.save, message: 'Guardado.', redirect: (r) => 'x/' + r.id });
```
Tipos: `text email number password search select textarea checkbox`. Los campos `required` llevan `*` (`stars:false` lo omite).

**Detalle con baja/reactivación**
```js
detailView({ title, sub, badge: statusBadge('prestamo', p.estado),
  items: [['Usuario', p.usuario], ['Vence', date(p.vence)]],
  actions: [btn({ label: 'Dar de baja', action: 'toggle', variant: 'danger' }), btn({ label: 'Volver', href: 'x', variant: 'link' })] });
bindToggle(main, { confirm: () => ({ title, message, confirmLabel }), run: () => model.toggle(id),
                   success: () => 'Actualizado.', refresh: () => detail(params, ctx) });
```
`confirmAction({title, message, confirmLabel})` devuelve `Promise<boolean>`. `onAction(root, {nombre: handler})`
conecta botones `data-action`, deshabilita el botón mientras corre y muestra los errores.

**Estados y etiquetas**: añade nuevos estados en `labels.js` (`LABELS` y `TONES`, ya existen `prestamo`,
`adeudo`, `listaEspera`) y usa `statusBadge(tipo, valor)`, `label()` y `labelItems()`. Vacíos: `emptyState({title, text})`.
Formato: `money`, `date` (solo fecha), `datetime`, `location`.

**Recibo / comprobante** (`receiptBlock`, se imprime con `printHtml` o `core/pdf.js`)
```js
receiptBlock({ id: 'recibo', title: 'Recibo de préstamo', folio: 'REC-000123',
  items: [['Usuario', u.nombre], ['Vence', date(p.fecha_vencimiento)]], footer: note('Multa', '$10 por día hábil') });
```

**Barra de avance** (`meter`): `meter({ value: 3200, max: 5000, label: 'Presupuesto del mes (USD)', text: '64 %' })`.

**Chat** (asistente, lista de consultas para el bibliotecario; sin lógica de negocio)
```js
// view.js
chatPanel({ id: 'chat', messages: items.map(chatBubble) });
// controller.js
bindChat($('#chat', main), { send: async (texto) => {
  appendChat('chat', chatBubble({ emisor: 'usuario', texto }));
  const r = await model.send(texto);                       // POST /api/asistente/mensajes
  appendChat('chat', chatBubble({ emisor: 'asistente', texto: r.respuesta.texto }));
} });
```

**Etiquetas disponibles** (no editar `labels.js` desde un paquete): `estadoUsuario estadoLibro fuente tipoUso(+reservado)
solicitud(+recibida) disponibilidad prestamo adeudo adeudoTipo listaEspera motivoBaja canal canalChat emisor consulta`.
Si falta una, avísalo en el informe del paquete.

**Navegación**: las entradas del menú (`core/layout.js`) solo aparecen si el usuario tiene el permiso **y** el módulo
registró una ruta con ese nombre; `main.js` carga cada `/m/<m>/controller.js` de forma tolerante.

Router: los handlers reciben `(params, ctx)`; `ctx.query` son los parametros de `#/ruta?a=b`. `api.delete(path)`; los errores de `api`
conservan `status`, `data` y los campos del JSON (`err.motivos`), y `showError(err)` los muestra como lista. Formularios:
`formField({ type: 'file', accept })` + `bindFileToText(input, textarea)`.
