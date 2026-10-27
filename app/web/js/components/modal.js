// Accessible confirm dialog with focus trap. Resolves true on confirm, false on cancel/Escape.
import { html, $, $$ } from '/js/core/ui.js';
import { btn } from './actions.js';

/** await confirmAction({ title, message, confirmLabel, variant }) -> boolean */
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
