// Catalog HTML (pure functions: data -> components).
import { html } from '/js/core/ui.js';
import { page, brand, btn, actions, toolbar, resultsPanel, resultsList, dataTable, cardList, itemCard, card, note, detailView,
  statusBadge, formView, submitButton, labelItems, label, location, count, receiptBlock, emptyState, notice, date } from '/js/components/index.js';
import { PLANTAS, PASILLOS, range, CAMPOS } from './model.js';

const DISPONIBILIDAD = [['', 'Toda disponibilidad'], ['disponible', 'Con copias disponibles'], ['agotado', 'Sin copias disponibles']];

const themeOptions = (themes) => [['', 'Todos los temas'], ...themes];

export const listPage = (themes, filters) => page({
  title: 'Catálogo de libros',
  desc: 'Una colección actualizada, con disponibilidad y ubicación por ejemplar.',
  actions: html`${btn({ label: 'Pendientes de catalogar', href: 'libros/pendientes' })}${btn({ label: 'Importar CSV', href: 'libros/importar' })}${btn({ label: 'Registrar libro', href: 'libros/nuevo', variant: 'primary' })}`,
  body: html`
  ${toolbar({
    search: { name: 'q', label: 'Buscar en catálogo', value: filters.q, placeholder: 'Título, autor, tema, clave o editorial' },
    filters: [
      { name: 'campo', label: 'Buscar por', value: filters.campo, options: CAMPOS },
      { name: 'tipo_uso', label: 'Tipo de uso', value: filters.tipo_uso, options: [['', 'Todos los usos'], ...labelItems('tipoUso')] },
      { name: 'disponibilidad', label: 'Disponibilidad', value: filters.disponibilidad, options: DISPONIBILIDAD },
      { name: 'tema', label: 'Tema', value: filters.tema, options: themeOptions(themes) },
      { name: 'estado', label: 'Estado', value: filters.estado, options: [['', 'Todos los estados'], ...labelItems('estadoLibro')] },
    ],
  })}
  ${resultsPanel()}`,
});

export const summary = (books) => count(books.length);

export const rows = (books) => dataTable({
  rows: books,
  empty: { text: 'Prueba otro título, autor, tema, clave o editorial.' },
  columns: [
    { label: 'Clave', key: 'clave' },
    { label: 'Título', render: (b) => html`<span class="mono">${b.titulo}</span>${b.estado === 'inactivo' ? html`<br>${statusBadge('estadoLibro', 'inactivo')}` : ''}` },
    { label: 'Autor', key: 'autor' },
    { label: 'Editorial', key: 'editorial' },
    { label: 'Uso', render: (b) => label('tipoUso', b.tipo_uso) },
    { label: 'Disponibles', render: (b) => `${b.disponibles} / ${b.ejemplares}` },
    { label: 'Acciones', render: (b) => html`<div class="row-actions">${btn({ label: 'Ver', href: 'libros/' + b.id_libro })}${btn({ label: 'Editar', href: `libros/${b.id_libro}/editar` })}</div>` },
  ],
});

export function form(book, themes, editing, pending = null) {
  const u = book.ubicacion;
  return page({
    title: editing ? 'Editar ficha bibliográfica' : 'Registrar libro',
    desc: 'Datos bibliográficos, ejemplares y ubicación física en una sola ficha.',
    body: html`${pending ? notice({ text: `Registrando la compra recibida ${pending.folio}: ${pending.descripcion} (${pending.cantidad_recibida} recibidos).` }) : ''}${formView({
      id: 'book-form',
      fields: [
        { name: 'clave', label: 'Clave', value: book.clave, required: true, maxlength: 24, readonly: editing },
        { name: 'titulo', label: 'Título', value: book.titulo, required: true, maxlength: 180 },
        { name: 'autor', label: 'Autor', value: book.autor, required: true, maxlength: 120 },
        { name: 'editorial', label: 'Editorial', value: book.editorial, required: true, maxlength: 120 },
        { name: 'tema', label: 'Tema', value: book.tema, required: true, maxlength: 80, list: 'themes' },
        { name: 'anio_publicacion', label: 'Año de publicación', type: 'number', value: book.anio_publicacion, required: true, min: 1000, max: 2100, step: 1 },
        { name: 'ejemplares', label: 'Ejemplares', type: 'number', value: book.ejemplares, required: true, min: 1, max: 10000, step: 1 },
        { name: 'tipo_uso', label: 'Tipo de uso', type: 'select', required: true, value: book.tipo_uso, options: labelItems('tipoUso') },
        { name: 'planta', label: 'Planta', type: 'select', value: u.planta, options: PLANTAS },
        { name: 'pasillo', label: 'Pasillo', type: 'select', value: u.pasillo, options: PASILLOS },
        { name: 'librero', label: 'Librero (plano)', type: 'select', value: Number(u.librero), options: range(1, 12) },
        { name: 'nivel', label: 'Nivel', type: 'select', value: u.nivel, options: range(1, 5) },
        { name: 'precio_referencia', label: 'Precio de referencia', type: 'number', value: book.precio_referencia, required: true, min: 0, step: 0.01 },
        { name: 'clasificacion', label: 'Clasificación', value: book.clasificacion, required: true },
        { name: 'estado', label: 'Estado', type: 'select', value: book.estado, options: labelItems('estadoLibro') },
        { name: 'sinopsis', label: 'Sinopsis', type: 'textarea', span: 'wide', value: book.sinopsis, required: true, maxlength: 2000 },
      ],
      children: html`<datalist id="themes">${themes.map((t) => html`<option value="${t}"></option>`)}</datalist>`,
      actions: [btn({ label: 'Cancelar', href: editing ? 'libros/' + book.id_libro : 'catalogo', variant: 'link' }),
        submitButton(editing ? 'Guardar cambios' : 'Registrar libro')],
    })}`,
  });
}

export const availability = (b) => statusBadge('disponibilidad',
  b.estado === 'inactivo' ? 'baja' : b.disponibles > 0 ? 'disponible' : 'agotado');

const ejemplarRow = (e) => html`<tr>
  <td class="mono">${e.etiqueta}</td>
  <td>${statusBadge('disponibilidad', e.estado)}${e.motivo_baja ? html` ${statusBadge('motivoBaja', e.motivo_baja)}` : ''}</td>
  <td>${e.prestamo_activo ? `${e.prestamo_activo.matricula} · vence ${date(e.prestamo_activo.fecha_vencimiento)}` : '—'}</td>
  <td>${date(e.fecha_alta)}</td>
  <td>${e.estado === 'disponible' ? html`<div class="row-actions">
      <select aria-label="Motivo de baja de ${e.etiqueta}" data-motivo="${e.id_ejemplar}" required><option value="">Selecciona motivo</option>${labelItems('motivoBaja').map(([v, t]) => html`<option value="${v}">${t}</option>`)}</select>
      ${btn({ label: 'Dar de baja', action: 'baja', variant: 'danger', data: { id: e.id_ejemplar, etiqueta: e.etiqueta } })}</div>`
    : e.estado === 'baja' ? btn({ label: 'Reactivar', action: 'reactivar', data: { id: e.id_ejemplar, etiqueta: e.etiqueta }, when: e.activo })
    : html`<span class="hint">Prestado: usa Multas y pagos para registrar pérdida.</span>`}</td></tr>`;

export const ejemplaresSection = (items, libroActivo) => card({
  title: 'Ejemplares',
  body: items.length ? html`<div class="table-wrap"><table><thead><tr><th scope="col">Etiqueta</th><th scope="col">Estado</th>
    <th scope="col">Préstamo activo</th><th scope="col">Alta</th><th scope="col">Acciones</th></tr></thead>
    <tbody>${items.map((e) => ejemplarRow({ ...e, activo: libroActivo }))}</tbody></table></div>`
    : emptyState({ text: 'Este libro no tiene ejemplares registrados.' }),
});

// Printable ficha bibliográfica + ejemplar labels (printHtml / PDF).
export const fichaBlock = (e) => receiptBlock({
  id: 'ficha', title: 'Ficha bibliográfica', folio: e.clave,
  items: [['Título', e.titulo], ['Autor', e.autor], ['Clasificación', e.clasificacion], ['Ubicación', location(e.ubicacion)]],
  footer: html`<h3>Etiquetas de ejemplares</h3>${dataTable({
    rows: e.codigo_ejemplares, empty: { text: 'Sin ejemplares activos.' },
    columns: [{ label: 'Etiqueta', render: (c) => html`<strong class="mono">${c.etiqueta}</strong>` },
      { label: 'Clasificación', render: () => e.clasificacion }, { label: 'Ubicación', render: () => location(e.ubicacion) }] })}`,
});

export const pdfLines = (e) => [`Ficha bibliografica ${e.clave}`, '', `Titulo: ${e.titulo}`, `Autor: ${e.autor}`,
  `Clasificacion: ${e.clasificacion}`, `Ubicacion: ${location(e.ubicacion)}`, '', 'Etiquetas de ejemplares:',
  ...e.codigo_ejemplares.map((c) => `  ${c.etiqueta}  |  ${e.clasificacion}  |  ${location(e.ubicacion)}`)];

// "Unirse a lista de espera" (package B): prestable, active, no copies, logged-in non-visitor.
const canJoinQueue = (b, canWait) => !!canWait && b.disponibles === 0 && b.estado === 'activo' && b.tipo_uso === 'prestamo_externo';
const joinQueueBtn = (b, canWait, variant = '') =>
  btn({ label: 'Unirse a lista de espera', href: `espera/unirse/${b.id_libro}`, variant, when: canJoinQueue(b, canWait) });

export const detail = (b, { canEdit, canLocate, canWait = false, ejemplares = null }) => page({
  title: 'Ficha del libro',
  desc: 'Información bibliográfica y ejemplares disponibles.',
  body: html`${detailView({
    title: b.titulo,
    sub: `${b.autor} · ${b.editorial} · ${b.anio_publicacion}`,
    badge: availability(b),
    intro: note('Sinopsis', b.sinopsis),
    items: [
      ['Ejemplares', `${b.disponibles} disponibles de ${b.ejemplares} (${b.prestados} prestados)`],
      ['Tipo de uso', label('tipoUso', b.tipo_uso)],
      ['Ubicación', location(b.ubicacion)],
      ['Clave', b.clave],
      ['Tema', b.tema],
      ['Clasificación', b.clasificacion],
    ],
    actions: [
      btn({ label: 'Editar ficha', href: `libros/${b.id_libro}/editar`, variant: 'primary', when: canEdit }),
      btn({ label: 'Imprimir ficha y etiquetas', action: 'imprimir', when: canEdit }),
      btn({ label: 'Descargar PDF', action: 'pdf', when: canEdit }),
      btn({ label: b.estado === 'activo' ? 'Dar de baja' : 'Reactivar libro', action: 'toggle', variant: 'danger', when: canEdit }),
      joinQueueBtn(b, canWait, 'primary'),
      btn({ label: 'Ver ubicación', href: `libros/${b.id_libro}/ubicacion`, variant: 'link', when: canLocate }),
      btn({ label: 'Volver', href: canEdit ? 'catalogo' : 'buscar', variant: 'link' }),
    ],
  })}${ejemplares ? ejemplaresSection(ejemplares, b.estado === 'activo') : ''}`,
});

export const pendientesPage = () => page({
  title: 'Pendientes de catalogar',
  desc: 'Compras recibidas que aún no tienen ficha en el catálogo.',
  actions: btn({ label: 'Volver al catálogo', href: 'catalogo', variant: 'link' }),
  body: html`<section class="card"><div id="results"></div></section>`,
});

export const pendientesRows = (items) => dataTable({
  rows: items, empty: { title: 'Todo catalogado', text: 'No hay compras recibidas pendientes de catalogar.' },
  columns: [{ label: 'Folio', key: 'folio' }, { label: 'Descripción', key: 'descripcion' },
    { label: 'Recibidos', key: 'cantidad_recibida', align: 'right' },
    { label: 'Acciones', render: (p) => btn({ label: 'Catalogar', href: `libros/nuevo?id_detalle=${p.id_detalle}`, variant: 'primary' }) }],
});

export const importPage = () => page({
  title: 'Importar libros (CSV)',
  desc: 'Alta masiva desde un archivo CSV. Se crean las filas válidas y se informan los errores por línea.',
  body: html`${formView({
    id: 'import-form',
    fields: [
      { name: 'archivo', label: 'Archivo CSV', type: 'file', accept: '.csv,text/csv', hint: 'Opcional: carga el archivo o pega el contenido abajo.' },
      { name: 'csv', label: 'Contenido CSV', type: 'textarea', span: 'wide', required: true,
        hint: 'Cabecera: clave,titulo,autor,editorial,tema,anio_publicacion,clasificacion,sinopsis,precio_referencia,ejemplares[,tipo_uso,planta,pasillo,librero,nivel]' },
    ],
    actions: [btn({ label: 'Cancelar', href: 'catalogo', variant: 'link' }), submitButton('Importar')],
  })}<div id="import-result" aria-live="polite"></div>`,
});

export const importResult = (r) => html`${notice({ text: `${r.creados} libro(s) creado(s); ${r.errores.length} error(es).`, tone: r.errores.length ? 'error' : 'success' })}
  ${r.errores.length ? dataTable({ rows: r.errores, columns: [{ label: 'Línea', key: 'linea' }, { label: 'Motivo', key: 'motivo' }] }) : ''}`;

// ---- Public search (buscar) and floor plan ----

export const searchResults = (books, canWait = false) => cardList({
  items: books,
  empty: { text: 'No encontramos coincidencias. Revisa los filtros o prueba otra búsqueda.' },
  render: (b) => itemCard({
    title: b.titulo,
    lines: [`${b.autor} · ${b.editorial} · ${b.clave}`,
      `${b.disponibles} de ${b.ejemplares} copias disponibles · ${label('tipoUso', b.tipo_uso)}.`],
    badge: statusBadge('disponibilidad', b.disponibles ? 'disponible' : 'agotado'),
    actions: html`${btn({ label: 'Abrir', href: `libros/${b.id_libro}/ubicacion` })}${joinQueueBtn(b, canWait)}`,
  }),
});

const searchToolbar = (label, filters, extra = []) => toolbar({
  id: 'search-form',
  search: { name: 'q', label, value: filters.q, placeholder: 'Escribe para buscar' },
  filters: extra,
  submit: 'Buscar',
});

export const searchPage = (themes, filters, canWait = false) => page({
  title: 'Encuentra tu próximo libro',
  desc: 'Consulta el catálogo y encuentra cada libro dentro de la biblioteca.',
  actions: html`${btn({ label: 'Mis solicitudes de espera', href: 'espera/mias', when: canWait })}${btn({ label: 'Ver búsqueda móvil', href: 'movil' })}`,
  body: html`${searchToolbar('Buscar por título, autor, tema, clave o editorial', filters, [
    { name: 'tema', label: 'Tema', value: filters.tema, options: themeOptions(themes) },
    { name: 'campo', label: 'Buscar por', value: filters.campo, options: CAMPOS },
    { name: 'tipo_uso', label: 'Tipo de uso', value: filters.tipo_uso, options: [['', 'Todos los usos'], ...labelItems('tipoUso')] },
    { name: 'disponibilidad', label: 'Disponibilidad', value: filters.disponibilidad, options: DISPONIBILIDAD },
  ])}${resultsList()}`,
});

export const mobilePage = (filters, canAssistant = false) => html`${brand()}${page({
  title: 'Encuentra tu libro',
  desc: 'Biblioteca Ducky',
  body: html`${searchToolbar('Título o autor', filters)}${resultsList()}
    ${actions([btn({ label: 'Asistente virtual', href: 'movil/asistente', when: canAssistant }),
      btn({ label: 'Volver a escritorio', href: 'buscar', variant: 'link' })])}`,
})}`;

const shelves = (selected) => Array.from({ length: 12 }, (_, i) => i + 1).map((n) => {
  const id = String(n).padStart(2, '0');
  return html`<div class="shelf ${n === selected ? 'selected' : ''}">${n === selected ? id + ' · TU LIBRO' : 'Librero ' + id}</div>`;
});

export function locationPage(b, mobile) {
  const where = location(b.ubicacion);
  const stock = b.estado === 'inactivo' ? 'Este libro fue dado de baja.'
    : b.disponibles > 0 ? `Hay ${b.disponibles} copias disponibles.` : 'No hay copias disponibles en este momento.';
  return html`${mobile ? brand() : ''}${page({
    title: 'Ubicación en biblioteca',
    desc: `${b.titulo} · ${b.autor} · ${b.clave}`,
    body: html`
  <div class="location-grid">
    <section class="card map"><p class="eyebrow">${b.ubicacion.planta}</p>
      <div class="shelves">${shelves(Number(b.ubicacion.librero))}</div>
      <p class="path">${where.replaceAll(' · ', ' → ')}</p></section>
    ${card({ title: 'Tu ruta', level: 3, cls: 'route-card', body: html`<p>${where.replaceAll(' · ', '\n')}<br>Clasificación: ${b.clasificacion}</p>` })}</div>
  ${card({ title: 'Antes de ir', level: 3, body: html`<p>${stock} Consulta al bibliotecario si el ejemplar no está en su lugar.</p>` })}
  ${actions([btn({ label: 'Volver a resultados', href: mobile ? 'movil' : 'buscar', variant: 'link' }),
    btn({ label: mobile ? 'Volver a escritorio' : 'Ver en móvil', href: mobile ? `libros/${b.id_libro}/ubicacion` : `movil/${b.id_libro}`, variant: 'primary' })], { spread: true })}`,
  })}`;
}
