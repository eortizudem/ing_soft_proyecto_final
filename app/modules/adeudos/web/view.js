/**
 * @module modules/adeudos/view — HTML de adeudos, pago, cancelación, pérdida y daño (funciones puras: datos -> componentes; capa view).
 */
import { html } from '/js/core/ui.js';
import { LIST_LIMIT } from '/js/core/api.js';
import { page, btn, toolbar, resultsPanel, dataTable, statusBadge, formView, submitButton, detailView, receiptBlock,
  notice, labelItems, label, money, date, today, count } from '/js/components/index.js';

/**
 * Nombre y matrícula del usuario de un adeudo.
 * @param {{usuario: {nombre_completo: string, matricula: string}}} a - Adeudo.
 * @returns {Safe} HTML.
 */
const who = (a) => html`${a.usuario.nombre_completo} (${a.usuario.matricula})`;

/**
 * Página del listado de adeudos con búsqueda y filtros de estado y tipo.
 * @param {{q: string, estado: string, tipo: string}} filters - Filtros actuales.
 * @returns {Safe} Página con panel de resultados vacío.
 */
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

/**
 * Texto del contador del listado.
 * @param {Array<Object>} items - Adeudos cargados (`estado`, `monto`).
 * @returns {string} Total y suma de montos pendientes.
 */
export const summary = (items) => {
  const pending = items.filter((a) => a.estado === 'pendiente').reduce((sum, a) => sum + a.monto, 0);
  return count(items.length, undefined, LIST_LIMIT) + ` · ${money(pending)} pendientes`;
};

/**
 * Tabla de adeudos con acciones Ver/Registrar pago/Cancelar (esta última solo admin, solo pendientes).
 * @param {Array<Object>} items - Adeudos con `usuario`, `libro`, `tipo`, `monto`, `estado`, `id_adeudo`.
 * @param {boolean} isAdmin - Si se muestra la acción de cancelar.
 * @returns {Safe} Tabla HTML.
 */
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

/**
 * Pares etiqueta/valor del adeudo (usuario, libro, tipo, días de retraso, monto).
 * @param {Object} a - Adeudo.
 * @returns {Array<Array>} Lista de `[etiqueta, valor]`.
 */
const payInfo = (a) => [
  ['Usuario', who(a)], ['Libro', `${a.libro.clave} · ${a.libro.titulo}`], ['Tipo', label('adeudoTipo', a.tipo)],
  ['Días de retraso', a.dias_retraso], ['Monto', money(a.monto)],
];

/**
 * Página de detalle del adeudo; incluye comprobante de pago si está pagado.
 * @param {Object} a - Adeudo con `referencia_tesoreria`, `motivo_cancelacion`, `fecha_pago`, `id_prestamo`.
 * @param {boolean} isAdmin - Si se muestra el botón de cancelar.
 * @returns {Safe} Página.
 */
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

/**
 * Formulario de pago (referencia de Tesorería y fecha, por omisión hoy).
 * @param {Object} a - Adeudo a cobrar.
 * @returns {Safe} Página.
 */
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

/**
 * Formulario de cancelación con el motivo (solo admin).
 * @param {Object} a - Adeudo a cancelar.
 * @returns {Safe} Página.
 */
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
/**
 * Resumen de montos mostrado antes de confirmar pérdida o daño.
 * @param {Object} p - Previsualización (`usuario`, `libro`, `numero_copia`, `fecha_vencimiento`, `monto_retraso`, `dias_retraso`, `reposicion`).
 * @returns {Array<Array>} Lista de `[etiqueta, valor]`.
 */
const summaryItems = (p) => [
  ['Usuario', `${p.usuario.nombre_completo} (${p.usuario.matricula})`],
  ['Libro', `${p.libro.clave} · ${p.libro.titulo} (copia ${p.numero_copia})`],
  ['Vencimiento', date(p.fecha_vencimiento)],
  ['Multa por retraso', `${money(p.monto_retraso)} (${p.dias_retraso} día(s) hábil(es))`],
  ['Valor de reposición', `${p.reposicion.valor_usd} USD × ${p.reposicion.tipo_cambio} = ${money(p.reposicion.monto_mxn)}`],
  ['Origen del precio', p.reposicion.fuente === 'ultima_compra' ? 'Última compra recibida' : 'Precio de referencia'],
];

/**
 * Bloque de montos recalculable (resumen más el adeudo resultante por pérdida o daño).
 * @param {Object} p - Previsualización (ver `summaryItems`, más `porcentaje` y `monto_danio`).
 * @param {'perdida'|'danio'} kind - Tipo de incidente.
 * @returns {Safe} Elementos de lista de detalle.
 */
export const amounts = (p, kind) => html`${summaryItems(p).map(([l, v]) => html`<div class="detail-item"><dt>${l}</dt><dd>${v}</dd></div>`)}
  <div class="detail-item"><dt>${kind === 'perdida' ? 'Adeudo por pérdida' : `Adeudo por daño (${p.porcentaje} %)`}</dt>
  <dd><strong>${money(kind === 'perdida' ? p.reposicion.monto_mxn : p.monto_danio)}</strong></dd></div>`;

/**
 * Formulario de pérdida (tipo de cambio) o daño (porcentaje y baja del ejemplar), con aviso si el préstamo ya está cerrado.
 * @param {Object} p - Previsualización con `abierto`, `id_prestamo`, `reposicion`, `porcentaje`.
 * @param {'perdida'|'danio'} kind - Tipo de incidente.
 * @returns {Safe} Página.
 */
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

/**
 * Página de resultado genérica con detalle y enlace a adeudos.
 * @param {string} title - Título.
 * @param {Array<Array>} items - Pares `[etiqueta, valor]`.
 * @param {Safe|string} [extra=''] - HTML adicional.
 * @returns {Safe} Página.
 */
export const done = (title, items, extra = '') => page({
  title,
  body: html`${detailView({ title, items, actions: [btn({ label: 'Ver adeudos', href: 'adeudos', variant: 'primary' })] })}${extra}`,
});
