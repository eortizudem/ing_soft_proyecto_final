/** @module components/detail — vistas de detalle (clave/valor) y comprobantes imprimibles. */
import { html } from '/js/core/ui.js';
import { actions } from './actions.js';

/**
 * Lista de definición `<dl class="detail-grid">` con pares etiqueta/valor.
 * @param {Array<Array<any>>} items - Pares `[etiqueta, valor]`.
 * @returns {Safe} HTML de la rejilla.
 */
export const detailGrid = (items) => html`<dl class="detail-grid">${items.map(([l, v]) =>
  html`<div class="detail-item"><dt>${l}</dt><dd>${v}</dd></div>`)}</dl>`;

/**
 * Tarjeta de detalle: encabezado del registro, bloque extra opcional (`intro`), rejilla clave/valor y
 * barra de acciones debajo.
 * @param {Object} opts - Opciones.
 * @param {string} opts.title - Título del registro.
 * @param {string} [opts.sub] - Subtítulo.
 * @param {Safe|string} [opts.badge] - Insignia de estado.
 * @param {Safe|string} [opts.intro] - Bloque extra antes de la rejilla.
 * @param {Array<Array<any>>} opts.items - Pares `[etiqueta, valor]`.
 * @param {Array<Safe|string>} [opts.actions] - Botones de la barra inferior.
 * @returns {Safe} HTML del detalle.
 */
export const detailView = ({ title, sub = '', badge = '', intro = '', items, actions: buttons = [] }) => html`
  <section class="card detail"><div class="stack"><h2>${title}</h2>${sub ? html`<p class="sub">${sub}</p>` : ''}${badge}</div>
    ${intro}${detailGrid(items)}</section>
  ${actions(buttons)}`;

/**
 * Tarjeta de comprobante imprimible (préstamo, pago, solicitud). Se imprime con
 * `printHtml($('#id'))` o con `core/pdf.js`.
 * @param {Object} opts - Opciones.
 * @param {string} opts.id - Id de la sección (para localizarla al imprimir).
 * @param {string} opts.title - Título del comprobante.
 * @param {string} [opts.folio] - Folio mostrado en tipografía monoespaciada.
 * @param {Array<Array<any>>} opts.items - Pares `[etiqueta, valor]`.
 * @param {Safe|string} [opts.footer] - Marcado extra al final.
 * @returns {Safe} HTML del comprobante.
 */
export const receiptBlock = ({ id, title, folio = '', items, footer = '' }) => html`
  <section class="card receipt" id="${id}"><div class="stack"><h2>${title}</h2>${folio ? html`<p class="mono">${folio}</p>` : ''}</div>
    ${detailGrid(items)}${footer}</section>`;
