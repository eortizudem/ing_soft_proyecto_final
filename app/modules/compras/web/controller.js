import * as session from '/js/core/session.js';
import { go } from '/js/core/router.js';
import { $, $$, setFlash } from '/js/core/ui.js';
import { bindForm, onAction, printHtml, confirmAction } from '/js/components/index.js';
import * as model from './model.js';
import * as view from './view.js';

let draft = null; // request being edited/reviewed, kept between form and review pages

async function list(params, ctx) {
  ctx.render(view.listPage(await model.list(), await model.budget()));
}

// Reads the lines currently in the form.
const readLines = (form) => $$('.purchase-line', form).map((row) => ({
  descripcion: $('[name="descripcion"]', row).value,
  cantidad: Number($('[name="cantidad"]', row).value),
  precio_unitario: Number($('[name="precio_unitario"]', row).value),
}));

async function newRequest(params, ctx) {
  const titles = await model.bookTitles();
  draft = draft && !draft.id ? draft : { justificacion: '', detalles: [model.emptyLine(), model.emptyLine()] };
  const main = ctx.render(view.form(draft, titles, await model.budget()));
  if (!main) return;
  const form = $('#purchase-form', main);
  const lines = $('#lines', main);
  const refresh = () => {
    $('#total', main).textContent = view.totalText(readLines(form));
    $$('[data-action="remove-line"]', main).forEach((b) => { b.disabled = lines.children.length === 1; });
    // Unique ids so every label points to its own input.
    $$('.purchase-line', main).forEach((row, n) => $$('input', row).forEach((input) => {
      input.id = `${input.name}-${n}`;
      input.previousElementSibling.htmlFor = input.id;
    }));
  };
  form.addEventListener('input', refresh);
  onAction(form, {
    'add-line': () => { lines.insertAdjacentHTML('beforeend', view.lineHtml()); refresh(); },
    'remove-line': (button) => { button.closest('.purchase-line').remove(); refresh(); },
  });
  refresh();
  // Atajos de 3 clics (D-17): "Guardar solicitud" la deja pendiente; "Guardar y enviar" la envía a Tesorería.
  // Sin atajo, el envío pasa por la pantalla de revisión (4 clics).
  let mode = 'review';
  const shortcut = (m) => () => { mode = m; form.requestSubmit(); };
  onAction(form, { save: shortcut('save'), 'save-send': shortcut('send') });
  bindForm(form, { onSubmit: async (data) => {
    const chosen = mode;
    mode = 'review';
    draft = model.validate({ justificacion: data.justificacion, detalles: readLines(form) });
    if (chosen === 'review') return go('compras/revisar');
    const saved = chosen === 'send' ? await model.createAndSend(draft) : await model.create(draft);
    draft = null;
    setFlash(chosen === 'send' ? 'Solicitud enviada a Tesorería.' : 'Solicitud guardada. Puedes enviarla a Tesorería desde la lista o el comprobante.');
    go('compras/' + saved.id_solicitud);
  } });
}

async function review(params, ctx) {
  if (!draft) return go('compras/nueva');
  const main = ctx.render(view.review(draft));
  if (!main) return;
  onAction(main, {
    edit: () => go('compras/nueva'),
    confirm: async () => {
      const sent = await model.createAndSend(draft);
      draft = null;
      setFlash('Solicitud enviada a Tesorería.');
      go('compras/' + sent.id_solicitud);
    },
  });
}

async function show(params, ctx) {
  const request = await model.get(params.id);
  const main = ctx.render(view.receipt(request, {
    canSend: session.can('compras'), canReceive: session.can('compras') && model.canReceive(request),
    canCancel: session.can('compras') && model.canCancel(request) }));
  if (!main) return;
  onAction(main, {
    cancel: async () => {
      if (!await confirmAction({ title: 'Cancelar solicitud', confirmLabel: 'Cancelar solicitud',
        message: `¿Cancelar la solicitud ${request.folio}? Se libera su importe del presupuesto del mes.` })) return;
      await model.cancel(request.id_solicitud);
      setFlash('Solicitud cancelada.');
      await show(params, ctx);
    },
    print: () => printHtml($('#receipt', main)),
    send: async () => {
      await model.send(request.id_solicitud);
      setFlash('Solicitud enviada a Tesorería.');
      await show(params, ctx);
    },
  });
}

async function receive(params, ctx) {
  const request = await model.get(params.id);
  if (!model.canReceive(request)) { setFlash('Solo se puede recibir el pedido de solicitudes enviadas con títulos pendientes.'); return go('compras/' + params.id); }
  const main = ctx.render(view.reception(request));
  if (!main) return;
  bindForm($('#reception-form', main), { onSubmit: async (data) => {
    const done = await model.receive(request.id_solicitud, model.receptionPayload(data, request));
    const extra = done.pendientes_catalogar.length ? ` ${done.pendientes_catalogar.length} título(s) pendientes de catalogar.` : '';
    setFlash(`Pedido recibido${done.estado === 'recibida' ? ' (solicitud completa)' : ' (parcial)'}; aviso enviado a Tesorería.${extra}`);
    go('compras/' + request.id_solicitud);
  } });
}

export const routes = [
  { path: 'compras', perm: 'compras', section: 'compras', action: list },
  { path: 'compras/nueva', perm: 'compras', section: 'compras', action: newRequest },
  { path: 'compras/revisar', perm: 'compras', section: 'compras', action: review },
  { path: 'compras/:id/recibir', perm: 'compras', section: 'compras', action: receive },
  { path: 'compras/:id', perm: 'compras', section: 'compras', action: show },
];
