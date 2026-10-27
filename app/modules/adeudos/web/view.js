// Adeudos HTML (pure functions: data -> components).
import { html } from '/js/core/ui.js';
import { LIST_LIMIT } from '/js/core/api.js';
import { page, btn, toolbar, resultsPanel, dataTable, statusBadge, formView, submitButton, detailView, receiptBlock,
  notice, labelItems, label, money, date, today, count } from '/js/components/index.js';

const who = (a) => html`${a.usuario.nombre_completo} (${a.usuario.matricula})`;

export const listPage = (filters) => page({
  title: 'Multas y pagos',
  desc: 'Adeudos por retraso, daño o pérdida. El pago se registra con la referencia de Tesorería.',
  body: html`
  ${toolbar({
    search: { name: 'q', label: 'Buscar usuario o libro', value: filters.q, placeholder: 'Matrícula, nombre o libro' },
    filters: [
      { name: 'estado', label: 'Estado', value: filters.estado, options: [['', 'Todos los estados'], ...labelItems('adeudo')] },
      { name: 'tipo', label: 'Tipo', value: filters.tipo, options: [['', 'Todos los tipos'], ...labelItems('adeudoTipo')] },
    ],
  })}
  ${resultsPanel()}`,
});

export const summary = (items) => {
  const pending = items.filter((a) => a.estado === 'pendiente').reduce((sum, a) => sum + a.monto, 0);
  return count(items.length, undefined, LIST_LIMIT) + ` · ${money(pending)} pendientes`;
};

export const rows = (items, isAdmin) => dataTable({
  rows: items,
  empty: { text: 'No hay adeudos con esos filtros.' },
  columns: [
    { label: 'Usuario', render: who },
    { label: 'Libro', render: (a) => a.libro.titulo },
    { label: 'Tipo', render: (a) => label('adeudoTipo', a.tipo) },
    { label: 'Monto (MXN)', align: 'right', render: (a) => money(a.monto) },
    { label: 'Estado', render: (a) => statusBadge('adeudo', a.estado) },
    { label: 'Acciones', render: (a) => html`<div class="row-actions">${btn({ label: 'Ver', href: 'adeudos/' + a.id_adeudo })}
      ${btn({ label: 'Registrar pago', href: `adeudos/${a.id_adeudo}/pago`, when: a.estado === 'pendiente' })}
      ${btn({ label: 'Cancelar adeudo', href: `adeudos/${a.id_adeudo}/cancelar`, when: isAdmin && a.estado === 'pendiente' })}</div>` },
  ],
});

const payInfo = (a) => [
  ['Usuario', who(a)], ['Libro', `${a.libro.clave} · ${a.libro.titulo}`], ['Tipo', label('adeudoTipo', a.tipo)],
  ['Días de retraso', a.dias_retraso], ['Monto', money(a.monto)],
];

export const detail = (a, isAdmin) => page({
  title: `Adeudo ${a.id_adeudo}`,
  desc: 'Situación del adeudo y, si ya se cobró, su comprobante.',
  body: html`${detailView({
    title: who(a),
    sub: `${label('adeudoTipo', a.tipo)} · Préstamo ${a.id_prestamo}`,
    badge: statusBadge('adeudo', a.estado),
    items: [...payInfo(a).slice(1),
      ['Fecha de pago', date(a.fecha_pago) || '—'],
      ['Referencia de Tesorería', a.referencia_tesoreria || '—'],
      ['Motivo de cancelación', a.motivo_cancelacion || '—']],
    actions: [
      btn({ label: 'Registrar pago', href: `adeudos/${a.id_adeudo}/pago`, variant: 'primary', when: a.estado === 'pendiente' }),
      btn({ label: 'Cancelar adeudo', href: `adeudos/${a.id_adeudo}/cancelar`, variant: 'danger', when: isAdmin && a.estado === 'pendiente' }),
      btn({ label: 'Imprimir comprobante', action: 'print', when: a.estado === 'pagado' }),
      btn({ label: 'Volver a adeudos', href: 'adeudos', variant: 'link' }),
    ],
  })}
  ${a.estado === 'pagado' ? receiptBlock({
    id: 'comprobante', title: 'Comprobante de pago de adeudo', folio: a.referencia_tesoreria,
    items: [...payInfo(a), ['Fecha de pago', date(a.fecha_pago)], ['Referencia de Tesorería', a.referencia_tesoreria]],
  }) : ''}`,
});

export const payForm = (a) => page({
  title: 'Registrar pago',
  desc: 'Captura la referencia del comprobante entregado por Tesorería.',
  body: html`${detailView({ title: who(a), sub: `${label('adeudoTipo', a.tipo)} · ${a.libro.titulo}`,
    items: [['Monto a cobrar', money(a.monto)], ['Estado', statusBadge('adeudo', a.estado)]] })}
  ${formView({
    id: 'pay-form',
    fields: [
      { name: 'referencia_tesoreria', label: 'Referencia de Tesorería', required: true, minlength: 3, maxlength: 40, placeholder: 'Ej. TES-2026-0001' },
      { name: 'fecha_pago', label: 'Fecha de pago', type: 'date', value: today(), max: today(), hint: 'Por omisión, hoy.' },
    ],
    actions: [btn({ label: 'Volver', href: 'adeudos', variant: 'link' }), submitButton('Registrar pago')],
  })}`,
});

export const cancelFineForm = (a) => page({
  title: 'Cancelar adeudo',
  desc: 'Solo el administrador puede cancelar. Queda registrado en la bitácora.',
  body: html`${detailView({ title: who(a), sub: `${label('adeudoTipo', a.tipo)} · ${a.libro.titulo}`,
    items: [['Monto a cancelar', money(a.monto)], ['Estado', statusBadge('adeudo', a.estado)]] })}
  ${formView({
    id: 'cancel-fine-form',
    fields: [{ name: 'motivo', label: 'Motivo de la cancelación', required: true, minlength: 3, maxlength: 120, span: 'wide' }],
    actions: [btn({ label: 'Volver', href: 'adeudos', variant: 'link' }), submitButton('Cancelar adeudo')],
  })}`,
});

// Amount summary shown before confirming a loss/damage report.
const summaryItems = (p) => [
  ['Usuario', `${p.usuario.nombre_completo} (${p.usuario.matricula})`],
  ['Libro', `${p.libro.clave} · ${p.libro.titulo} (copia ${p.numero_copia})`],
  ['Vencimiento', date(p.fecha_vencimiento)],
  ['Multa por retraso', `${money(p.monto_retraso)} (${p.dias_retraso} día(s) hábil(es))`],
  ['Valor de reposición', `${p.reposicion.valor_usd} USD × ${p.reposicion.tipo_cambio} = ${money(p.reposicion.monto_mxn)}`],
  ['Origen del precio', p.reposicion.fuente === 'ultima_compra' ? 'Última compra recibida' : 'Precio de referencia'],
];

export const amounts = (p, kind) => html`${summaryItems(p).map(([l, v]) => html`<div class="detail-item"><dt>${l}</dt><dd>${v}</dd></div>`)}
  <div class="detail-item"><dt>${kind === 'perdida' ? 'Adeudo por pérdida' : `Adeudo por daño (${p.porcentaje} %)`}</dt>
  <dd><strong>${money(kind === 'perdida' ? p.reposicion.monto_mxn : p.monto_danio)}</strong></dd></div>`;

export const incidentForm = (p, kind) => page({
  title: kind === 'perdida' ? 'Reportar pérdida' : 'Reportar daño',
  desc: kind === 'perdida'
    ? 'El ejemplar se da de baja, el préstamo se cierra y se avisa a Servicios Escolares y Tesorería.'
    : 'Se registra la devolución del ejemplar con un adeudo por daño.',
  body: html`${p.abierto ? '' : notice({ tone: 'error', text: 'Este préstamo ya está cerrado.' })}
  <section class="card"><dl class="detail-grid" id="amounts" aria-live="polite">${amounts(p, kind)}</dl></section>
  ${formView({
    id: 'incident-form',
    fields: kind === 'perdida' ? [
      { name: 'tipo_cambio', label: 'Tipo de cambio USD/MXN', type: 'number', step: '0.0001', min: '0.0001', value: p.reposicion.tipo_cambio, hint: 'Modifícalo solo si aplica otro tipo de cambio.' },
      { name: 'observacion', label: 'Observación', maxlength: 100, span: 'wide' },
    ] : [
      { name: 'porcentaje', label: 'Porcentaje del valor de reposición', type: 'number', min: 10, max: 100, step: 1, value: p.porcentaje, required: true, hint: 'Entre 10 y 100. Por omisión, 50.' },
      { name: 'observacion', label: 'Observación', maxlength: 100, span: 'wide' },
      { name: 'dar_baja', label: 'Dar de baja el ejemplar (dañado)', type: 'checkbox' },
    ],
    actions: [btn({ label: 'Cancelar', href: `prestamos/${p.id_prestamo}`, variant: 'link' }),
      submitButton(kind === 'perdida' ? 'Registrar pérdida' : 'Registrar daño')],
  })}`,
});

export const done = (title, items, extra = '') => page({
  title,
  body: html`${detailView({ title, items, actions: [btn({ label: 'Ver adeudos', href: 'adeudos', variant: 'primary' })] })}${extra}`,
});
