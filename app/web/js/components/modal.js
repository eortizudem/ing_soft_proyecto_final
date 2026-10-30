/** @module components/modal — diálogo de confirmación accesible con trampa de foco. Resuelve true al confirmar y false al cancelar o pulsar Escape. */
import { html, $, $$ } from '/js/core/ui.js';
import { btn } from './actions.js';

/**
 * Muestra un diálogo modal de confirmación en #dialog-root y devuelve la decisión. Atrapa el foco,
 * se cierra con Escape y restaura el foco previo.
 * @param {Object} opts - Opciones.
 * @param {string} opts.title - Título del diálogo.
 * @param {string} opts.message - Mensaje.
 * @param {string} [opts.confirmLabel='Confirmar'] - Texto del botón de confirmar.
 * @param {string} [opts.variant='danger'] - Variante del botón de confirmar.
 * @returns {Promise<boolean>} true si se confirma; false si se cancela o se pulsa Escape.
 * @example if (!(await confirmAction({ title: 'Dar de baja', message: '¿Seguro?' }))) return;
 */
export function confirmAction({ title, message, confirmLabel = 'Confirmar', variant = 'danger' }) {
  const root = $('#dialog-root');
  const previous = document.activeElement;
  root.innerHTML = html`<div class="modal-overlay">
    <section role="dialog" aria-modal="true" aria-labelledby="dialog-title" class="modal" tabindex="-1">
      <h2 id="dialog-title">${title}</h2><p>${message}</p>
      <div class="actions">${btn({ label: 'Cancelar', action: 'cancel' })}${btn({ label: confirmLabel, action: 'ok', variant })}</div>
    </section></div>`;
  const dialog = $('.modal', root);
  dialog.focus();
  return new Promise((resolve) => {
    const close = (result) => {
      document.removeEventListener('keydown', onKey, true);
      root.innerHTML = '';
      if (previous?.isConnected) previous.focus();
      resolve(result);
    };
    const onKey = (event) => {
      if (event.key === 'Escape') return close(false);
      if (event.key !== 'Tab') return;
      const items = $$('button,[href],input,select,textarea', dialog);
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && (document.activeElement === first || document.activeElement === dialog)) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener('keydown', onKey, true);
    root.onclick = (event) => {
      const action = event.target.closest('[data-action]')?.dataset.action;
      if (action) close(action === 'ok');
    };
  });
}
