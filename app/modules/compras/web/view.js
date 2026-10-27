import { html } from '/js/core/ui.js';
import { page, btn, actions, cardList, itemCard, card, statusBadge, formField, formView, submitButton,
  meter, notice, detailGrid, datetime, date, usd } from '/js/components/index.js';
import { total, pending } from './model.js';

// Monthly budget bar (RF-05, D-22).
export const budgetMeter = (b) => {
  const used = Number(b.usado_usd);
  const pct = b.presupuesto_usd > 0 ? Math.round((used / b.presupuesto_usd) * 100) : 100;
  return html`<section class="card">${meter({ value: used, max: b.presupuesto_usd,
    label: `Presupuesto del mes ${b.mes} (USD)`, text: `${usd(used)} de ${usd(b.presupuesto_usd)} · ${pct} %` })}
    <p class="muted">Disponible: <strong>${usd(Math.max(b.disponible_usd, 0))}</strong></p></section>`;
};

export const listPage = (items, budget) => page({
  title: 'Solicitudes de compra',
  desc: 'Prepara adquisiciones y da seguimiento a su envío a Tesorería.',
  actions: btn({ label: 'Nueva solicitud', href: 'compras/nueva', variant: 'primary' }),
  body: html`${budget ? budgetMeter(budget) : ''}${cardList({
    items,
    empty: { title: 'Aún no hay solicitudes', text: 'Crea una nueva solicitud para comenzar.' },
    render: (s) => itemCard({
      title: `${s.folio} · ${s.detalles.length} título(s)`,
      lines: [{ muted: s.justificacion }, usd(s.total_estimado)],
      badge: statusBadge('solicitud', s.estado),
      actions: btn({ label: s.estado === 'pendiente' ? 'Revisar' : 'Ver comprobante', href: 'compras/' + s.id_solicitud }),
    }),
  })}`,
});

const line = (l) => html`<div class="purchase-line">
  ${formField({ name: 'descripcion', label: 'Título', value: l.descripcion, required: true, maxlength: 180, list: 'purchase-titles' })}
  ${formField({ name: 'cantidad', label: 'Cantidad', type: 'number', value: l.cantidad, required: true, min: 1, step: 1 })}
  ${formField({ name: 'precio_unitario', label: 'Precio unitario (USD)', type: 'number', value: l.precio_unitario, required: true, min: 0, step: 0.01 })}
  ${btn({ label: 'Quitar', action: 'remove-line' })}</div>`;

export const lineHtml = (l = { descripcion: '', cantidad: 1, precio_unitario: 0 }) => line(l);

export const totalText = (lines) => 'Total estimado: ' + usd(total(lines));

export const form = (draft, titles, budget) => page({
  title: 'Nueva solicitud de compra',
  desc: 'Para: Tesorería de la Universidad Ducky.',
  body: html`${budget ? budgetMeter(budget) : ''}${formView({
    id: 'purchase-form',
    grid: false,
    fields: [{ name: 'justificacion', label: 'Justificación', value: draft.justificacion, required: true, maxlength: 500, placeholder: 'Motivo de la solicitud' }],
    children: html`
      <div class="purchase-lines" id="lines">${draft.detalles.map(lineHtml)}</div>
      <datalist id="purchase-titles">${titles.map((t) => html`<option value="${t}"></option>`)}</datalist>
      ${actions([btn({ label: 'Agregar título', action: 'add-line' })])}
      <p class="total" id="total">${totalText(draft.detalles)}</p>`,
    actions: [btn({ label: 'Cancelar', href: 'compras', variant: 'link' }), btn({ label: 'Guardar solicitud', action: 'save' }), btn({ label: 'Guardar y enviar', action: 'save-send' }), submitButton('Revisar y enviar')],
  })}`,
});

export const review = (draft) => page({
  title: 'Revisar solicitud',
  desc: 'Confirma los datos antes de enviar a Tesorería.',
  body: card({
    title: 'Confirmación de envío', cls: 'receipt',
    body: html`<p class="muted">Tesorería · ${draft.detalles.length} título(s) · ${draft.detalles.reduce((s, l) => s + l.cantidad, 0)} ejemplares</p>
    <p>${draft.justificacion}</p>
    ${draft.detalles.map((l) => html`<p>${l.descripcion}: ${l.cantidad} × ${usd(l.precio_unitario)}</p>`)}
    <p class="total">${totalText(draft.detalles)}</p>
    ${actions([btn({ label: 'Confirmar y enviar', action: 'confirm', variant: 'primary' }),
      !draft.id && btn({ label: 'Volver a editar', action: 'edit' })])}`,
  }),
});

const detailLine = (l) => html`<p>${l.descripcion} · ${l.cantidad} × ${usd(l.precio_unitario)} = ${usd(l.subtotal)}
  ${l.cantidad_recibida > 0 ? html`<span class="muted">· recibidos ${l.cantidad_recibida} de ${l.cantidad}</span>` : ''}</p>`;

const invoice = (s) => s.factura_folio ? detailGrid([
  ['Folio de factura', s.factura_folio], ['Monto facturado', usd(s.factura_total)],
  ['Fecha en que llegó el pedido', s.fecha_recepcion ? date(s.fecha_recepcion) : 'Recibido por partes'],
]) : '';

export const receipt = (s, { canSend, canReceive, canCancel }) => page({
  title: 'Comprobante de solicitud',
  desc: s.estado === 'pendiente' ? 'La solicitud aún no se ha enviado a Tesorería.' : 'Registro del envío a Tesorería.',
  body: html`${card({
    id: 'receipt', title: `Solicitud ${s.folio}`, cls: 'receipt',
    body: html`${statusBadge('solicitud', s.estado)}
    <p>Para: ${s.destinatario || 'Tesorería · Universidad Ducky'}</p>
    <p>Solicitante: ${s.solicitante}</p><p>Fecha: ${date(s.fecha)}</p><p>${s.justificacion}</p>
    ${s.detalles.map(detailLine)}
    <p><strong>Total estimado: ${usd(s.total_estimado)}</strong></p>${invoice(s)}`,
  })}
  ${actions([btn({ label: 'Volver a solicitudes', href: 'compras' }),
    btn({ label: 'Enviar a Tesorería', action: 'send', variant: 'primary', when: canSend && s.estado === 'pendiente' }),
    btn({ label: 'Recibir pedido', href: `compras/${s.id_solicitud}/recibir`, variant: 'primary', when: canReceive }),
    btn({ label: 'Cancelar solicitud', action: 'cancel', variant: 'danger', when: canCancel }),
    btn({ label: 'Imprimir comprobante', action: 'print' })])}`,
});

export const reception = (s) => page({
  title: `Recibir pedido · ${s.folio}`,
  desc: 'Captura la factura de la Editorial y las cantidades recibidas en esta entrega.',
  body: html`${notice({ text: 'Los títulos ya catalogados suman ejemplares; los nuevos quedan pendientes de catalogar.' })}
  ${formView({
    id: 'reception-form',
    fields: [
      { name: 'factura_folio', label: 'Folio de factura', required: true, minlength: 3, maxlength: 30 },
      { name: 'factura_total', label: 'Monto de la factura (USD)', type: 'number', required: true, min: 0, step: 0.01 },
      { name: 'fecha_recepcion', label: 'Fecha en que llegó el pedido', type: 'date' },
      ...s.detalles.filter((l) => pending(l) > 0).map((l) => ({
        name: 'cant_' + l.id_detalle, type: 'number', value: pending(l), min: 0, max: pending(l), step: 1, required: true,
        label: `${l.descripcion} (pendientes ${pending(l)} de ${l.cantidad})`, span: 'wide',
      })),
    ],
    actions: [btn({ label: 'Cancelar', href: 'compras/' + s.id_solicitud, variant: 'link' }), submitButton('Recibir pedido')],
  })}`,
});
