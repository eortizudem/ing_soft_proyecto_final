/** @module components/empty — estado vacío (sin resultados o sin datos). */
import { html } from '/js/core/ui.js';

/**
 * Bloque `.empty` para cuando no hay resultados o datos.
 * @param {Object} [opts] - Opciones.
 * @param {string} [opts.title='No hay resultados'] - Título.
 * @param {string} [opts.text] - Texto de ayuda.
 * @returns {Safe} HTML del bloque.
 */
export const emptyState = ({ title = 'No hay resultados', text = '' } = {}) =>
  html`<div class="empty"><h2>${title}</h2>${text ? html`<p class="muted">${text}</p>` : ''}</div>`;
