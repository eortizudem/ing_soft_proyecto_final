/** @module modules/asistente/controller — rutas del asistente: chat (web y móvil), consultas del bibliotecario y detalle/resolución. */
import { $, setFlash, toast } from '/js/core/ui.js';
import { go } from '/js/core/router.js';
import { can } from '/js/core/session.js';
import { appendChat, bindChat, bindForm, onAction } from '/js/components/index.js';
import { listPage } from '/js/core/crud.js';
import * as model from './model.js';
import * as view from './view.js';

/**
 * Estado del módulo: id de la conversación activa (en memoria; se recarga por GET).
 * @type {{id: number|null}}
 */
const state = { id: null };          // conversacion activa (en memoria; se recarga por GET)
/**
 * Filtros de la lista de consultas (por defecto, solo pendientes).
 * @type {{estado: string}}
 */
const filters = { estado: 'pendiente' };

/**
 * Carga los mensajes de la conversación activa; si expiró o es ajena, reinicia el estado.
 * @returns {Promise<Array<{emisor: string, texto: string}>>} mensajes (vacío si no hay conversación).
 */
async function history() {
  if (!state.id) return [];
  try {
    return (await model.get(state.id)).mensajes;
  } catch {
    state.id = null;                 // expirada o ajena: empezar de nuevo
    return [];
  }
}

/**
 * Ruta del chat (escritorio o móvil): pinta el historial, envía mensajes, atiende las sugerencias y guarda la opinión.
 * @param {object} params - parámetros de ruta (sin uso).
 * @param {{render: Function, mobile?: boolean}} ctx - contexto del router; `mobile` activa la versión móvil y el canal `movil`.
 * @returns {Promise<void>}
 */
async function chat(params, ctx) {
  const mobile = !!ctx.mobile;
  const messages = await history();
  const main = ctx.render(view.chatPage({ suggestions: model.SUGGESTIONS, staff: can('prestamos'), mobile, messages }));
  if (!main) return;
  const form = $('#chat', main);
  /** Envía un mensaje, pinta la burbuja del usuario y la respuesta, y recuerda la conversación. @param {string} texto - mensaje. @returns {Promise<void>} */
  const send = async (texto) => {
    appendChat('chat', view.bubble({ texto }, 'usuario'), main);
    const r = await model.send(texto, state.id, mobile ? 'movil' : 'web');
    state.id = r.id_conversacion;
    appendChat('chat', view.bubble(r.respuesta, 'asistente'), main);
  };
  bindChat(form, { send });
  onAction(main, { chip: (button) => send(button.dataset.texto) });
  bindForm($('#rate-form', main), {
    onSubmit: async (data) => {
      if (!state.id) throw new Error('Envía al menos un mensaje antes de responder.');
      await model.rate(state.id, data.calificacion, data.resuelta);
      toast('¡Gracias por tu opinión!');
    },
  });
}

/**
 * Ruta de la lista de consultas escaladas (filtro por estado).
 * @param {object} params - parámetros de ruta (sin uso).
 * @param {object} ctx - contexto del router.
 * @returns {Promise<void>}
 */
const listConsultas = (params, ctx) => listPage(ctx, {
  markup: view.consultasPage(filters), filters, load: model.consultas, render: view.consultaRows,
  summary: (items) => `${items.length} consulta(s)`,
});

/**
 * Ruta de detalle de una consulta; si está pendiente permite responderla y marcarla atendida.
 * @param {{id: string}} params - parámetros de ruta (`id` de la conversación).
 * @param {{render: Function}} ctx - contexto del router.
 * @returns {Promise<void>}
 */
async function consulta(params, ctx) {
  const main = ctx.render(view.consultaDetail(await model.get(params.id)));
  if (!main) return;
  const form = $('#resolve-form', main);
  if (form) {
    bindForm(form, {
      onSubmit: async (data) => {
        await model.resolve(params.id, data.respuesta);
        setFlash('Consulta atendida.');
        go('asistente/consultas');
      },
    });
  }
}

/**
 * Rutas del módulo.
 * - `#/asistente` (permiso `asistente`): chat web.
 * - `#/movil/asistente` (permiso `asistente`, sin marco): chat móvil.
 * - `#/asistente/consultas` (permiso `prestamos`): consultas del bibliotecario.
 * - `#/asistente/consultas/:id` (permiso `prestamos`): detalle y resolución.
 * @type {Array<{path: string, perm: string, action: Function}>}
 */
export const routes = [
  { path: 'asistente', perm: 'asistente', section: 'asistente', action: chat },
  { path: 'movil/asistente', perm: 'asistente', bare: true, action: (p, ctx) => chat(p, Object.assign(ctx, { mobile: true })) },
  { path: 'asistente/consultas', perm: 'prestamos', section: 'asistente', action: listConsultas },
  { path: 'asistente/consultas/:id', perm: 'prestamos', section: 'asistente', action: consulta },
];
