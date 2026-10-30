/** @module components/notice — avisos informativos, de éxito o de error. */
import { html } from '/js/core/ui.js';

/**
 * Aviso `.notice`; no renderiza nada si no hay texto.
 * @param {Object} opts - Opciones.
 * @param {string} opts.text - Texto del aviso.
 * @param {string} [opts.tone='info'] - 'info' | 'success' | 'error'.
 * @param {string} [opts.role] - Rol ARIA (por defecto 'alert' en error y 'status' en el resto).
 * @param {string} [opts.cls] - Clases extra.
 * @returns {Safe|string} HTML del aviso, o cadena vacía.
 */
export const notice = ({ text, tone = 'info', role, cls = '' }) =>
  text ? html`<div class="notice ${tone === 'info' ? '' : tone} ${cls}" role="${role || (tone === 'error' ? 'alert' : 'status')}">${text}</div>` : '';
