import * as session from '/js/core/session.js';
import { go } from '/js/core/router.js';
import { $, toast } from '/js/core/ui.js';
import { downloadPdf } from '/js/core/pdf.js';
import { bindForm, onAction, printHtml, confirmAction } from '/js/components/index.js';
import * as model from './model.js';
import * as view from './view.js';

// Los tipos con datos personales o de circulación piden además su permiso (usuarios / prestamos).
const available = () => Object.keys(model.TYPES).filter((t) => !model.EXTRA_PERMISSION[t] || session.can(model.EXTRA_PERMISSION[t]));

async function index(params, ctx) {
  const main = ctx.render(view.indexPage(available()));
  if (!main) return;
  const form = $('#report-form', main);
  // Solo se muestran los filtros que aplican al tipo elegido (model.FILTERS).
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

export const routes = [
  { path: 'reportes', perm: 'reportes', section: 'reportes', action: index },
  { path: 'reportes/:tipo', perm: 'reportes', section: 'reportes', action: preview },
];
