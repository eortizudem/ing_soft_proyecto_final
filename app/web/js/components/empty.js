import { html } from '/js/core/ui.js';

/** emptyState({ title, text }) -> .empty block (no results / no data yet). */
export const emptyState = ({ title = 'No hay resultados', text = '' } = {}) =>
  html`<div class="empty"><h2>${title}</h2>${text ? html`<p class="muted">${text}</p>` : ''}</div>`;
