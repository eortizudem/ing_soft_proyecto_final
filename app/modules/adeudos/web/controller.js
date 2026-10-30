/**
 * @module modules/adeudos/controller — rutas y manejadores de adeudos, pago, cancelación, pérdida y daño (capa controller; une model y view).
 */
import { $, setFlash } from '/js/core/ui.js';
import { confirmAction, onAction, bindForm, printHtml, money } from '/js/components/index.js';
import { get as sessionUser } from '/js/core/session.js';
import { listPage, editPage } from '/js/core/crud.js';
import { go } from '/js/core/router.js';
import * as model from './model.js';
import * as view from './view.js';

/**
 * Estado de filtros del listado (se conserva entre renderizados).
 * @type {{q: string, estado: string, tipo: string}}
 */
const filters = { q: '', estado: '', tipo: '' };
/**
 * Indica si el usuario en sesión es administrador.
 * @returns {boolean}
 */
const isAdmin = () => sessionUser()?.rol === 'admin';

/**
 * Ruta `adeudos`: listado con filtros; muestra la acción de cancelar solo al admin.
 * @param {Object} params - Parámetros de ruta (sin uso).
 * @param {Object} ctx - Contexto del router.
 * @returns {Promise<void>}
 */
async function list(params, ctx) {
  await listPage(ctx, {
    markup: view.listPage(filters),
    filters,
    load: model.list,
    render: (items) => view.rows(items, isAdmin()),
    summary: view.summary,
  });
}

/**
 * Ruta `adeudos/:id`: detalle del adeudo y comprobante imprimible si está pagado.
 * @param {{id: string}} params - Parámetros de ruta.
 * @param {Object} ctx - Contexto del router.
 * @returns {Promise<void>}
 */
async function detail(params, ctx) {
  const adeudo = await model.get(params.id);
  const main = ctx.render(view.detail(adeudo, isAdmin()));
  if (!main) return;
  onAction(main, {
    print: () => printHtml($('#comprobante', main)),
  });
}

/**
 * Ruta `adeudos/:id/cancelar` (solo admin): formulario de motivo con confirmación.
 * @param {{id: string}} params - Parámetros de ruta.
 * @param {Object} ctx - Contexto del router.
 * @returns {Promise<void>}
 */
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

/**
 * Ruta `adeudos/:id/pago`: formulario de pago con referencia de Tesorería.
 * @param {{id: string}} params - Parámetros de ruta.
 * @param {Object} ctx - Contexto del router.
 * @returns {Promise<void>}
 */
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
/**
 * Rutas de pérdida y daño: muestra el monto calculado, lo recalcula al cambiar el tipo de cambio o el porcentaje, confirma y registra.
 * @param {'perdida'|'danio'} kind - Tipo de incidente.
 * @param {{id: string}} params - Parámetros de ruta (id del préstamo).
 * @param {Object} ctx - Contexto del router.
 * @returns {Promise<void>}
 */
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

/**
 * Rutas del módulo (hash `#/<path>`), todas con permiso `adeudos`.
 * - `adeudos`: listado.
 * - `adeudos/perdida/:id`: reportar pérdida del préstamo.
 * - `adeudos/danio/:id`: reportar daño del préstamo.
 * - `adeudos/:id`: detalle.
 * - `adeudos/:id/cancelar`: cancelar (solo rol `admin`).
 * - `adeudos/:id/pago`: registrar pago.
 * @type {Array<{path: string, perm: string, roles?: Array<string>, section: string, action: function}>}
 */
export const routes = [
  { path: 'adeudos', perm: 'adeudos', section: 'adeudos', action: list },
  { path: 'adeudos/perdida/:id', perm: 'adeudos', section: 'adeudos', action: (p, c) => incident('perdida', p, c) },
  { path: 'adeudos/danio/:id', perm: 'adeudos', section: 'adeudos', action: (p, c) => incident('danio', p, c) },
  { path: 'adeudos/:id', perm: 'adeudos', section: 'adeudos', action: detail },
  { path: 'adeudos/:id/cancelar', perm: 'adeudos', roles: ['admin'], section: 'adeudos', action: cancelFine },
  { path: 'adeudos/:id/pago', perm: 'adeudos', section: 'adeudos', action: pay },
];
