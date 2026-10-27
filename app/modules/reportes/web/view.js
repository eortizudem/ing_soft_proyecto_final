import { html } from '/js/core/ui.js';
import { page, btn, actions, formView, submitButton, card, dataTable, datetime, notice } from '/js/components/index.js';
import { TYPES } from './model.js';

export const indexPage = (types) => page({
  title: 'Reportes',
  desc: 'Consulta el listado y prepara su salida a PDF o impresión.',
  body: formView({
    id: 'report-form',
    fields: [
      { name: 'tipo', label: 'Tipo de reporte', type: 'select', options: types.map((t) => [t, TYPES[t]]), span: 'wide' },
      { name: 'planta', label: 'Planta', hint: 'Ej. Planta baja', maxlength: 20 },
      { name: 'pasillo', label: 'Pasillo', hint: 'Una letra', maxlength: 1 },
      { name: 'librero', label: 'Librero', hint: 'Ej. 03', maxlength: 2 },
      { name: 'tema', label: 'Tema', maxlength: 60 },
      { name: 'desde', label: 'Desde', type: 'date' },
      { name: 'hasta', label: 'Hasta', type: 'date' },
      { name: 'incluir_docentes', label: 'Incluir docentes', type: 'checkbox', },
    ],
    actions: [submitButton('Generar listado')],
  }),
});

export const reportTable = (r) => dataTable({
  columns: r.columnas.map((label, i) => ({ label, render: (row) => row[i] })),
  rows: r.filas,
  empty: { text: 'El listado no tiene registros.' },
});

export const preview = (r, { canNotify = false } = {}) => page({
  title: 'Vista previa del listado',
  desc: `Biblioteca Ducky · ${TYPES[r.tipo] || r.tipo} · ${r.total} registros`,
  body: html`${card({
    cls: 'report-preview', title: `LIBRIGEST / ${(TYPES[r.tipo] || r.tipo).toUpperCase()}`,
    body: html`<p class="muted">Total: ${r.total} registros · ${datetime(r.generado)} · ${r.generado_por}</p>${reportTable(r)}`,
  })}
  ${r.tipo === 'con_adeudos' && canNotify ? notice({ text: 'Épocas de exámenes: el aviso a Servicios Escolares se registra en la lista de avisos.' }) : ''}
  ${actions([btn({ label: 'Descargar PDF', action: 'pdf', variant: 'primary' }), btn({ label: 'Imprimir', action: 'print' }),
    btn({ label: 'Enviar aviso a Servicios Escolares', action: 'aviso', when: r.tipo === 'con_adeudos' && canNotify }),
    btn({ label: 'Volver a reportes', href: 'reportes' })])}`,
});

export const printable = (r) => html`<h1>LibriGest · ${TYPES[r.tipo] || r.tipo}</h1>
  <p>Universidad Ducky · ${datetime(r.generado)} · ${r.total} registros</p>${reportTable(r)}`;
