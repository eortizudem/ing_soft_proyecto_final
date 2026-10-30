/** @module components/badge — insignias (badges) de estado con tono de color. */
import { html } from '/js/core/ui.js';
import { label, tone } from './labels.js';

/**
 * Insignia `<span class="badge">`.
 * @param {string} text - Texto de la insignia.
 * @param {string} [kind='good'] - Tono: 'good' | 'warn' | 'bad'.
 * @returns {Safe} HTML de la insignia.
 * @example badge('Vencido', 'bad')
 */
export const badge = (text, kind = 'good') => html`<span class="badge ${kind}">${text}</span>`;

/**
 * Insignia cuyo texto y tono salen de `labels.js`.
 * @param {string} kind - Tipo de enumeración (clave de `LABELS`, p. ej. 'prestamo').
 * @param {string} value - Valor almacenado (p. ej. 'vencido').
 * @returns {Safe} HTML de la insignia.
 * @example statusBadge('solicitud', 'pendiente') // <span class="badge warn">Pendiente</span>
 */
export const statusBadge = (kind, value) => badge(label(kind, value), tone(kind, value));
