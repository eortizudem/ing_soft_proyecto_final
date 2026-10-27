import { html, attrs } from '/js/core/ui.js';
import { emptyState } from './empty.js';

/**
 * dataTable({ columns, rows, empty, rowHref, cls })
 *  columns: [{ key, label, render?(row, index), align?: 'center'|'right' }]
 *  rowHref(row) -> route: first cell becomes a link. empty: { title, text } shown when no rows.
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
