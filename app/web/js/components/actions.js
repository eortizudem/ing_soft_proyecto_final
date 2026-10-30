/** @module components/actions — botones, enlaces y manejo de acciones compartidos por todas las vistas y controladores. */
import { html, attrs, raw, $, showError, clearError } from '/js/core/ui.js';

/**
 * Botón o enlace con estilo `.btn`. `href` genera un <a> a la ruta hash; `action` un <button data-action>;
 * `type: 'submit'` un botón de envío.
 * @param {Object} opts - Opciones.
 * @param {string} opts.label - Texto visible.
 * @param {string} [opts.href] - Ruta hash sin "#/" (genera <a>).
 * @param {string} [opts.action] - Valor de `data-action` (genera <button>; ver `onAction`).
 * @param {string} [opts.type] - Tipo del botón (por defecto 'button').
 * @param {string} [opts.variant] - Clases separadas por espacio: 'primary' | 'danger' | 'link' | 'active'.
 * @param {string} [opts.id] - Atributo id del botón.
 * @param {Object<string,any>} [opts.data] - Atributos `data-*` extra (`{id: 1}` -> `data-id="1"`).
 * @param {boolean} [opts.current] - Si es true y hay `href`, añade `aria-current="page"`.
 * @param {boolean} [opts.disabled] - Deshabilita el botón.
 * @param {boolean} [opts.when=true] - Si es `false` no renderiza nada (comprobación de permisos).
 * @returns {Safe|string} HTML del botón, o cadena vacía si `when` es false.
 * @example
 * btn({ label: 'Nuevo', href: 'prestamos/nuevo', variant: 'primary', when: can('prestamos') });
 * btn({ label: 'Devolver', action: 'devolver', data: { id: 7 } });
 */
export function btn({ label, href, action, type, variant = '', id, data = {}, current, disabled, when = true }) {
  if (when === false) return '';
  const cls = `btn ${variant}`.trim();
  if (href !== undefined) {
    return html`<a class="${cls}" href="#/${href}"${current ? raw(' aria-current="page"') : ''}>${label}</a>`;
  }
  const dataAttrs = Object.fromEntries(Object.entries(data).map(([k, v]) => [`data-${k}`, v]));
  return html`<button type="${type || 'button'}" class="${cls}"${attrs({ id, 'data-action': action, disabled, ...dataAttrs })}>${label}</button>`;
}

/**
 * Enlace tipo botón «link» para volver a una ruta.
 * @param {string} href - Ruta hash sin "#/".
 * @param {string} [label='Volver'] - Texto.
 * @returns {Safe} HTML del enlace.
 */
export const backLink = (href, label = 'Volver') => btn({ label, href, variant: 'link' });

/**
 * Barra de acciones `<div class="actions">`; los elementos vacíos se omiten.
 * @param {Array<Safe|string>} items - Botones (resultado de `btn`).
 * @param {Object} [opts] - Opciones.
 * @param {boolean} [opts.spread=false] - Reparte los botones a lo ancho (clase `spread`).
 * @param {string} [opts.cls] - Clases CSS adicionales.
 * @returns {Safe} HTML de la barra.
 * @example actions([btn({ label: 'Editar', href: 'libros/1/editar' }), backLink('libros')])
 */
export const actions = (items, { spread = false, cls = '' } = {}) =>
  html`<div class="actions ${spread ? 'spread' : ''} ${cls}">${items}</div>`;

/**
 * Enlaza los clics en [data-action] por delegación; muestra los errores del servidor y deshabilita el
 * botón mientras el manejador se ejecuta.
 * @param {HTMLElement} root - Contenedor sobre el que se delega.
 * @param {Object<string, function(HTMLElement, Event): any>} handlers - Manejadores por valor de `data-action`
 *   (pueden ser asíncronos; reciben el botón y el evento).
 * @returns {void}
 * @example onAction(main, { devolver: async (button) => { await api.post(`/prestamos/${button.dataset.id}/devolver`); } });
 */
export function onAction(root, handlers) {
  root.addEventListener('click', async (event) => {
    const button = event.target.closest('[data-action]');
    const handler = button && handlers[button.dataset.action];
    if (!handler || !root.contains(button)) return;
    clearError();
    button.disabled = true;
    try {
      await handler(button, event);
    } catch (err) {
      showError(err);
    } finally {
      if (button.isConnected) button.disabled = false;
    }
  });
}

/**
 * Imprime un fragmento HTML (cadena de marcado o elemento DOM, p. ej. la sección de `receiptBlock`)
 * a través del contenedor #print-root. Los comprobantes conservan su envoltorio `.receipt` para que el
 * CSS de impresión los estilice de forma uniforme.
 * @param {string|Safe|Element} content - Marcado o elemento a imprimir.
 * @returns {void}
 */
export function printHtml(content) {
  $('#print-root').innerHTML = content instanceof Element ? content.outerHTML : String(content);
  window.print();
}

