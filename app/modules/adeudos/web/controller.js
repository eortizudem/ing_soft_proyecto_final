import { $, setFlash } from '/js/core/ui.js';
import { confirmAction, onAction, bindForm, printHtml, money } from '/js/components/index.js';
import { get as sessionUser } from '/js/core/session.js';
import { listPage, editPage } from '/js/core/crud.js';
import { go } from '/js/core/router.js';
import * as model from './model.js';
import * as view from './view.js';

const filters = { q: '', estado: '', tipo: '' };
const isAdmin = () => sessionUser()?.rol === 'admin';

async function list(params, ctx) {
  await listPage(ctx, {
    markup: view.listPage(filters),
    filters,
    load: model.list,
    render: (items) => view.rows(items, isAdmin()),
    summary: view.summary,
  });
}

async function detail(params, ctx) {
  const adeudo = await model.get(params.id);
  const main = ctx.render(view.detail(adeudo, isAdmin()));
  if (!main) return;
  onAction(main, {
    print: () => printHtml($('#comprobante', main)),
  });
}

async function cancelFine(params, ctx) {
  const adeudo = await model.get(params.id);
  const main = ctx.render(view.cancelFineForm(adeudo));
  if (!main) return;
  bindForm($('#cancel-fine-form', main), {
    onSubmit: async (data) => {
      const ok = await confirmAction({ title: 'Confirmar cancelación',
        message: `Se cancelará el adeudo de ${money(adeudo.monto)} de ${adeudo.usuario.nombre_completo}.`, confirmLabel: 'Sí, cancelar adeudo' });
      if (!ok) return;
      await model.cancelFine(params.id, data.motivo.trim());
      setFlash('Adeudo cancelado.');
      go('adeudos/' + params.id);
    },
  });
}

async function pay(params, ctx) {
  const adeudo = await model.get(params.id);
  editPage(ctx, {
    markup: view.payForm(adeudo),
    formId: 'pay-form',
    save: (data) => model.pay(params.id, data),
    message: 'Pago registrado.',
    redirect: (saved) => 'adeudos/' + saved.id_adeudo,
  });
}

// Loss / damage: show the computed amount, refresh it as the exchange rate or percentage change, confirm, submit.
async function incident(kind, params, ctx) {
  let preview = await model.preview(params.id);
  const main = ctx.render(view.incidentForm(preview, kind));
  if (!main) return;
  const form = $('#incident-form', main);
  const refresh = async () => {
    const field = kind === 'perdida' ? 'tipo_cambio' : 'porcentaje';
    const value = form.elements[field].value;
    try {
      preview = await model.preview(params.id, { [field]: value });
      $('#amounts', main).innerHTML = String(view.amounts(preview, kind));
    } catch { /* an invalid intermediate value keeps the last computed amount */ }
  };
  form.elements[kind === 'perdida' ? 'tipo_cambio' : 'porcentaje'].addEventListener('change', refresh);
  bindForm(form, {
    onSubmit: async (data) => {
      await refresh();
      const amount = kind === 'perdida' ? preview.reposicion.monto_mxn : preview.monto_danio;
      const ok = await confirmAction({
        title: kind === 'perdida' ? 'Confirmar pérdida' : 'Confirmar daño',
        message: `Se registrará un adeudo de ${money(amount)} para ${preview.usuario.nombre_completo}.`
          + (kind === 'perdida' ? ' El ejemplar quedará dado de baja y el préstamo cerrado.' : ''),
        confirmLabel: 'Registrar',
      });
      if (!ok) return;
      await (kind === 'perdida' ? model.reportLoss : model.reportDamage)(params.id, data);
      setFlash(kind === 'perdida' ? 'Pérdida registrada; se avisó a Servicios Escolares y Tesorería.' : 'Daño registrado.');
      go('adeudos');
    },
  });
}

export const routes = [
  { path: 'adeudos', perm: 'adeudos', section: 'adeudos', action: list },
  { path: 'adeudos/perdida/:id', perm: 'adeudos', section: 'adeudos', action: (p, c) => incident('perdida', p, c) },
  { path: 'adeudos/danio/:id', perm: 'adeudos', section: 'adeudos', action: (p, c) => incident('danio', p, c) },
  { path: 'adeudos/:id', perm: 'adeudos', section: 'adeudos', action: detail },
  { path: 'adeudos/:id/cancelar', perm: 'adeudos', roles: ['admin'], section: 'adeudos', action: cancelFine },
  { path: 'adeudos/:id/pago', perm: 'adeudos', section: 'adeudos', action: pay },
];
