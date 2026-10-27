import { $, debounce, toast, setFlash } from '/js/core/ui.js';
import { go } from '/js/core/router.js';
import * as session from '/js/core/session.js';
import { listPage, editPage } from '/js/core/crud.js';
import { onAction, bindForm, confirmAction, printHtml, money, date } from '/js/components/index.js';
import { downloadPdf } from '/js/core/pdf.js';
import * as model from './model.js';
import * as view from './view.js';

const filters = { q: '', estado: '' };

const ACTIONS = {
  renovar: (p) => ({ title: 'Renovar préstamo', message: `Se ampliará la vigencia de ${p}.`, confirmLabel: 'Renovar', variant: 'primary' }),
  devolver: (p) => ({ title: 'Registrar devolución', message: `Se registrará la devolución de ${p}.`, confirmLabel: 'Devolver', variant: 'primary' }),
};

const renewed = (r) => `Préstamo renovado. Nuevo vencimiento: ${date(r.renovacion.nueva_fecha_vencimiento)}.`;

function returned(r) {
  let text = 'Devolución registrada; el ejemplar ya está disponible.';
  if (r.adeudo) text += ` Retraso de ${r.dias_retraso} día(s) hábil(es): adeudo de ${money(r.adeudo.monto)}.`;
  if (r.espera_notificada) text += ' Se avisó al primer usuario en lista de espera.';
  return text;
}

// Renew / return buttons shared by the list rows and the detail page.
function bindLoanActions(main, refresh) {
  onAction(main, {
    renovar: async (button) => {
      if (!(await confirmAction(ACTIONS.renovar('este préstamo')))) return;
      setFlash(renewed(await model.renovar(button.dataset.id)));
      refresh();
    },
    devolver: async (button) => {
      if (!(await confirmAction(ACTIONS.devolver('este préstamo')))) return;
      setFlash(returned(await model.devolver(button.dataset.id)));
      refresh();
    },
  });
}

async function list(params, ctx) {
  const main = await listPage(ctx, {
    markup: view.listPage(filters, session.can('perfiles')),
    filters,
    load: model.list,
    render: view.rows,
    summary: view.summary,
  });
  if (main) bindLoanActions(main, () => go('prestamos'));
}

function create(params, ctx) {
  const main = ctx.render(view.form());
  if (!main) return;
  const form = $('#loan-form', main);
  const box = $('#validacion', main);
  let ticket = 0;
  const check = debounce(async () => {
    const values = { matricula: form.matricula.value, clave: form.clave.value };
    const mine = ++ticket;
    if (!values.matricula.trim() || !values.clave.trim()) {
      box.innerHTML = '';
      return;
    }
    try {
      const r = await model.validar(values);
      if (mine === ticket) box.innerHTML = String(view.validacion(r, values));
    } catch (err) {
      if (mine === ticket) box.textContent = err.message;
    }
  }, 350);
  form.matricula.addEventListener('input', check);
  form.clave.addEventListener('input', check);
  bindForm(form, {
    onSubmit: async (data) => {
      const saved = await model.crear(data);
      setFlash('Préstamo registrado. Recibo generado.');
      go('prestamos/' + saved.prestamo.id_prestamo);
    },
  });
}

async function detail(params, ctx) {
  const [loan, receipt] = await Promise.all([model.get(params.id), model.recibo(params.id)]);
  const main = ctx.render(view.detail(loan, receipt, session.can('adeudos')));
  if (!main) return;
  const refresh = () => detail(params, ctx);
  bindLoanActions(main, refresh);
  onAction(main, {
    imprimir: () => printHtml($('#recibo', main)),
    pdf: () => downloadPdf(view.receiptLines(receipt), `${receipt.folio}.pdf`),
    enviar: async (button) => {
      await model.enviarRecibo(params.id, [button.dataset.canal]);
      toast('Recibo enviado.');
      refresh();
    },
  });
}

async function policies(params, ctx) {
  const main = ctx.render(view.policiesPage(await model.politicas()));
  return main;
}

async function policy(params, ctx) {
  const current = await model.politica(params.id);
  if (!current) throw new Error('No se encontró la política.');
  editPage(ctx, {
    markup: view.policyForm(current),
    formId: 'policy-form',
    save: (data) => model.savePolitica(params.id, data),
    message: 'Política actualizada.',
    redirect: () => 'politicas',
  });
}

export const routes = [
  { path: 'prestamos', perm: 'prestamos', section: 'prestamos', action: list },
  { path: 'prestamos/nuevo', perm: 'prestamos', section: 'prestamos', action: create },
  { path: 'prestamos/:id', perm: 'prestamos', section: 'prestamos', action: detail },
  { path: 'politicas', perm: 'perfiles', section: 'perfiles', action: policies },
  { path: 'politicas/:id', perm: 'perfiles', section: 'perfiles', action: policy },
];
