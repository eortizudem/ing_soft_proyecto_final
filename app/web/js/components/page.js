/** @module components/page — estructura de página: encabezado, regiones de mensajes y marca. */
import { html } from '/js/core/ui.js';
import { logoSrc } from '/js/core/theme.js';

/**
 * Página: encabezado + regiones de mensajes (#alert para errores, #flash para éxito) + cuerpo.
 * El router envuelve el resultado en `<div class="page">` (ver `layout.setContent`).
 * @param {Object} opts - Opciones.
 * @param {string} opts.title - Título (<h1>).
 * @param {string} [opts.desc] - Descripción bajo el título.
 * @param {Safe|string} [opts.actions] - Botones del encabezado (resultado de `btn`).
 * @param {Safe|string} [opts.body] - Contenido de la página.
 * @returns {Safe} HTML de la página.
 * @example
 * page({ title: 'Préstamos', desc: 'Control de préstamos.',
 *   actions: btn({ label: 'Nuevo', href: 'prestamos/nuevo', variant: 'primary' }), body });
 */
export const page = ({ title, desc = '', actions = '', body = '' }) => html`
  <header class="page-header"><div class="page-title"><h1>${title}</h1>${desc ? html`<p class="page-desc">${desc}</p>` : ''}</div>${actions ? html`<div class="page-actions">${actions}</div>` : ''}</header>
  <div id="alert" role="alert" class="notice error" tabindex="-1"></div>
  <div id="flash" role="status" class="notice success"></div>
  ${body}`;

/**
 * Marca de la aplicación (logo según el tema y nombre).
 * @returns {Safe} HTML de la marca.
 */
export const brand = () =>
  html`<div class="brand"><img src="${logoSrc()}" width="40" height="40" alt="Logo LibriGest"><span>LibriGest</span></div>`;
