/** @module components/chat — estructura genérica de panel de chat (asistente, consultas del bibliotecario). Sin lógica de negocio: el controlador aporta `send()`. */
import { html, attrs, $, showError, clearError } from '/js/core/ui.js';
import { btn } from './actions.js';
import { label } from './labels.js';

/**
 * Un mensaje del chat.
 * @param {Object} opts - Opciones.
 * @param {string} opts.emisor - 'usuario' | 'asistente'.
 * @param {string} opts.texto - Texto del mensaje (se escapa).
 * @param {Safe|string} [opts.extra] - Marcado bajo el texto (enlaces, tarjetas).
 * @returns {Safe} HTML del mensaje.
 */
export const chatBubble = ({ emisor, texto, extra = '' }) => html`
  <div class="chat-msg ${emisor}"><span class="chat-who">${label('emisor', emisor)}</span><p>${texto}</p>${extra}</div>`;

/**
 * Tarjeta de chat con registro en vivo (`role="log"`, anunciado de forma educada) y formulario de entrada.
 * Se enlaza con `bindChat()`; el registro tiene id `${id}-log` y el formulario `${id}`.
 * @param {Object} opts - Opciones.
 * @param {string} opts.id - Id del formulario (prefijo de los demás ids).
 * @param {Array<Safe>} [opts.messages] - Mensajes iniciales (resultado de `chatBubble`).
 * @param {string} [opts.placeholder='Escribe tu mensaje'] - Placeholder del campo.
 * @param {string} [opts.sendLabel='Enviar'] - Texto del botón.
 * @param {number} [opts.maxlength=500] - Longitud máxima del mensaje.
 * @returns {Safe} HTML del panel.
 * @example
 * chatPanel({ id: 'chat', messages: [chatBubble({ emisor: 'asistente', texto: 'Hola' })] });
 * bindChat($('#chat'), { send: async (texto) => { ... } });
 */
export const chatPanel = ({ id, messages = [], placeholder = 'Escribe tu mensaje', sendLabel = 'Enviar', maxlength = 500 }) => html`
  <section class="card chat">
    <div class="chat-log" id="${id}-log" role="log" aria-live="polite" aria-label="Conversación" tabindex="0">${messages}</div>
    <form class="chat-form" id="${id}" novalidate>
      <label class="sr-only" for="${id}-text">Mensaje</label>
      <input type="text" id="${id}-text" name="texto" autocomplete="off"${attrs({ placeholder, maxlength })} required>
      ${btn({ label: sendLabel, type: 'submit', variant: 'primary' })}
    </form></section>`;

/**
 * Añade marcado de mensaje al registro y desplaza hasta el final.
 * @param {string} panelId - Id del panel (el mismo que en `chatPanel`).
 * @param {Safe|string} markup - Mensaje(s) a añadir.
 * @param {ParentNode} [root=document] - Raíz de búsqueda.
 * @returns {void}
 */
export function appendChat(panelId, markup, root = document) {
  const log = $(`#${panelId}-log`, root);
  log.insertAdjacentHTML('beforeend', String(markup));
  log.scrollTop = log.scrollHeight;
}

/**
 * Enlaza el formulario del chat: al enviar vacía y deshabilita el campo, llama a `send`, vuelve a
 * enfocar y muestra los errores en #alert.
 * @param {HTMLFormElement} form - Formulario de `chatPanel`.
 * @param {Object} opts - Opciones.
 * @param {function(string): Promise<any>} opts.send - Recibe el texto recortado (no se llama si está vacío).
 * @returns {void}
 */
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
