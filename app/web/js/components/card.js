// Cards and card-based layouts.
import { html, attrs } from '/js/core/ui.js';
import { btn } from './actions.js';
import { emptyState } from './empty.js';

/** card({ title, body, cls, id, level }) -> .card; cls e.g. 'receipt', 'detail', 'split'. */
export const card = ({ title, body = '', cls = '', id, level = 2 }) => html`
  <section class="card ${cls}"${attrs({ id })}>${title ? html`<h${level}>${title}</h${level}>` : ''}${body}</section>`;

/** Block with a small caption and text inside a card. */
export const note = (eyebrow, text) => html`<div class="stack"><p class="eyebrow">${eyebrow}</p><p>${text}</p></div>`;

/** grid(items, { cols: 2|3|'stats' }) */
export const grid = (items, { cols = 2, cls = '' } = {}) =>
  html`<div class="grid ${cols === 'stats' ? 'stats' : 'cols-' + cols} ${cls}">${items}</div>`;

/** Dashboard shortcut card with an "Abrir" button. */
export const linkCard = ({ title, text, href, full = false }) => html`
  <article class="card quick-card ${full ? 'full' : ''}"><h3>${title}</h3><p class="muted">${text}</p>${btn({ label: 'Abrir', href })}</article>`;

export const statCard = ({ title, value, note: text }) =>
  html`<article class="card stat"><p class="muted">${title}</p><div class="value">${value}</div><span class="mono muted">${text}</span></article>`;

/** Row card: text on the left (title, lines), badge/actions on the right. */
export const itemCard = ({ title, lines = [], badge = '', actions = '' }) => html`
  <article class="card split"><div class="stack"><h2>${title}</h2>
    ${lines.map((l) => (l instanceof Object && 'muted' in l ? html`<p class="muted">${l.muted}</p>` : html`<p>${l}</p>`))}
    ${badge}</div>${actions ? html`<div class="actions">${actions}</div>` : ''}</article>`;

/** cardList({ items, render, empty }) -> .card-list or the empty state. */
export const cardList = ({ items, render, empty }) =>
  items.length ? html`<div class="card-list">${items.map(render)}</div>` : emptyState(empty);

/** Where list results are rendered by crud.listPage (with an optional counter). */
export const resultsPanel = () => html`<section class="card"><p class="card-meta" id="count"></p><div id="results"></div></section>`;
export const resultsList = () => html`<div id="results" class="card-list"></div>`;

/** Expandable block. */
export const disclosure = (summary, body) => html`<details><summary>${summary}</summary>${body}</details>`;
