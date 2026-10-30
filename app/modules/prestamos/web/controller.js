/**
 * @module modules/prestamos/controller — rutas y manejadores de préstamos, recibo y políticas (capa controller; une model y view).
 */
import { $, debounce, toast, setFlash } from '/js/core/ui.js';
import { go } from '/js/core/router.js';
import * as session from '/js/core/session.js';
import { listPage, editPage } from '/js/core/crud.js';
import { onAction, bindForm, confirmAction, printHtml, money, date } from '/js/components/index.js';
import { downloadPdf } from '/js/core/pdf.js';
import * as model from './model.js';
import * as view from './view.js';

/**
 * Estado de filtros del listado (se conserva entre renderizados).
 * @type {{q: string, estado: string}}
 */
const filters = { q: '', estado: '' };

/**
 * Configuración del diálogo de confirmación por acción de préstamo.
 * @type {Object<string, function(string): Object>} Recibe el nombre del préstamo y devuelve las opciones de `confirmAction`.
 */
const ACTIONS = {
  renovar: (p) => ({ title: 'Renovar préstamo', message: `Se ampliará la vigencia de ${p}.`, confirmLabel: 'Renovar', variant: 'primary' }),
  devolver: (p) => ({ title: 'Registrar devolución', message: `Se registrará la devolución de ${p}.`, confirmLabel: 'Devolver', variant: 'primary' }),
};

/**
 * Mensaje flash tras renovar.
 * @param {Object} r - Respuesta de `model.renovar`.
 * @param {{nueva_fecha_vencimiento: string}} r.renovacion - Nuevo vencimiento.
 * @returns {string} Mensaje.
 */
const renewed = (r) => `Préstamo renovado. Nuevo vencimiento: ${date(r.renovacion.nueva_fecha_vencimiento)}.`;

/**
 * Mensaje flash tras devolver (incluye adeudo por retraso y aviso a la lista de espera).
 * @param {Object} r - Respuesta de `model.devolver`.
 * @param {?Object} r.adeudo - Adeudo generado, si hubo retraso.
 * @param {number} r.dias_retraso - Días hábiles de retraso.
 * @param {?Object} r.espera_notificada - Entrada de espera notificada, si hubo.
 * @returns {string} Mensaje.
 */
function returned(r) {
  let text = 'Devolución registrada; el ejemplar ya está disponible.';
  if (r.adeudo) text += ` Retraso de ${r.dias_retraso} día(s) hábil(es): adeudo de ${money(r.adeudo.monto)}.`;
  if (r.espera_notificada) text += ' Se avisó al primer usuario en lista de espera.';
  return text;
}

// Renew / return buttons shared by the list rows and the detail page.
/**
 * Enlaza los botones Renovar/Devolver (compartidos por el listado y el detalle) con confirmación.
 * @param {HTMLElement} main - Contenedor de la página.
 * @param {function(): void} refresh - Recarga la vista tras la acción.
 * @returns {void}
 */
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

/**
 * Ruta `prestamos`: listado con búsqueda y filtro de estado.
 * @param {Object} params - Parámetros de ruta (sin uso).
 * @param {Object} ctx - Contexto del router.
 * @returns {Promise<void>}
 */
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

/**
 * Ruta `prestamos/nuevo`: formulario con validación RN-01 en vivo (debounce 350 ms) y alta del préstamo.
 * @param {Object} params - Parámetros de ruta (sin uso).
 * @param {Object} ctx - Contexto del router.
 * @returns {void}
 */
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

/**
 * Ruta `prestamos/:id`: detalle, acciones y recibo (imprimir, PDF, enviar por canal).
 * @param {{id: string}} params - Parámetros de ruta.
 * @param {Object} ctx - Contexto del router.
 * @returns {Promise<void>}
 */
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

/**
 * Ruta `politicas`: tabla de políticas de préstamo.
 * @param {Object} params - Parámetros de ruta (sin uso).
 * @param {Object} ctx - Contexto del router.
 * @returns {Promise<?HTMLElement>} El <main> o null si la ruta quedó obsoleta.
 */
async function policies(params, ctx) {
  const main = ctx.render(view.policiesPage(await model.politicas()));
  return main;
}

/**
 * Ruta `politicas/:id`: formulario de edición de una política.
 * @param {{id: string}} params - Parámetros de ruta.
 * @param {Object} ctx - Contexto del router.
 * @returns {Promise<void>}
 * @throws {Error} Si la política no existe.
 */
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

/**
 * Rutas del módulo (hash `#/<path>`).
 * - `prestamos` (permiso `prestamos`): listado.
 * - `prestamos/nuevo` (permiso `prestamos`): nuevo préstamo.
 * - `prestamos/:id` (permiso `prestamos`): detalle y recibo.
 * - `politicas` (permiso `perfiles`): lista de políticas.
 * - `politicas/:id` (permiso `perfiles`): editar política.
 * @type {Array<{path: string, perm: string, section: string, action: function}>}
 */
export const routes = [
  { path: 'prestamos', perm: 'prestamos', section: 'prestamos', action: list },
  { path: 'prestamos/nuevo', perm: 'prestamos', section: 'prestamos', action: create },
  { path: 'prestamos/:id', perm: 'prestamos', section: 'prestamos', action: detail },
  { path: 'politicas', perm: 'perfiles', section: 'perfiles', action: policies },
  { path: 'politicas/:id', perm: 'perfiles', section: 'perfiles', action: policy },
];
