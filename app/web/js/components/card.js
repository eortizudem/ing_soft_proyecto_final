/** @module components/card — tarjetas y layouts basados en tarjetas. */
import { html, attrs } from '/js/core/ui.js';
import { btn } from './actions.js';
import { emptyState } from './empty.js';

/**
 * Tarjeta `<section class="card">` con título opcional.
 * @param {Object} opts - Opciones.
 * @param {string} [opts.title] - Título (si falta no se pinta encabezado).
 * @param {Safe|string} [opts.body] - Contenido.
 * @param {string} [opts.cls] - Clases extra, p. ej. 'receipt', 'detail', 'split'.
 * @param {string} [opts.id] - Atributo id.
 * @param {number} [opts.level=2] - Nivel del encabezado (h1-h6).
 * @returns {Safe} HTML de la tarjeta.
 */
export const card = ({ title, body = '', cls = '', id, level = 2 }) => html`
  <section class="card ${cls}"${attrs({ id })}>${title ? html`<h${level}>${title}</h${level}>` : ''}${body}</section>`;

/**
 * Bloque con un rótulo pequeño y un texto dentro de una tarjeta.
 * @param {string} eyebrow - Rótulo.
 * @param {Safe|string} text - Texto.
 * @returns {Safe} HTML del bloque.
 */
export const note = (eyebrow, text) => html`<div class="stack"><p class="eyebrow">${eyebrow}</p><p>${text}</p></div>`;

/**
 * Rejilla de elementos.
 * @param {Array<Safe|string>} items - Elementos.
 * @param {Object} [opts] - Opciones.
 * @param {number|string} [opts.cols=2] - Columnas: 2, 3 o 'stats' (rejilla de estadísticas).
 * @param {string} [opts.cls] - Clases extra.
 * @returns {Safe} HTML de la rejilla.
 */
export const grid = (items, { cols = 2, cls = '' } = {}) =>
  html`<div class="grid ${cols === 'stats' ? 'stats' : 'cols-' + cols} ${cls}">${items}</div>`;

/**
 * Tarjeta de acceso rápido del inicio con botón «Abrir».
 * @param {Object} opts - Opciones.
 * @param {string} opts.title - Título.
 * @param {string} opts.text - Descripción.
 * @param {string} opts.href - Ruta hash destino (sin "#/").
 * @param {boolean} [opts.full=false] - Ocupa todo el ancho.
 * @returns {Safe} HTML de la tarjeta.
 */
export const linkCard = ({ title, text, href, full = false }) => html`
  <article class="card quick-card ${full ? 'full' : ''}"><h3>${title}</h3><p class="muted">${text}</p>${btn({ label: 'Abrir', href })}</article>`;

/**
 * Tarjeta de estadística (valor destacado con nota).
 * @param {Object} opts - Opciones.
 * @param {string} opts.title - Etiqueta de la métrica.
 * @param {string|number} opts.value - Valor destacado.
 * @param {string} opts.note - Nota inferior.
 * @returns {Safe} HTML de la tarjeta.
 */
export const statCard = ({ title, value, note: text }) =>
  html`<article class="card stat"><p class="muted">${title}</p><div class="value">${value}</div><span class="mono muted">${text}</span></article>`;

/**
 * Tarjeta de fila: texto a la izquierda (título y líneas), insignia y acciones a la derecha.
 * @param {Object} opts - Opciones.
 * @param {string} opts.title - Título.
 * @param {Array<string|{muted: string}>} [opts.lines] - Líneas de texto; `{muted}` se pinta atenuada.
 * @param {Safe|string} [opts.badge] - Insignia bajo las líneas.
 * @param {Safe|string} [opts.actions] - Botones a la derecha.
 * @returns {Safe} HTML de la tarjeta.
 */
export const itemCard = ({ title, lines = [], badge = '', actions = '' }) => html`
  <article class="card split"><div class="stack"><h2>${title}</h2>
    ${lines.map((l) => (l instanceof Object && 'muted' in l ? html`<p class="muted">${l.muted}</p>` : html`<p>${l}</p>`))}
    ${badge}</div>${actions ? html`<div class="actions">${actions}</div>` : ''}</article>`;

/**
 * Lista de tarjetas `.card-list` o, si no hay elementos, el estado vacío.
 * @param {Object} opts - Opciones.
 * @param {Array<Object>} opts.items - Elementos.
 * @param {function(Object): Safe} opts.render - Pinta un elemento.
 * @param {Object} [opts.empty] - Opciones de `emptyState` ({ title, text }).
 * @returns {Safe} HTML de la lista.
 */
export const cardList = ({ items, render, empty }) =>
  items.length ? html`<div class="card-list">${items.map(render)}</div>` : emptyState(empty);

/**
 * Panel contenedor de resultados (#count y #results) que rellena `listPage`.
 * @returns {Safe} HTML del panel.
 */
export const resultsPanel = () => html`<section class="card"><p class="card-meta" id="count"></p><div id="results"></div></section>`;
/**
 * Contenedor #results en formato de lista de tarjetas (sin panel) para `listPage`.
 * @returns {Safe} HTML del contenedor.
 */
export const resultsList = () => html`<div id="results" class="card-list"></div>`;

/**
 * Bloque expandible `<details>`.
 * @param {Safe|string} summary - Texto del encabezado.
 * @param {Safe|string} body - Contenido desplegable.
 * @returns {Safe} HTML del bloque.
 */
export const disclosure = (summary, body) => html`<details><summary>${summary}</summary>${body}</details>`;
