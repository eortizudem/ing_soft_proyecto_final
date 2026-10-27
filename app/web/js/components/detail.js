import { html } from '/js/core/ui.js';
import { actions } from './actions.js';

/** detailGrid([[label, value], ...]) -> <dl class="detail-grid"> */
export const detailGrid = (items) => html`<dl class="detail-grid">${items.map(([l, v]) =>
  html`<div class="detail-item"><dt>${l}</dt><dd>${v}</dd></div>`)}</dl>`;

/**
 * detailView({ title, sub, badge, intro, items, actions }) -> card with record header, optional extra
 * block (intro), key/value grid, and an action bar below it.
 */
export const detailView = ({ title, sub = '', badge = '', intro = '', items, actions: buttons = [] }) => html`
  <section class="card detail"><div class="stack"><h2>${title}</h2>${sub ? html`<p class="sub">${sub}</p>` : ''}${badge}</div>
    ${intro}${detailGrid(items)}</section>
  ${actions(buttons)}`;

/**
 * receiptBlock({ id, title, folio, items, footer }) -> printable receipt card (préstamo, pago, solicitud).
 * Print it with printHtml($('#id').innerHTML) or core/pdf.js. items: [[label, value]...]; footer: extra markup.
 */
export const receiptBlock = ({ id, title, folio = '', items, footer = '' }) => html`
  <section class="card receipt" id="${id}"><div class="stack"><h2>${title}</h2>${folio ? html`<p class="mono">${folio}</p>` : ''}</div>
    ${detailGrid(items)}${footer}</section>`;
