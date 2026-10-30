/** @module components/meter — barra de progreso accesible. */
import { html } from '/js/core/ui.js';

/**
 * Barra de progreso accesible (presupuesto usado, cupo de libros...). El valor se limita a `max`.
 * @param {Object} opts - Opciones.
 * @param {number|string} opts.value - Valor actual.
 * @param {number|string} opts.max - Valor máximo.
 * @param {string} opts.label - Etiqueta visible y `aria-label`.
 * @param {string} [opts.text] - Texto auxiliar a la derecha (p. ej. «3 de 5»).
 * @returns {Safe} HTML de la barra.
 * @example meter({ value: 3, max: 5, label: 'Libros prestados', text: '3 de 5' })
 */
export const meter = ({ value, max, label, text = '' }) => html`
  <div class="meter-block"><div class="meter-head"><span>${label}</span><span class="mono muted">${text}</span></div>
    <progress class="meter" value="${Math.min(Number(value) || 0, Number(max) || 0)}" max="${Number(max) || 1}" aria-label="${label}"></progress></div>`;
