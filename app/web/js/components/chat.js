// Generic chat panel shell (asistente, lista de consultas para el bibliotecario). No business logic: the controller supplies send().
import { html, attrs, $, showError, clearError } from '/js/core/ui.js';
import { btn } from './actions.js';
import { label } from './labels.js';

/** chatBubble({ emisor:'usuario'|'asistente', texto, extra }) -> one message; extra = markup under the text (links, cards). */
export const chatBubble = ({ emisor, texto, extra = '' }) => html`
  <div class="chat-msg ${emisor}"><span class="chat-who">${label('emisor', emisor)}</span><p>${texto}</p>${extra}</div>`;

/**
 * chatPanel({ id, messages, placeholder, sendLabel, maxlength }) -> card with a live log + input form.
 * messages: chatBubble() markup array. Wire it with bindChat(). Log is role="log" (announced politely).
 */
export const chatPanel = ({ id, messages = [], placeholder = 'Escribe tu mensaje', sendLabel = 'Enviar', maxlength = 500 }) => html`
  <section class="card chat">
    <div class="chat-log" id="${id}-log" role="log" aria-live="polite" aria-label="Conversación" tabindex="0">${messages}</div>
    <form class="chat-form" id="${id}" novalidate>
      <label class="sr-only" for="${id}-text">Mensaje</label>
      <input type="text" id="${id}-text" name="texto" autocomplete="off"${attrs({ placeholder, maxlength })} required>
      ${btn({ label: sendLabel, type: 'submit', variant: 'primary' })}
    </form></section>`;

/** Appends bubble markup to the log and scrolls to it. */
export function appendChat(panelId, markup, root = document) {
  const log = $(`#${panelId}-log`, root);
  log.insertAdjacentHTML('beforeend', String(markup));
  log.scrollTop = log.scrollHeight;
}

/** bindChat(form, { send(texto) -> Promise }) : Enter/submit sends, clears and refocuses the input, shows errors in #alert. */
export function bindChat(form, { send }) {
  const input = $('input[name="texto"]', form);
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const texto = input.value.trim();
    if (!texto) return;
    clearError();
    input.value = '';
    input.disabled = true;
    try {
      await send(texto);
    } catch (err) {
      showError(err);
    } finally {
      input.disabled = false;
      input.focus();
    }
  });
}
