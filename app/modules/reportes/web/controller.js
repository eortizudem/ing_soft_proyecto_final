/** @module modules/reportes/controller — rutas de reportes (selección de tipo y vista previa/PDF/impresión) */
import * as session from '/js/core/session.js';
import { go } from '/js/core/router.js';
import { $, toast } from '/js/core/ui.js';
import { downloadPdf } from '/js/core/pdf.js';
import { bindForm, onAction, printHtml, confirmAction } from '/js/components/index.js';
import * as model from './model.js';
import * as view from './view.js';

// Los tipos con datos personales o de circulación piden además su permiso (usuarios / prestamos).
/**
 * Tipos de reporte visibles para el usuario (según permisos extra).
 * @returns {string[]} Claves de tipo.
 */
const available = () => Object.keys(model.TYPES).filter((t) => !model.EXTRA_PERMISSION[t] || session.can(model.EXTRA_PERMISSION[t]));

/**
 * Ruta `#/reportes` (permiso `reportes`): formulario de tipo y filtros; muestra solo los filtros que aplican.
 * @param {Object} params - Parámetros de ruta (sin uso).
 * @param {Object} ctx - Contexto del router.
 * @returns {Promise<void>}
 */
async function index(params, ctx) {
  const main = ctx.render(view.indexPage(available()));
  if (!main) return;
  const form = $('#report-form', main);
  // Solo se muestran los filtros que aplican al tipo elegido (model.FILTERS).
  /**
   * Muestra solo los filtros del tipo elegido.
   * @returns {void}
   */
  const showFilters = () => {
    const applies = model.FILTERS[form.elements.tipo.value] || [];
    for (const el of Array.from(form.elements)) {
      if (el.name && el.name !== 'tipo') el.closest('.field').hidden = !applies.includes(el.name);
    }
  };
  form.elements.tipo.addEventListener('change', showFilters);
  showFilters();
  bindForm(form, { onSubmit: (values) => go(model.reportPath(values.tipo, values)) });
}

/**
 * Ruta `#/reportes/:tipo` (permiso `reportes`): vista previa con PDF, impresión y aviso (con_adeudos). Filtros en `ctx.query`.
 * @param {{tipo: string}} params - Parámetros de ruta.
 * @param {Object} ctx - Contexto del router.
 * @returns {Promise<void>}
 */
async function preview(params, ctx) {
  const { tipo } = params;
  const filters = ctx.query;
  const report = await model.fetchReport(tipo, 'pantalla', filters);
  const main = ctx.render(view.preview(report, { canNotify: session.can('prestamos') }));
  if (!main) return;
  onAction(main, {
    pdf: async () => {
      downloadPdf(model.pdfLines(await model.fetchReport(tipo, 'pdf', filters)), `LibriGest_${tipo}.pdf`);
      toast('PDF descargado.');
    },
    print: async () => printHtml(view.printable(await model.fetchReport(tipo, 'impresion', filters))),
    aviso: async () => {
      const ok = await confirmAction({
        title: 'Enviar aviso a Servicios Escolares',
        message: `Se avisará de ${report.total} alumno(s) con libros vencidos o multas pendientes.`,
        confirmLabel: 'Enviar aviso',
      });
      if (!ok) return;
      const r = await model.sendDebtorNotice(!!filters.incluir_docentes);
      toast(`Aviso enviado (${r.enviados} matrículas).`);
    },
  });
}

/**
 * Rutas del módulo: reportes y reportes/:tipo (permiso `reportes`).
 * @type {Array<Object>}
 */
export const routes = [
  { path: 'reportes', perm: 'reportes', section: 'reportes', action: index },
  { path: 'reportes/:tipo', perm: 'reportes', section: 'reportes', action: preview },
];
