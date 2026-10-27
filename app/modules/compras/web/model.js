// Purchase requests: API calls and validation helpers.
import { api } from '/js/core/api.js';

export const list = () => api.get('/compras');
export const get = (id) => api.get('/compras/' + encodeURIComponent(id));
export const budget = (month = '') => api.get('/compras/presupuesto' + (month ? '?mes=' + encodeURIComponent(month) : ''));
export const cancel = (id) => api.post(`/compras/${encodeURIComponent(id)}/cancelar`, {});
export const receive = (id, payload) => api.post(`/compras/${encodeURIComponent(id)}/recibir`, payload);
export const send = (id) => api.post(`/compras/${encodeURIComponent(id)}/enviar`);

export async function bookTitles() {
  try {
    return (await api.get('/libros?estado=activo')).map((b) => b.titulo);
  } catch {
    return [];
  }
}

export const total = (lines) => lines.reduce((sum, l) => sum + (Number(l.cantidad) || 0) * (Number(l.precio_unitario) || 0), 0);
export const emptyLine = () => ({ descripcion: '', cantidad: 1, precio_unitario: 0 });

// Mirrors the server rules for a quick error; the server stays the authority.
export function validate(draft) {
  if (!draft.justificacion.trim()) throw new Error('Completa el campo justificación.');
  if (!draft.detalles.length) throw new Error('Agrega por lo menos un título.');
  for (const l of draft.detalles) {
    if (!l.descripcion.trim()) throw new Error('Completa el título de cada línea.');
    if (!Number.isInteger(l.cantidad) || l.cantidad < 1) throw new Error('La cantidad de cada título debe ser un entero positivo.');
    if (!Number.isFinite(l.precio_unitario) || l.precio_unitario < 0) throw new Error('Introduce un precio unitario válido.');
  }
  return draft;
}

export const create = (draft) => api.post('/compras', { justificacion: draft.justificacion, detalles: draft.detalles });

// Creates the request, then sends it. If sending fails, draft.id lets the caller retry only the send.
export async function createAndSend(draft) {
  if (!draft.id) draft.id = (await create(draft)).id_solicitud;
  return send(draft.id);
}

// Lines still to receive (ordered - received).
export const pending = (l) => l.cantidad - (l.cantidad_recibida || 0);
export const canReceive = (s) => s.estado === 'enviada' && s.detalles.some((l) => pending(l) > 0);
export const canCancel = (s) => ['pendiente', 'enviada'].includes(s.estado)
  && !s.detalles.some((l) => l.cantidad_recibida > 0);

// Builds the reception payload from the form values (cant_<id_detalle> inputs).
export function receptionPayload(data, s) {
  const lineas = s.detalles.map((l) => ({ id_detalle: l.id_detalle, cantidad_recibida: Number(data['cant_' + l.id_detalle] || 0) }));
  if (!data.factura_folio.trim() || data.factura_folio.trim().length < 3) throw new Error('El folio de factura debe tener al menos 3 caracteres.');
  if (!(Number(data.factura_total) >= 0) || data.factura_total === '') throw new Error('Introduce un monto de factura válido.');
  if (lineas.some((l) => !Number.isInteger(l.cantidad_recibida) || l.cantidad_recibida < 0)) throw new Error('Las cantidades recibidas deben ser enteros positivos.');
  const payload = { factura_folio: data.factura_folio.trim(), factura_total: Number(data.factura_total), lineas };
  if (data.fecha_recepcion) payload.fecha_recepcion = data.fecha_recepcion;
  return payload;
}
