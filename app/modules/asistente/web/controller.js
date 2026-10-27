import { $, setFlash, toast } from '/js/core/ui.js';
import { go } from '/js/core/router.js';
import { can } from '/js/core/session.js';
import { appendChat, bindChat, bindForm, onAction } from '/js/components/index.js';
import { listPage } from '/js/core/crud.js';
import * as model from './model.js';
import * as view from './view.js';

const state = { id: null };          // conversacion activa (en memoria; se recarga por GET)
const filters = { estado: 'pendiente' };

async function history() {
  if (!state.id) return [];
  try {
    return (await model.get(state.id)).mensajes;
  } catch {
    state.id = null;                 // expirada o ajena: empezar de nuevo
    return [];
  }
}

async function chat(params, ctx) {
  const mobile = !!ctx.mobile;
  const messages = await history();
  const main = ctx.render(view.chatPage({ suggestions: model.SUGGESTIONS, staff: can('prestamos'), mobile, messages }));
  if (!main) return;
  const form = $('#chat', main);
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

const listConsultas = (params, ctx) => listPage(ctx, {
  markup: view.consultasPage(filters), filters, load: model.consultas, render: view.consultaRows,
  summary: (items) => `${items.length} consulta(s)`,
});

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

export const routes = [
  { path: 'asistente', perm: 'asistente', section: 'asistente', action: chat },
  { path: 'movil/asistente', perm: 'asistente', bare: true, action: (p, ctx) => chat(p, Object.assign(ctx, { mobile: true })) },
  { path: 'asistente/consultas', perm: 'prestamos', section: 'asistente', action: listConsultas },
  { path: 'asistente/consultas/:id', perm: 'prestamos', section: 'asistente', action: consulta },
];
