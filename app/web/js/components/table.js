/** @module components/table — tabla de datos accesible con estado vacío. */
import { html, attrs } from '/js/core/ui.js';
import { emptyState } from './empty.js';

/**
 * Tabla de datos con encabezados `scope="col"`; sin filas muestra el estado vacío.
 * @param {Object} opts - Opciones.
 * @param {Array<Object>} opts.columns - Columnas.
 * @param {string} opts.columns[].key - Propiedad de la fila a mostrar.
 * @param {string} opts.columns[].label - Encabezado.
 * @param {function(Object, number): (Safe|string)} [opts.columns[].render] - Pinta la celda `(fila, índice)`.
 * @param {string} [opts.columns[].align] - 'center' | 'right'.
 * @param {Array<Object>} opts.rows - Filas.
 * @param {Object} [opts.empty] - Opciones de `emptyState` ({ title, text }) cuando no hay filas.
 * @param {function(Object): string} [opts.rowHref] - Ruta hash de la fila; la primera celda pasa a ser enlace.
 * @param {string} [opts.cls] - Clases de la tabla.
 * @returns {Safe} HTML de la tabla.
 * @example
 * dataTable({ columns: [{ key: 'titulo', label: 'Título' }, { key: 'estado', label: 'Estado',
 *   render: (r) => statusBadge('estadoLibro', r.estado) }], rows: libros, rowHref: (r) => `libros/${r.id}` })
 */
export function dataTable({ columns, rows, empty = {}, rowHref, cls = '' }) {
  if (!rows.length) return emptyState(empty);
  const alignClass = (c) => (c.align ? `col-${c.align}` : '');
  const cell = (c, row, i, first) => {
    const value = c.render ? c.render(row, i) : row[c.key];
    return html`<td${attrs({ class: alignClass(c) })}>${first && rowHref ? html`<a href="#/${rowHref(row)}">${value}</a>` : value}</td>`;
  };
  return html`<div class="table-wrap"><table${attrs({ class: cls })}>
    <thead><tr>${columns.map((c) => html`<th scope="col"${attrs({ class: alignClass(c) })}>${c.label}</th>`)}</tr></thead>
    <tbody>${rows.map((row, i) => html`<tr>${columns.map((c, n) => cell(c, row, i, n === 0))}</tr>`)}</tbody></table></div>`;
}
