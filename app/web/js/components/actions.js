// Buttons, links and action handling shared by every view/controller.
import { html, attrs, raw, $, showError, clearError } from '/js/core/ui.js';

/**
 * btn({ label, href|action|type, variant, id, data, attrs, when })
 *  - href: hash route without "#/" -> <a class="btn">; action -> <button data-action>; type:'submit' -> submit button
 *  - variant: 'primary' | 'danger' | 'link' | 'active' (space separated)
 *  - when: false renders nothing (permission checks)
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

export const backLink = (href, label = 'Volver') => btn({ label, href, variant: 'link' });

/** actions([btn...], { spread }) -> <div class="actions"> (empty items are skipped). */
export const actions = (items, { spread = false, cls = '' } = {}) =>
  html`<div class="actions ${spread ? 'spread' : ''} ${cls}">${items}</div>`;

/** Wires [data-action] clicks with delegation; shows server errors and disables the button while running. */
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
 * Prints an HTML fragment (markup string or a DOM element, e.g. the receiptBlock section) through the
 * #print-root container. Receipts keep their `.receipt` wrapper so the print CSS styles them uniformly.
 */
export function printHtml(content) {
  $('#print-root').innerHTML = content instanceof Element ? content.outerHTML : String(content);
  window.print();
}

